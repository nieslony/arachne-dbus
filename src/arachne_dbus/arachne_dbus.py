import argparse
import dbus
import dbus.service
import time
import signal
import os

DBUS_BUS_NAME = "at.nieslony.Arachne"
DBUS_IFACE_SERVER = DBUS_BUS_NAME + ".Server"

class Arachne(dbus.service.Object):
    def __init__(self, object_name, server_name, args):
        self._work_dir = args.directory
        self._server_name = server_name
        if args.bus == "system":
            self.bus = dbus.SystemBus()
        else:
            self.bus = dbus.SessionBus()

        name = dbus.service.BusName(DBUS_BUS_NAME, bus=self.bus)
        super().__init__(name, "/" + object_name)

        self.dbus_info = None
        self.polkit = None


    @dbus.service.method(DBUS_IFACE_SERVER)
    def Restart(self):
        pid_fn = f"{self._work_dir}/{self._server_name}.pid"
        pid = -1
        print("restart")
        try:
            with open(pid_fn, "r") as f:
                pid = int(f.read())
        except IOError as ex:
            raise dbus.DBusException(f"Cannot open pid file {pid_fn}: {ex.strerror}")
        except ValueError as ex:
            raise dbus.DBusException(f"Cannot read pid from {pid_fn}: {str(ex)}")
        try:
            os.kill(pid, signal.SIGHUP)
        except (ProcessLookupError, PermissionError) as ex:
            raise dbus.DBusException(f"Cannot kill process {pid}: {ex.strerror}")

    @dbus.service.method(DBUS_IFACE_SERVER, out_signature='saa{ss}')
    def CurrentConnections(self):
        status_fn = f"{self._work_dir}/status-{self._server_name}.conf"
        try:
            with open(status_fn, "r") as f:
                f.readlines()
        except IOError as ex:
            raise dbus.DBusException(f"Cannot open status file {status_fn}: {ex.strerror}")
        return (self.name, returnList)

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
            print(auth_response)
            (is_auth, _, details) = auth_response
        except dbus.DBusException as e:
            if e._dbus_error_name == "org.freedesktop.DBus.Error.ServiceUnknown":
                # polkitd timeout, retry
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, privilege)
            else:
                # it's another error, propagate it
                raise

        if not is_auth:
            # Aww, not authorized :(
            print(":(")
            return False

        print("Successful authorization!")
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="arachne_dbus",
        description="DBUS interface openvpn <-> arachne"
        )
    parser.add_argument(
        "-b", "--bus",
        choices=["system","user"],
        default="system",
        )
    parser.add_argument(
        "-d", "--directory",
        default="/etc/openvpn/server")
    args = parser.parse_args()

    import dbus.mainloop.glib
    from gi.repository import GLib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    loop = GLib.MainLoop()
    object = Arachne("UserVpn", "arachne", args)
    object = Arachne("SiteVpn", "arachne-site", args)
    loop.run()

