from asyncio import get_event_loop
import asyncio

from Core import ERROR_MSG
from Core import INFO_MSG
from Core.TCP.TCPServer import TCPServer
from Core.TCP.TCPClient import TCPClient

tcp_server = None
tcp_client = None

class HandlerClass():
    def __init__(self, client):
        self.client = client

    def __call__(self, data):
        return self.handle_message(data)

    async def handle_message(self, data):
        pass

class HandlerClass2():
    def __init__(self, client):
        self.client = client

    def __call__(self, data):
        return self.handle_message(data)

    async def handle_message(self, data):
        ERROR_MSG('Data received', data)

        ERROR_MSG('Data sent to %s' % (self.client))
        await self.client.send(b"qwdwqf ~ " + data)

def main():
    async def server():
        global tcp_server
        global tcp_client
        tcp_server = await TCPServer(("127.0.0.1", 9001), HandlerClass2)
        tcp_client = await TCPClient(("127.0.0.1", 9002), HandlerClass2)
        ERROR_MSG('Data sent to %s' % tcp_client)
        await tcp_client.send(b"qwe")
        # tcp_client.writer.close()

    try:
        get_event_loop().run_until_complete(server())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()


if __name__ == '__main__':
    main()