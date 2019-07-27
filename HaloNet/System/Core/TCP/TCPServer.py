import asyncio
import asyncio.streams
from Core.AsyncObj import AsyncObj
from asyncio import get_event_loop
from Core.Logging import INFO_MSG, ERROR_MSG, WARN_MSG

from Core.TCP.TCPClient import TCPClient

__author__ = "Broly"

async def handler(client):
    return
    await asyncio.sleep(.5)
    print(in_data)
    if in_data:
        await client.send(in_data + (b" ?" if in_data.endswith(b"!") else b" !"))

class TCPServer(AsyncObj):
    async def __ainit__(self, endpoint, client_handler_class):
        self.server = None # encapsulates the server sockets
        self.endpoint = endpoint
        self.client_handler_class = client_handler_class

        self.clients = dict() # task -> (reader, writer)

        await self.start()
        INFO_MSG("%s spawned" % self)

    def __repr__(self):
        return "<TCPServer connection at {0}>".format(self.endpoint)

    def accept_new_client(self, client_reader, client_writer):
        INFO_MSG("Server accepted client", client_writer)
        async def Task():
            peername = client_writer.transport._extra['peername']
            client = await TCPClient(peername, self.client_handler_class, False)
            self.clients[peername] = client
            client.accept(client_reader, client_writer)
        asyncio.Task(Task())

    async def start(self):
        INFO_MSG("Server start")
        await asyncio.streams.start_server(self.accept_new_client, self.endpoint[0], self.endpoint[1], loop=get_event_loop())

    async def stop(self):
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

def main():

    async def server():
        tcp_server = await TCPServer(("127.0.0.1", 9001))

    try:
        get_event_loop().run_until_complete(server())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()


if __name__ == '__main__':
    main()