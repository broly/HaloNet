import asyncio

from Core import INFO_MSG
from Core.ClientConnectionHandler import ClientConnectionHandler
from Core.TCP.TestProtocolClient import TCPClient


class TCPServer():
    def __init__(self):
        self.srv = None
        self.clients = dict()

    def set_srv(self, srv):
        self.srv = srv

    def accept(self, client):
        # INFO_MSG("Accepted client %s" % client)
        self.clients[client.endpoint] = client

    async def close(self):
        if self.srv is not None:
            self.srv.close()
            await self.srv.wait_closed()


async def create_server(endpoint, do_serving=True):
    server = TCPServer()
    if do_serving:
        srv = await asyncio.get_event_loop().create_server(lambda: TCPClient(("0.0.0.0", 0), ClientConnectionHandler, server), endpoint[0], endpoint[1])
    else:
        srv = None
    server.set_srv(srv)
    return server


async def main():
    loop = asyncio.get_event_loop()
    server = await create_server(('127.0.0.1', 8888))
    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.srv.sockets[0].getsockname()))
    return server

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(main())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()