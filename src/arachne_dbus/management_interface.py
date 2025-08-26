import threading
import socket
import time

class AnswerHandler:
    def pushAnswerLine(self, line: str) -> bool:
        return False

    def handleAnswerLine(self):
        pass



class ManagementInterface:
    def __init__(self, socket_filename: str):
        self._management_socket_fn = socket_filename
        self._management_handler = threading.Thread(target=self.management_handler)
        self._management_handler.daemon = True
        self._mgmt_file = None
        self._answer_handler = None

    def start(self):
        self._management_handler.start()

    def sendSigHup(self):
        self._mgmt_file.print("signal SIGHUP", file=self._mgmt_file)

    def management_handler(self):
        while True:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as mgmt:
                while True:
                    try:
                        mgmt.connect(self._management_socket_fn)
                        break
                    except ConnectionRefusedError as ex:
                        pass
                    except FileNotFoundError as ex:
                        pass
                    time.sleep(0.5)

                self._mgmt_file = mgmt.makefile("rw")
                while (True):
                    line = self._mgmt_file.readline().strip()
                    if not line:
                        mgmt.close()
                        print("Socket closed")
                        break
                    if line.startswith(">"):
                        print(f"Push line {line} ignored")
                    elif self._answer_handler:
                        removeHandler = self._answer_handler.pushAnswerLine(line)
                        if removeHandler:
                            self._answer_handler = None
                    else:
                        print(f"Unhandled line: {line}")
