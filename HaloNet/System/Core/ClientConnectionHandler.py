import asyncio
from time import time

from Core import ERROR_MSG, WARN_MSG
from Core.Globals import Globals
from Core import INFO_MSG
from Core.GlobalManagers import EntitiesDispatcher
from Core.intrinsic.Serialization import BinarySerialization
from Core.Utils import ConnectionMessageTypes

class RemoteServerException(Exception):
    pass

class ClientConnectionHandler():
    """
    Incoming data handler
    :var client_connection current connection
    """

    def __init__(self, client_connection):
        self.client_connection = client_connection

    def __call__(self, data):
        return self.handle_message(data)

    async def handle_message(self, data):
        """ Обработка входящего сообщения """

        try:
            message_proxy = BinarySerialization(data).proxy()
        except Exception as e:
            ERROR_MSG("Unable to make proxy for data %s: %s" % (data, e))
            return
        try:
            message_type = message_proxy >> int
            message_data = message_proxy >> bytes
        except:
            print(message_proxy)


        if message_type == ConnectionMessageTypes.rmi_call:
            proxy = BinarySerialization(message_data).proxy()
            entity_id    = proxy >> int
            gen_sig      = proxy >> str
            method_index = proxy >> int
            future_id    = proxy >> int
            access_token = proxy >> str
            params       = proxy >> bytes
            if gen_sig == Globals.generator_signature:
                await EntitiesDispatcher().execute_rmi(self.client_connection, entity_id, method_index, future_id, access_token, params)
            else:
                EntitiesDispatcher().remote_response_error(self.client_connection, entity_id, future_id, "Generator signature mismatch")

        elif message_type == ConnectionMessageTypes.rmi_future:
            proxy = BinarySerialization(message_data).proxy()
            entity_id    = proxy >> int
            method_index = proxy >> int
            future_id    = proxy >> int
            returns      = proxy >> bytes
            if future_id != -1:
                EntitiesDispatcher().yield_rmi_result(future_id, entity_id, method_index, returns)

        elif message_type == ConnectionMessageTypes.rmi_error:
            proxy = BinarySerialization(message_data).proxy()
            error_source  = proxy >> str
            error_message = proxy >> str
            future_id     = proxy >> int

            WARN_MSG("Error from %s: %s" % (error_source, error_message))

            if future_id != -1:
                EntitiesDispatcher().yield_rmi_error(future_id)

        elif message_type == ConnectionMessageTypes.rmi_exception:
            proxy = BinarySerialization(message_data).proxy()
            exception_source  = proxy >> str
            exception_class   = proxy >> str
            exception_args    = proxy >> str
            future_id         = proxy >> int

            WARN_MSG("Exception from %s: %s" % (exception_source, exception_class))

            if future_id != -1:
                EntitiesDispatcher().yield_rmi_exception(future_id, exception_class, exception_args)

        await asyncio.sleep(0.1)
        # await self.client_connection.send(b"lolz")

