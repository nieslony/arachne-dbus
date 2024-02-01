import argparse
import dbus
import dbus.service
import time
import signal
import os
import os.path
import threading
import inotify_simple
import time
import sys
import syslog

DBUS_BUS_NAME = "at.nieslony.Arachne"
DBUS_IFACE_SERVER = DBUS_BUS_NAME + ".Server"

class Arachne(dbus.service.Object):
    def __init__(self, object_name, server_name, args):
        self._work_dir = args.directory
        self._server_name = server_name
        self._pid_fn = f"{self._work_dir}/server-{self._server_name}.pid"
        self._status_fn = f"{self._work_dir}/server-{self._server_name}.log"
        self._console_log = args.console_log

        if args.bus == "system":
            self.bus = dbus.SystemBus()
        else:
            self.bus = dbus.SessionBus()

        name = dbus.service.BusName(DBUS_BUS_NAME, bus=self.bus)
        super().__init__(name, "/" + object_name)

        self.dbus_info = None
        self.polkit = None

        self._observer = threading.Thread(target=self.observe_status)
        self._observer.start()

    def log(self, priority, message):
        if (self._console_log):
            if priority == syslog.LOG_ERR:
                prefix = "Error"
                f = sys.stderr
            elif priority == syslog.LOG_WARNING:
                prefix = "Warning"
                f = sys.stderr
            elif priority == syslog.LOG_INFO:
                prefix = "Info"
                f = sys.stdout
            else:
                prefix = "???"
                f = sys.stdout
            print(f"{prefix}: {message}", file=f)
        else:
            syslog.syslog(priority, message)
        if priority == syslog.LOG_ERR:
            raise dbus.DBusException(message)

    def observe_status(self):
        self.log(syslog.LOG_INFO, f"Starting observer for {self._status_fn}.")
        inotify = inotify_simple.INotify()
        if not os.path.exists(self._status_fn):
            f = open(self._status_fn, "a")
            f.close()
        wd = inotify.add_watch(self._status_fn, inotify_simple.flags.MODIFY)
        last_notify = 0
        while True:
            for event in inotify.read():
                now = time.time()
                if now - last_notify > 1:
                    self.log(syslog.LOG_DEBUG, f"{time.strftime('%H:%M:%S')} {self._status_fn} {str(event)}")
                    last_notify = now
                    try:
                        (ti, cl) = self.readServerStatus()
                        self.ServerStatusChanged(ti, cl)
                    except dbus.DBusException:
                        pass
        self.log(syslog.LOG_INFO, f"Terminating observer for {self._status_fn}.")

    def sendSignal(self, sign):
        pid = -1
        try:
            with open(self._pid_fn, "r") as f:
                pid = int(f.read())
        except IOError as ex:
            self.log(syslog.LOG_ERR, f"Cannot open pid file {self._pid_fn}: {ex.strerror}")
        except ValueError as ex:
            self.log(syslog.LOG_ERR, f"Cannot read pid from {pid_fn}: {str(ex)}")
        try:
            os.kill(pid, sign)
        except (ProcessLookupError, PermissionError) as ex:
            self.log(syslog.LOG_ERR, f"Cannot kill process {pid}: {ex.strerror}")

    @dbus.service.method(DBUS_IFACE_SERVER)
    def Restart(self):
        self.log(syslog.LOG_INFO, f"Restart {self._server_name}")
        self.sendSignal(signal.SIGUSR1)

    @dbus.service.method(DBUS_IFACE_SERVER, out_signature='(xa(ssssxxxssss))')
    def ServerStatus(self):
        self.log(syslog.LOG_INFO, f"ServerStatus {self._server_name}")
        self.sendSignal(signal.SIGUSR2)
        return self.readServerStatus()

    @dbus.service.signal(DBUS_IFACE_SERVER, signature='xa(ssssxxxssss)')
    def ServerStatusChanged(self, ti, cl):
        pass

    def readServerStatus(self):
        clients = []
        try:
            with open(self._status_fn, "r") as f:
                f.readline()
                l = f.readline().strip()
                try:
                    (line_head, _, statusTime) = l.split(",")
                except ValueError as ex:
                    self.log(syslog.LOG_ERR, f'Expected line "TIME,<ISO date time>,<secs since epoch>" got: "{l}"')
                l = f.readline()
                if not l.startswith("HEADER,CLIENT_LIST,"):
                    self.log(syslog.LOG_ERR, f'Expected "HEADER,CLIENT_LIST,..." got "{l}"')
                while (l := f.readline().strip()).startswith("CLIENT_LIST,"):
                    try:
                        (_, commonName, readAddress, virtualAddress, virtualIpV6Address, bytesReceivedStr, bytesSentStr, _, connectedSinceStr, username, clientId, peerId, dataChannelCipher) = l.split(",")
                    except ValueError as ex:
                        self.log(syslog.LOG_ERR, f'Wrong number of fields "{str(ex)}" got "{l}"')
                    try:
                        bytesReceived = int(bytesReceivedStr)
                        bytesSent = int(bytesSentStr)
                    except ValueError as ex:
                        self.log(syslog.LOG_ERR, f"bytes received and bytes sent are not integer: {l}")
                    clients.append((commonName, readAddress, virtualAddress, virtualIpV6Address, bytesReceived, bytesSent, connectedSinceStr, username, clientId, peerId, dataChannelCipher))
        except IOError as ex:
            self.log(syslog.LOG_ERR, f"Cannot open status file {status_fn}: {ex.strerror}")
        return (statusTime, clients)

    def _check_polkit_privilege(self, sender, conn, privilege):
        # Get Peer PID
        if self.dbus_info is None:
            # Get DBus Interface and get info thru that
            self.dbus_info = dbus.Interface(conn.get_object("org.freedesktop.DBus",
                                                            "/org/freedesktop/DBus/Bus", False),
                                            "org.freedesktop.DBus")
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)

        # Query polkit
        if self.polkit is None:
            self.polkit = dbus.Interface(dbus.SystemBus().get_object(
            "org.freedesktop.PolicyKit1",
            "/org/freedesktop/PolicyKit1/Authority", False),
                                        "org.freedesktop.PolicyKit1.Authority")

        # Check auth against polkit; if it times out, try again
        try:
            auth_response = self.polkit.CheckAuthorization(
                ("unix-process", {"pid": dbus.UInt32(pid, variant_level=1),
                                "start-time": dbus.UInt64(0, variant_level=1)}),
                privilege, {"AllowUserInteraction": "true"}, dbus.UInt32(1), "", timeout=600)
            self.log(syslog.LOG_INFO, auth_response)
            (is_auth, _, details) = auth_response
        except dbus.DBusException as e:
            if e._dbus_error_name == "org.freedesktop.DBus.Error.ServiceUnknown":
                # polkitd timeout, retry
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, privilege)
            else:
                # it's another error, propagate it
                self.log(syslog.LOG_ERR, str(e))

        if not is_auth:
            # Aww, not authorized :(
            self.log(syslog.LOG_WARNING, "Not authorized")
            return False

        self.log(syslog.LOG_INFO, "Successful authorization!")
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
        )
    parser.add_argument(
        "-d", "--directory",
        default="/etc/openvpn/server")
    parser.add_argument(
        "-c", "--console-log",
        action='store_true',
        help="Log to console instead of syslog"
        )
    args = parser.parse_args()

    import dbus.mainloop.glib
    from gi.repository import GLib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    loop = GLib.MainLoop()
    object = Arachne("UserVpn", "arachne", args)
    object = Arachne("SiteVpn", "arachne-site", args)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
