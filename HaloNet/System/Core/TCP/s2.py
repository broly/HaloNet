from asyncio import get_event_loop
import asyncio

from Core import ERROR_MSG
from Core import INFO_MSG
from Core.TCP.TCPServer import TCPServer

tcp_server = None

class HandlerClass():
    def __init__(self, client):
        self.client = client

    def __call__(self, data):
        return self.handle_message(data)

    async def handle_message(self, data):
        ERROR_MSG('Data received %s from %s' % (data, self.client))

        await self.client.send(b" = " + data)

def main():
    async def server():
        global tcp_server
        tcp_server = await TCPServer(("127.0.0.1", 9002), HandlerClass)

    try:
        get_event_loop().run_until_complete(server())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()


if __name__ == '__main__':
    main()