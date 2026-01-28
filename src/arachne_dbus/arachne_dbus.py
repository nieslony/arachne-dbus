import argparse
import dbus
import dbus.service
import time
import signal
import socket
import os
import os.path
import threading
import inotify_simple
import time
import sys
import syslog

from . management_interface import *
from . logger import logger

DBUS_BUS_NAME = "at.nieslony.Arachne"
DBUS_IFACE_SERVER = DBUS_BUS_NAME + ".Server"

class Arachne(dbus.service.Object):
    def __init__(self, object_name, server_name, args):
        self._work_dir = args.directory
        self._server_name = server_name
        self._pid_fn = f"{self._work_dir}/arachne-{self._server_name}-server.pid"
        self._status_fn = f"{self._work_dir}/status-arachne-{self._server_name}.log"

        if args.bus == "system":
            self.bus = dbus.SystemBus()
        else:
            self.bus = dbus.SessionBus()

        try:
            name = dbus.service.BusName(DBUS_BUS_NAME, bus=self.bus)
        except dbus.exceptions.DBusException as ex:
            logger.log(syslog.LOG_CRIT, f"Cannot register DBUS service {DBUS_BUS_NAME}: {ex}")
        super().__init__(name, "/" + object_name)

        self.dbus_info = None
        self.polkit = None

        self._management_interface = ManagementInterface(f"{self._work_dir}/arachne-{self._server_name}.sock")
        self._management_interface.start()

        self._observer = threading.Thread(target=self.observe_status)
        self._observer.daemon = True
        self._observer.start()

    def observe_status(self):
        logger.log(syslog.LOG_INFO, f"Starting observer for {self._status_fn}.")
        inotify = inotify_simple.INotify()
        if not os.path.exists(self._status_fn):
            logger.log(syslog.LOG_INFO, f"Log file does not exist, creating empty one.")
            try:
                f = open(self._status_fn, "a")
                f.close()
            except PermissionError as ex:
                logger.log(syslog.LOG_CRIT, f"Error creating {self._status_fn}: {ex}")
        try:
            wd = inotify.add_watch(self._status_fn, inotify_simple.flags.MODIFY)
        except OSError as ex:
            logger.log(syslog.LOG_CRIT, f"Error accessing {self._status_fn}: {ex}")
        last_notify = 0
        while True:
            for event in inotify.read():
                now = time.time()
                if now - last_notify > 1:
                    logger.log(
                        syslog.LOG_DEBUG,
                        f"{time.strftime('%H:%M:%S')} Got observer event on {self._status_fn} {str(event)}"
                    )
                    last_notify = now
                    try:
                        (ti, cl) = self.readServerStatus()
                        self.ServerStatusChanged(ti, cl)
                    except dbus.DBusException:
                        pass
        logger.log(syslog.LOG_INFO, f"Terminating observer for {self._status_fn}.")

    def sendSignal(self, sign):
        pid = -1
        try:
            with open(self._pid_fn, "r") as f:
                pid = int(f.read())
        except IOError as ex:
            logger.log(syslog.LOG_ERR, f"Cannot open pid file {self._pid_fn}: {ex.strerror}")
        except ValueError as ex:
            logger.log(syslog.LOG_ERR, f"Cannot read pid from {self._pid_fn}: {str(ex)}")
        try:
            os.kill(pid, sign)
        except (ProcessLookupError, PermissionError) as ex:
            logger.log(syslog.LOG_ERR, f"Cannot send signal {sign} to process {pid}: {ex.strerror}")

    @dbus.service.method(DBUS_IFACE_SERVER)
    def Restart(self):
        logger.log(syslog.LOG_INFO, f"Restart {self._server_name} VPN")
        #self.sendSignal(signal.SIGHUP)
        asyncio.run(self._management_interface.restart())

    @dbus.service.method(DBUS_IFACE_SERVER, out_signature='(xa(ssssxxxssss))')
    def ServerStatus(self):
        logger.log(syslog.LOG_INFO, f"ServerStatus {self._server_name} changed")
        self.sendSignal(signal.SIGUSR2)
        return self.readServerStatus()

    @dbus.service.signal(DBUS_IFACE_SERVER, signature='xa(ssssxxxssss)')
    def ServerStatusChanged(self, ti, cl):
        pass

    @dbus.service.method(DBUS_IFACE_SERVER, out_signature='s')
    def RunningAsUser(self):
        return os.getlogin()

    def readServerStatus(self):
        clients = []
        statusTime = ""
        try:
            with open(self._status_fn, "r") as f:
                f.readline()
                l = f.readline().strip()
                try:
                    (line_head, _, statusTime) = l.split(",")
                except ValueError as ex:
                    logger.log(syslog.LOG_ERR, f'Expected line "TIME,<ISO date time>,<secs since epoch>" got: "{l}"')
                l = f.readline()
                if not l.startswith("HEADER,CLIENT_LIST,"):
                    logger.log(syslog.LOG_ERR, f'Expected "HEADER,CLIENT_LIST,..." got "{l}"')
                while (l := f.readline().strip()).startswith("CLIENT_LIST,"):
                    try:
                        (_, commonName, readAddress, virtualAddress, virtualIpV6Address, bytesReceivedStr, bytesSentStr, _, connectedSinceStr, username, clientId, peerId, dataChannelCipher) = l.split(",")
                    except ValueError as ex:
                        logger.log(syslog.LOG_ERR, f'Wrong number of fields "{str(ex)}" got "{l}"')
                    try:
                        bytesReceived = int(bytesReceivedStr)
                        bytesSent = int(bytesSentStr)
                    except ValueError as ex:
                        logger.log(syslog.LOG_ERR, f"bytes received and bytes sent are not integer: {l}")
                    clients.append((commonName, readAddress, virtualAddress, virtualIpV6Address, bytesReceived, bytesSent, connectedSinceStr, username, clientId, peerId, dataChannelCipher))
        except IOError as ex:
            logger.log(syslog.LOG_ERR, f"Cannot open status file {self._status_fn}: {ex.strerror}")

        logger.log(syslog.LOG_DEBUG, f"Clients connected to arachne-{self._server_name}: {clients}")
        return (statusTime, clients)

    def _check_polkit_privilege(self, sender, conn, privilege):
        # Get Peer PID
        if self.dbus_info is None:
            # Get DBus Interface and get info thru that
            self.dbus_info = dbus.Interface(
                conn.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus/Bus", False),
                "org.freedesktop.DBus"
            )
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)

        # Query polkit
        if self.polkit is None:
            self.polkit = dbus.Interface(
                dbus.SystemBus().get_object(
                    "org.freedesktop.PolicyKit1",
                    "/org/freedesktop/PolicyKit1/Authority",
                    False
                ),
                "org.freedesktop.PolicyKit1.Authority"
            )

        # Check auth against polkit; if it times out, try again
        try:
            auth_response = self.polkit.CheckAuthorization(
                ( "unix-process",
                    { "pid": dbus.UInt32(pid, variant_level=1),
                      "start-time": dbus.UInt64(0, variant_level=1)
                    }
                ),
                privilege,
                {"AllowUserInteraction": "true"},
                dbus.UInt32(1),
                "",
                timeout=600
            )
            logger.log(syslog.LOG_INFO, auth_response)
            (is_auth, _, details) = auth_response
        except dbus.DBusException as e:
            if e._dbus_error_name == "org.freedesktop.DBus.Error.ServiceUnknown":
                # polkitd timeout, retry
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, privilege)
            else:
                # it's another error, propagate it
                logger.log(syslog.LOG_ERR, str(e))

        if not is_auth:
            # Aww, not authorized :(
            logger.log(syslog.LOG_WARNING, "Not authorized")
            return False

        logger.log(syslog.LOG_INFO, "Successful authorization!")
        return True

def main():
    parser = argparse.ArgumentParser(
        prog="arachne_dbus",
        description="DBUS interface openvpn <-> arachne"
        )
    parser.add_argument(
        "-b", "--bus",
        choices=["system","session"],
        default="system",
        help="Connect to system or session bus (default: %(default)s)"
        )
    parser.add_argument(
        "-d", "--directory",
        default="/run/openvpn-server",
        help="Directory containing runtime files (default: %(default)s)"
        )
    parser.add_argument(
        "-c", "--console-log",
        action='store_true',
        help="Log to console instead of syslog"
        )
    args = parser.parse_args()
    logger.console_log(args.console_log)

    import dbus.mainloop.glib
    from gi.repository import GLib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    userVpn = None
    siteVpn = None
    try:
        loop = GLib.MainLoop()
        userVpn = Arachne("UserVpn", "user", args)
        #siteVpn = Arachne("SiteVpn", "site", args)
        loop.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
