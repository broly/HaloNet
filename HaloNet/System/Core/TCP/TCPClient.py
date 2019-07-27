import asyncio
import asyncio.streams
from asyncio import Queue
import struct
from asyncio import get_event_loop
from Core.Logging import INFO_MSG, ERROR_MSG, WARN_MSG

from Core.AsyncObj import AsyncObj
from Core.Utils import is_valid

__author__ = "Broly"

clients = set()

async def handler(client):
    return
    await asyncio.sleep(.5)
    print(in_data)
    if in_data:
        await client.send(in_data + (b" ?" if in_data.endswith(b"!") else b" !"))


class TCPClient(AsyncObj):
    clients = set()

    async def __ainit__(self, endpoint, client_handler_class=None, do_open_connection=True):
        INFO_MSG("Created tcp client")
        self.endpoint = endpoint
        self.reader = None
        self.writer = None
        self.client_handler = client_handler_class(self) if client_handler_class else None

        self.clients.add(self)

        if do_open_connection:
            try:
                reader, writer = await asyncio.streams.open_connection(self.endpoint[0], self.endpoint[1])
                self.accept(reader, writer)
            except ConnectionRefusedError:
                WARN_MSG("Connection refused: %s" % self)

    def accept(self, reader, writer):
        INFO_MSG("accepted", writer.transport._extra['peername'])
        self.reader = reader
        self.writer = writer
        asyncio.Task(self.client_loop())

    def __isvalid__(self):
        return super().__isvalid__() and \
               self.reader is not None and self.writer is not None

    def __repr__(self):
        return "<TCPClient connection to {0}>".format(self.endpoint)

    async def recv(self):
        data_size_raw = await self.reader.read(8)
        if data_size_raw:
            INFO_MSG("Receiving from", self.reader._transport._extra['peername'])
            INFO_MSG("a1")
            INFO_MSG("a2")
            data_size = struct.unpack('Q', data_size_raw)[0]
            INFO_MSG("a3")
            data = await self.reader.read(data_size)
            INFO_MSG("a4")
            return data

    async def send(self, msg):
        INFO_MSG("Sending to", self.writer.transport._extra['peername'], msg)
        if is_valid(self):
            self.writer.write(struct.pack('Q', len(msg)) + msg)
            await self.writer.drain()
            INFO_MSG("SENT")
            return True
        ERROR_MSG("Unable to send info. Not connected")
        return False

    async def client_loop(self):
        try:
            INFO_MSG('client loop started')
            while True:
                INFO_MSG('LOOP')
                msg = await self.recv()
                INFO_MSG('LOO2')
                await asyncio.sleep(0.1)
                if msg and self.client_handler is not None:
                    await self.client_handler(msg)
        except ConnectionResetError:
            WARN_MSG("Connection reseted")

    def __adel__(self):
        if self.writer is not None:
            self.writer.close()

def main():

    async def client():
        client = await TCPClient(('127.0.0.1', 8888), handler)
        if is_valid(client):
            await client.send(b"Yo!")

    try:
        get_event_loop().run_until_complete(client())
        get_event_loop().run_forever()
    finally:
        get_event_loop().close()


if __name__ == '__main__':
    main()