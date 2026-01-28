import syslog

class Logger:
    def __init__(self, console_log: bool):
        self._console_log = console_log

    def log(self, priority, message: str):
        if (self._console_log):
            if priority == syslog.LOG_CRIT:
                prefix = "Critical"
                f = sys.stderr
            elif priority == syslog.LOG_ERR:
                prefix = "Error"
                f = sys.stderr
            elif priority == syslog.LOG_WARNING:
                prefix = "Warning"
                f = sys.stderr
            elif priority == syslog.LOG_INFO:
                prefix = "Info"
                f = sys.stdout
            elif priority == syslog.LOG_DEBUG:
                prefix = "Debug"
                f = sys.stdout
            else:
                prefix = "???"
                f = sys.stdout
            print(f"{prefix}: {message}", file=f)
        else:
            syslog.syslog(priority, message)
        if priority == syslog.LOG_ERR:
            raise dbus.DBusException(message)
        elif priority == syslog.LOG_CRIT:
            os.kill(os.getpid(), signal.SIGTERM)

logger = None
