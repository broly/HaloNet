from copy import copy
from functools import partial

import asyncio
from typing import List

from Core import ERROR_MSG, INFO_MSG, WARN_MSG
from Core.AsyncObj import AsyncObj
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator
from Core.ConfigSystem.AppsConfig import AppConfig
from Core.GlobalManagers import FuturesManager
from Core.EntityProxy import EntityProxy
from Core.Globals import Globals
from Core.intrinsic.Serialization import BinarySerialization, SerializationError
from Core.TCP.TestProtocolClient import TCPClient
from Core.Utils import ConnectionMessageTypes, is_valid, async_time_it, time_it


class MailboxBase(EntityProxy):
    initialized_flag = False

    async def get_connection_and_endpoint_with_lost_callback(self, endpoint_or_connection):
        INFO_MSG("endpoint_or_connection")
        if isinstance(endpoint_or_connection, TCPClient):
            endpoint = endpoint_or_connection.endpoint
            client_connection = endpoint_or_connection
            client_connection.add_lost_callback(self.on_connection_lost)
        else:
            endpoint = endpoint_or_connection
            client_connection = await self.service.create_client_connection(tuple(endpoint_or_connection), on_lost=self.on_connection_lost)
        return client_connection, endpoint

    def set_id(self, new_id):
        self.remote_id = new_id

    def __repr__(self):
        return "<Unknown mailbox>"

    def send_data(self, msg):
        raise NotImplementedError()

    def destroy(self):
        raise NotImplementedError()

    def set_service_info(self, entity_typename):
        if ConfigurationGenerator().generated_entities_info.has_entity(entity_typename):
            self.entity_info = ConfigurationGenerator().generated_entities_info.get_by_name(entity_typename)
            self.context_name = AppConfig.context_by_name[entity_typename]

    def on_connection_lost(self, connection):
        raise NotImplementedError()


    def send_method_call(self, method_index, future_id, *args, **kwargs):
        if not self:
            WARN_MSG("Call to invalid mailbox %s" % self, depth=1)
            return

        method_info = self.entity_info.get_method(self.context_name, method_index)
        params, _ = method_info.signature
        name = method_info.name

        serialized_params = BinarySerialization()

        for param_index, (param_name, param_type) in enumerate(params):
            param = param_type.instantiate(args[param_index])
            serialized_params << param.serialize()

        serialized_call = BinarySerialization()
        serialized_call << self.remote_id
        serialized_call << Globals.generator_signature
        serialized_call << method_index
        serialized_call << future_id
        serialized_call << Globals.access_token
        serialized_call << serialized_params

        message = BinarySerialization()
        message << ConnectionMessageTypes.rmi_call
        message << serialized_call

        self.send_data(message.get_archive())

    def as_exposed(self):
        mb = self.instantiate(self)
        mb.endpoint = Globals.this_service.exposed_ip, mb.endpoint[1]
        mb.entity_info = self.entity_info
        mb.is_exposed_mailbox = True

        return mb

    async def async_method_caller(self, method_index, *args, **kwargs):
        if not self: return \
            WARN_MSG("Awaiting call to invalid mailbox %s" % self, depth=1)

        future_data = FuturesManager().new(self, method_index)
        self.send_method_call(method_index, future_data['future_id'], *args)
        return await future_data['future']

    def method_caller(self, method_index, *args, **kwargs):
        if not self: return \
            ERROR_MSG("Call to invalid mailbox %s" % self, depth=1)

        self.send_method_call(method_index, -1, *args)

    async def done_caller(self, future, method_index, retdata):
        # INFO_MSG("Future %i preparing to done" % method_index)
        # method = self.entity_class.get_method_by_id(method_index)

        method = self.entity_info.get_method(self.context_name, method_index)
        _, returns = method.signature

        serialized_rets = BinarySerialization(retdata)
        rets = tuple()
        for param_index, ret_type in enumerate(returns):
            try:
                ret = ret_type.deserialize(serialized_rets.get_data()[param_index])
            except SerializationError:
                ERROR_MSG(f"Failed to return result by method {method.name}, return value {param_index} invalid")
                raise
            if isinstance(ret, AsyncObj):
                ret = await ret
            rets += ret,

        if len(rets) == 1:
            rets = rets[0]

        try:
            future.set_result(rets)
        except asyncio.InvalidStateError:
            ERROR_MSG(f"Failed to done future {future} (of method {method}), retdata: {retdata}")

    def __getattr__(self, item):
        if self.initialized_flag:
            method = self.entity_info.find_method(self.context_name, item)
            if method:
                if method.is_async:
                    return partial(self.async_method_caller, method.id)
                else:
                    return partial(self.method_caller, method.id)

    def __eq__(self, other):
        if isinstance(other, Mailbox):
            return other.get_endpoint() == self.get_endpoint()
        return False

    def __ne__(self, other):
        if isinstance(other, Mailbox):
            return not self == other
        return False

    def __hash__(self):
        return tuple(self.endpoint).__hash__() if self.endpoint else ().__hash__()

    def get_id(self):
        return self.remote_id

    def get_class_name(self):
        return self.entity_info.entity_name

    def get_endpoint(self):
        return self.endpoint

    def get_context(self):
        return self.context_name


class Mailbox(AsyncObj, MailboxBase):
    async def __ainit__(self, context_name, entity_typename, endpoint_or_connection, remote_id, existent_endpoint_and_connection=None):
        INFO_MSG("")
        self.remote_id = remote_id
        self.client_connection: TCPClient

        if existent_endpoint_and_connection is None:
            self.client_connection, self.endpoint = await self.get_connection_and_endpoint_with_lost_callback(endpoint_or_connection)
        else:
            self.client_connection, self.endpoint = existent_endpoint_and_connection

        self.initialized_flag = True

        self.context_name = context_name
        self.entity_typename = entity_typename
        self.entity_info = ConfigurationGenerator().generated_entities_info.get_by_name(entity_typename)
        self.lost_callbacks = []

    def __repr__(self):
        if not self.async_initialized:
            return f"<Mailbox {self.async_state}>"
        else:
            return "<Mailbox object id=%i, connection=%s>" % (self.remote_id, self.client_connection)

    def __isvalid__(self):
        return super().__isvalid__() and \
               is_valid(self.client_connection)

    def send_data(self, msg):
        self.client_connection.send(msg)

    def destroy(self):
        self.client_connection.destroy()

    def on_connection_lost(self, connection):
        [
            lcb()
            for lcb in self.lost_callbacks if callable(lcb)
        ]
        self.lost_callbacks.clear()

    def add_lost_callback(self, callback):
        self.lost_callbacks.append(callback)

    def __lshift__(self, other):
        self.add_lost_callback(other)

    def clear_lost_callbacks(self):
        self.lost_callbacks = list()


class InvalidMailbox(MailboxBase):
    def __repr__(self):
        return "<InvalidMailbox (not usable for this context)>"

    def create_client_connection(self, endpoint, on_lost=None):
        raise NotImplementedError()

    def on_connection_lost(self, connection):
        raise NotImplementedError()

    def send_method_call(self, method_index, future_id, *args, **kwargs):
        raise RuntimeError("Call to invalid mailbox")

    def send_data(self, msg):
        raise NotImplementedError()

    def destroy(self):
        raise NotImplementedError()

    def __bool__(self):
        return False


class MulticastMailbox(MailboxBase):
    def destroy(self):
        pass  # todo: review please

    def __init__(self, context_name, entity_typename, remote_id):
        self.remote_id = remote_id
        self.initialized_flag = True
        self.context_name = context_name
        self.entity_typename = entity_typename
        self.entity_info = ConfigurationGenerator().generated_entities_info.get_by_name(entity_typename)
        self.lost_callbacks = []
        self.clients_connections: List[TCPClient] = []


    def __repr__(self):
        if not self.async_initialized:
            return f"<MulticastMailbox {self.async_state}>"
        else:
            return "<MulticastMailbox object id=%i, subscribers=%s>" % (self.remote_id, self.clients_connections)

    async def subscribe_connection(self, endpoint_or_connection_or_mailbox):
        INFO_MSG("Subscribing")
        endpoint_or_connection = endpoint_or_connection_or_mailbox
        if isinstance(endpoint_or_connection_or_mailbox, Mailbox):
            endpoint_or_connection = endpoint_or_connection_or_mailbox.client_connection

        client_connection, _ = await self.get_connection_and_endpoint_with_lost_callback(endpoint_or_connection)
        self.clients_connections.append(client_connection)

    def unsubscribe_connection(self, endpoint_or_connection_or_mailbox):
        endpoint_or_connection = endpoint_or_connection_or_mailbox
        if isinstance(endpoint_or_connection_or_mailbox, Mailbox):
            endpoint_or_connection = endpoint_or_connection_or_mailbox.client_connection
        if endpoint_or_connection in self.clients_connections:
            self.clients_connections.remove(endpoint_or_connection)

    def clear_connections(self):
        self.clients_connections.clear()

    def on_connection_lost(self, connection):
        if connection in self.clients_connections:
            self.clients_connections.remove(connection)

    def send_data(self, msg):
        for connection in self.clients_connections:
            connection.send(msg)

    async def async_method_caller(self, method_index, *args, **kwargs):
        raise RuntimeError("Call to 'async' method of Muilticast mailbox")
