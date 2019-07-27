import asyncio
from asyncio import Queue
import struct
from functools import partial

from Core.Globals import Globals
from Core import ERROR_MSG
from Core import INFO_MSG
from Core import WARN_MSG

# connections_count = 0
from Core.intrinsic.Serialization import BinarySerialization
from Core.Utils import is_valid

from Core.ClientConnectionHandler import ClientConnectionHandler

HELLO_PACKAGE =             b'\xffhello\xffp'
HELLO_RESPONSE_PACKAGE =    b'\x7fhello\x7fp'


class TCPClient(asyncio.Protocol):

    def __init__(self, endpoint, handler, server=None, on_connection_lost=None):
        self.transport = None
        self.handler = handler(self) if handler is not None else None
        self.endpoint = endpoint
        self.server = server
        self.on_connection_lost_callbacks = {on_connection_lost}

        self.late_data = bytes()

    def __isvalid__(self):
        return self.transport is not None

    def __repr__(self):
        return "<Connection to {0}{1}>".format(self.endpoint, "[INVALID]" if not self.__isvalid__() else "")

    def connection_made(self, transport):
        # global connections_count
        # connections_count += 1
        # INFO_MSG("created connection %i" % connections_count)
        if self.endpoint == ("0.0.0.0", 0):
            self.endpoint = transport.get_extra_info('peername')
        self.transport = transport
        if self.server is not None:
            self.server.accept(self)

    def send(self, msg):
        if is_valid(self):
            data = struct.pack('Q', len(msg)) + msg
            self.transport.write(data)
        else:
            WARN_MSG("Unable to send data to {}, not connected".format(self.endpoint))

    def data_received(self, data):
        data = self.late_data + data
        self.late_data = bytes()
        while data:
            data_size = struct.unpack('Q', data[:8])[0]
            msg = data[8:data_size+8]
            data_slice = data[data_size+8:]
            if len(msg) != data_size:  # TODO check the late data!
                self.late_data = data
                return

            data = data_slice

            if msg == HELLO_PACKAGE:
                self.send(HELLO_RESPONSE_PACKAGE)
                return
            elif msg == HELLO_RESPONSE_PACKAGE:
                # pass the response handling
                return

            if self.handler is not None:
                asyncio.Task(self.handler(msg))

    def connection_lost(self, exc):
        if not self.on_connection_lost_callbacks:
            WARN_MSG("Connection to %s lost: %s and not handled" % (self.endpoint, exc))
        else:
            INFO_MSG("Connection to %s lost: %s" % (self.endpoint, exc))
        self.transport = None
        for cb in self.on_connection_lost_callbacks:
            cb(self) if callable(cb) else None


    def add_lost_callback(self, callback):
        self.on_connection_lost_callbacks.add(callback)

    def close(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None

    def destroy(self):
        self.close()

    def __del__(self):
        self.close()


async def create_connection(endpoint, on_lost=None, connection_handler=ClientConnectionHandler):
    try:
        connection = await asyncio.get_event_loop().create_connection(lambda: TCPClient(endpoint, connection_handler, on_connection_lost=on_lost), endpoint[0], endpoint[1])
    except ConnectionRefusedError:
        WARN_MSG("Connection refused to {}".format(endpoint))
        connection = None, TCPClient(endpoint, None)
    except OSError as exc:
        ERROR_MSG("Incorrect endpoint %s" % (endpoint,), exc)
        connection = None, TCPClient(endpoint, None)
    finally:
        return connection


async def main():
    c = await create_connection(('127.0.0.1', 8888))
    c.send(b"qwe1234567890")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()
    loop.close()