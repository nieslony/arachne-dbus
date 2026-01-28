import threading
import socket
import time
import sys
import asyncio
import syslog

from . logger import logger

class AnswerHandler:
    def __init__(self):
        pass

    def pushAnswerLine(self, line: str) -> bool:
        return False

    def writeCommand(self, command: str, writer):
        print("Sending command: " + command, file=sys.stdout)
        writer.write(str)

    def run(self, reader, writer):
        pass

class RestartHandler(AnswerHandler):
    def __init__(self, reader, writer):
        super().__init__(reader, writer)

    def run(self, reader, writer):
        self.sendCommand("signal SIGHUP". writer)

    def pushAnswerLine(self, line: str) -> bool:
        print("Got answer " + line)
        if not lines.startwith("SUCCESS:"):
             raise dbus.DBusException(line)
        return True

class ManagementInterface:
    def __init__(self, socket_filename: str):
        self._management_socket_fn = socket_filename
        self._commandQeue = asyncio.Queue()

    def start(self):
        #asyncio.run(self.management_handler())
        logger.log(syslog.LOG_INFO, "Starting management thread")
        loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.multiThread())
        thread = threading.Thread(target=loop.run_until_complete, args=(self.multiThread(), ))
        thread.start()

    async def restart(self):
        await self._commandQeue.put(RestartHandler())

    async def multiThread(self):
        await asyncio.gather(self.handleEventQuete(), self.management_handler())

    async def readFromSocket(self, reader, writer):
        line = await reader.readline()
        if not line:
            writer.close()
            await writer.wait_closed()
            self._commandQeue = None
            print("Socket closed")
            return
        line = line.decode().strip()
        if line.startswith(">"):
            print(f'Push line: "{line}" (ignored)')
        elif self._answer_handler:
            print("push answer: " + line)
            removeHandler = self._answer_handler.pushAnswerLine(line)
            if removeHandler:
                print("Exit handler")
                self._answer_handler = None
        else:
            print(f"Unhandled line: {line}")

    async def handleEventQuete(self):
        while (True):
            event = await self._commandQeue.get()
            logger.log(syslog.LOG_INFO, "Processing event")
            event.run()

    async def management_handler(self):
        while True:
            while True:
                try:
                    reader, writer = await asyncio.open_unix_connection(self._management_socket_fn)
                    break;
                except FileNotFoundError:
                    pass
                except ConnectionRefusedError:
                    pass
                await asyncio.sleep(0.5)
            while (True):
                await self.readFromSocket(reader, writer)

