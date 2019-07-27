import os
from functools import partial
from time import time
from traceback import print_exc
from typing import Dict, TypeVar, Type, Union, List
import sys

from pathlib import Path

import asyncio

from Core import ERROR_MSG, INFO_MSG, Log, WARN_MSG
from Core.Access import AccessLevel, Access
from Core.AsyncObj import AsyncObj, AsyncObjMcs
from Core.Common.Colors import Color
from Core.Declarators.Specs import CaptureConnection, Replicated, CaptureAccessToken, DisplayThis, \
    PartialRep_EXPERIMENTAL, Exposed
from Core.EntityProxy import EntityProxy
from Core.GlobalManagers import EntitiesDispatcher
from Core.Globals import Globals
from Core.Mailbox import Mailbox, InvalidMailbox, MulticastMailbox
from Core.Property import PropertyMetadata, ClientVariableProxy
from Core.intrinsic.Serialization import BinarySerialization, SerializationError
from Core.Type import MailboxProxyDatatype, TypeBase
from Core.Utils import error, ConnectionMessageTypes, get_file_line, get_annotation_comment_and_line_by_source, \
    call_later, profile_it, async_profile_it, time_it, async_time_it

UNDEFINED_ID = -1

MailboxProxyDatatype.mailbox_class = Mailbox

CALL_INFO_MSG = Log("CALL INFO", None, Color.LightGray, enabled=False)


class ScopeTimeCounter:
    def __init__(self, name):
        self.name = name
        self.t = time()

    def __del__(self):
        print(f'{self.name} done at {time() - self.t}')

class AsyncObjEntityMcs(AsyncObjMcs):
    def __new__(cls, *args, **kwargs):
        entity_class = AsyncObjMcs.__new__(cls, *args, **kwargs)
        frame_info = sys._getframe(1)
        entity_class.inspect_info = get_file_line(frame_info)
        return entity_class


class Entity(AsyncObj, EntityProxy, metaclass=AsyncObjEntityMcs):
    is_main_entity = False
    is_exposed = True
    is_client_side = False
    is_contextual = False
    base_entity_class = None
    context_name = "Unknown"
    display_attributes = tuple()

    is_multicast = False

    __modulepath__ = None


    rmi_methods = dict()
    rmi_mapping = dict()

    properties: Dict[str, PropertyMetadata] = dict()

    def __repr__(self):
        if not self.async_initialized:
            return f"<{self.__class__.__name__} {self.async_state}>"
        return f"<Entity {self.__class__.__name__}{' [DESTROYED]' if self.pending_destroy else ''} id={self.internal_id}, '{self.context_name}', {'multicast' if  self.is_multicast else 'with client'}>"

    def __init_subclass__(cls, **kwargs):
        cls.register_typename(cls.context_name, cls.__name__, cls)
        # s= os.path.abspath(sys.modules[cls.__module__].__file__)
        # if Globals.IsInGenerator:
        if getattr(cls, 'entity_type', None) != 'service':
            if cls.context_name.lower() != "unknown":
                cls.__modulepath__ = str(Path(os.getcwd()).parent.joinpath("Entities").joinpath(cls.context_name).joinpath(cls.__name__ + ".py"))


        cls.register_all_methods()
        cls.register_all_properties()
        # SymbolsRegistry().register_entity_type(cls)

    async def __ainit__(self, *args, **kwargs):
        await AsyncObj.__ainit__(self)
        self.pending_destroy = False
        self.timer_to_destroy = None
        self.subscribed_clients = list()
        self.subscribed_entities = set()
        self.properties_values = dict()
        self.internal_id = UNDEFINED_ID
        self.client = InvalidMailbox()
        self.timers: List[asyncio.TimerHandle] = list()
        if self.is_multicast:
            self.all_clients = MulticastMailbox("ue4", self.__class__.__name__, remote_id=-1)
            self.all_clients_apps = MulticastMailbox("ue4", "UE4App", remote_id=0)
        else:
            self.all_clients = InvalidMailbox()
            self.all_clients_apps = InvalidMailbox()
        EntitiesDispatcher().register_new(self)

        for prop_name, prop_meta in self.properties.items():
            if not issubclass(prop_meta.prop_type, Entity):
                default_value = prop_meta.prop_type.instantiate()
                setattr(self, prop_name, default_value)

    def get_client_interface(self):
        return self.all_clients if self.is_multicast else self.client

    async def __apostinit__(self):
        # await self.init_done()
        await self.begin_play()

    # async def init_done(self):
    #     await self.begin_play()

    async def begin_play(self):
        pass

    def end_play(self):
        pass

    def destroy(self):
        if not self.pending_destroy:
            from traceback import print_stack
            #print_stack()
            INFO_MSG(f"Entity {self.internal_id} pending destroy")
            self.end_play()

            for client in self.subscribed_clients:
                if client:
                    client.DestroyClientEntity(self.internal_id)

            EntitiesDispatcher().destroy_entity(self)

            self.pending_destroy = True

            for prop_name in self.properties.keys():
                delattr(self, prop_name)
            self.properties_values = dict()
            self.properties_locks = dict()

        [timer.cancel() for timer in self.timers]
        self.timers.clear()

    def call_later(self, func, secs):
        timer = call_later(func, secs)
        self.timers.append(timer)
        return timer

    def set_internal_id(self, internal_id):
        self.internal_id = internal_id
        if self.is_multicast:
            self.update_multicast_mailbox()

    def update_multicast_mailbox(self):
        self.all_clients.set_id(self.internal_id)

    def __isvalid__(self):
        return super().__isvalid__() and \
               self.internal_id != UNDEFINED_ID

    T = TypeVar('T')
    @classmethod
    async def make_mailbox(cls: Type[T], context_name, entity_typename, endpoint_or_connection, *, remote_id=0) -> Union[T, Mailbox]:
        mailbox = await Mailbox(context_name, entity_typename, endpoint_or_connection, remote_id)
        return mailbox

    @classmethod
    async def mailbox_cast(cls, other_mailbox: Mailbox):
        mailbox = await Mailbox(other_mailbox.context_name,
                                other_mailbox.entity_typename,
                                None,
                                other_mailbox.remote_id,
                                (other_mailbox.client_connection, other_mailbox.endpoint))
        return mailbox


    @classmethod
    def register_rmi_method(cls, method):
        if not method.__name__ in cls.rmi_mapping:
            id = len(cls.rmi_methods)
            cls.rmi_methods[id] = method
            cls.rmi_mapping[method.__name__] = id
            return id

    @classmethod
    def register_all_methods(cls):
        cls.rmi_methods = dict(cls.rmi_methods)
        cls.rmi_mapping = dict(cls.rmi_mapping)
        methods_to_register = getattr(cls, 'methods_to_register', list())
        for method in methods_to_register:
            cls.register_rmi_method(method)

    @classmethod
    def get_annotations(cls):
        res = dict()
        for base in (cls.__bases__ + (cls,)):
            if hasattr(base, '__annotations__'):
                res.update(base.__annotations__)
        return res

    @classmethod
    def serializable_value(cls, *value):
        return 0

    @classmethod
    def register_property(cls, name, T, default):
        if isinstance(T, type) and issubclass(T, TypeBase):
            T = PropertyMetadata(T)
        if isinstance(T, PropertyMetadata):

            data = get_annotation_comment_and_line_by_source(cls, name, cls.__modulepath__)
            if data:
                comment, lnum = data
                T.set_comment(comment)
                T.set_line_number(lnum)
                T.set_source(cls.__modulepath__)

            if default is not None:
                T.set_has_default()

            if default is not None:
                T.set_default(T.prop_type.serializable_value(default))
            else:
                if issubclass(T.prop_type, Entity):
                    T.set_default(None)
                else:
                    T.set_default(T.prop_type.serializable_value())
            cls.properties[name] = T

            cls.create_property(name)

    @classmethod
    def register_all_properties(cls):
        cls.properties: Dict[str, PropertyMetadata] = dict(cls.properties)
        for key, value in cls.get_annotations().items():
            if isinstance(value, TypeBase) or isinstance(value, PropertyMetadata):
                default_value = getattr(cls, key, None)
                cls.register_property(key, value, default_value)
            if isinstance(value, int):
                value = [value]

            if isinstance(value, list):
                if DisplayThis in value:
                    cls.display_attributes += key,

    @classmethod
    def create_property(cls, property_name):
        def setter(self, in_value):
            old = self.get_property_value(property_name)
            if old.is_transactional and not old.locked:
                raise ValueError("Only in transactions 'Transactional' properties can be changed")
            T = old.__class__
            from Core.LocalDatatypes import int32
            if property_name == "CityInstance" and issubclass(T, int32):
                ERROR_MSG("OMG!")
            db_interface = old.db_interface
            client_interface = old.client_interface
            try:
                in_value = T.instantiate(in_value)
            except TypeError:
                print('...')
            in_value.set_db_interface(db_interface)
            in_value.set_client_interface(client_interface)
            in_value.initialize_property(self, property_name)
            in_value._locked = old.locked
            if old.is_transactional:
                in_value.locker = old.locker
            self.set_property_value(property_name, in_value)
            if not in_value.locked:
                in_value.replicate()

        def getter(self):
            return self.get_property_value(property_name)

        def deleter(self):
            self.destroy_property()

        setattr(cls, property_name, property(getter, setter, deleter))

    def set_property_value(self, key, value):
        self.properties_values[key] = value

    def get_property_value(self, key):
        return self.properties_values.get(key, self.properties[key].default)

    @classmethod
    def get_method_by_id(cls, id):
        method = cls.rmi_methods.get(id, None)
        assert method is not None or error("Failed to get method by id %i" % id)
        return method

    @classmethod
    def get_method_id(cls, method):
        for key, value in cls.rmi_methods:
            if value == method:
                return key
        else:
            return None

    async def execute_rmi(self, executor_connection, method_index, future_id, access_token, params_data):
        method = self.get_method_by_id(method_index)

        CALL_INFO_MSG("Call method %s" % method)
        params, returns, defaults = method.rmi_signature

        serialized_params = BinarySerialization(params_data)
        args = list()
        data = serialized_params.get_data()

        if len(params) != len(data):
            raise SerializationError(f"Signature mismatch: formal parameters count are not equals to serialized {method}, {executor_connection.endpoint}")

        for param_index, (param_name, param_type) in enumerate(params):
            arg = param_type.deserialize(serialized_params.get_data()[param_index])
            if isinstance(arg, AsyncObj):
                arg = await arg
            args.append(arg)

        if CaptureConnection in method.rmi_specifiers['specifiers']:
            args = [executor_connection] + args

        if CaptureAccessToken in method.rmi_specifiers['specifiers']:
            args = [access_token] + args


        access_level = method.rmi_specifiers['kwspecifiers'].get('access', AccessLevel.Internal)
        if not Access().has_access(access_token, access_level):
            err = "call to %s. Access denied!" % method
            ERROR_MSG(err)
            self.send_error(executor_connection, err, future_id)
            return

        if hasattr(self, "__rmi_firewall__"):
            error_message = self.__rmi_firewall__(method)
            if error_message:
                err = "call to forbidden method %s, reason:" % (method, error_message)
                ERROR_MSG(err)
                self.send_error(executor_connection, err, future_id)
                return


        if not method.rmi_specifiers['isasyncmethod']:
            method(self, *args)  # Call the method
        else:
            try:
                ret_data = await method(self, *args)  # Call the async method
            except Exception as e:
                print('lolz', method, args)
                raise

            if not isinstance(ret_data, tuple):
                ret_data = ret_data,

            if len(returns) > 0:
                assert len(ret_data) == len(returns) or error(f"Actual return values for method {method.__name__} count must be equals with formal return values count! {len(ret_data)}/{len(returns)}", do_break=True)

            serialized_returns = BinarySerialization()
            for ret_index, ret_type in enumerate(returns):
                if issubclass(ret_type, MailboxProxyDatatype):
                    if not ret_data[ret_index].is_exposed_mailbox and Exposed in method.rmi_specifiers['specifiers']:
                        ret = ret_type.instantiate(ret_data[ret_index]).as_exposed()
                    else:
                        ret = ret_type.instantiate(ret_data[ret_index])
                else:
                    ret = ret_type.instantiate(ret_data[ret_index])
                serialized_returns << ret.serialize()


            serialized_yield = BinarySerialization()
            serialized_yield << self.internal_id
            serialized_yield << method_index
            serialized_yield << future_id
            serialized_yield << serialized_returns

            message = BinarySerialization()
            message << ConnectionMessageTypes.rmi_future
            message << serialized_yield.get_archive()


            CALL_INFO_MSG(f"Send response for method {method} {message.get_archive()}")
            executor_connection.send(message.get_archive())


    def send_error(self, executor_connection, err, future_id):
        msg_data = BinarySerialization()
        msg_data << "%s[%i]:%s:%s" % (Globals.this_service.__class__.__name__,
                                      self.internal_id,
                                      Globals.this_service.endpoint[0],
                                      Globals.this_service.endpoint[1])
        msg_data << err
        msg_data << future_id

        message = BinarySerialization()
        message << ConnectionMessageTypes.rmi_error
        message << msg_data

        executor_connection.send(message.get_archive())

    def send_exception(self, executor_connection, exc, future_id):
        assert isinstance(exc, Exception)

        msg_data = BinarySerialization()
        msg_data << "%s[%i]:%s:%s" % (Globals.this_service.__class__.__name__,
                                      self.internal_id,
                                      Globals.this_service.endpoint[0],
                                      Globals.this_service.endpoint[1])
        msg_data << exc.__class__.__name__
        msg_data << ', '.join(exc.args)
        msg_data << future_id

        message = BinarySerialization()
        message << ConnectionMessageTypes.rmi_exception
        message << msg_data

        executor_connection.send(message.get_archive())


    def get_id(self):
        return self.internal_id

    def get_class_name(self):
        return self.__class__.__name__

    def get_endpoint(self):
        return self.service.endpoint

    def get_context(self):
        return Globals.context_name

    async def client_connected(self, client):
        client_mailbox = client if not self.is_multicast else self.all_clients_apps

        for name, prop_info in self.properties.items():
            var = getattr(self, name)
            if Replicated in prop_info.specifiers:
                var.initialize_property(self, name)
                var.set_client_interface(ClientVariableProxy(client_mailbox, self.internal_id, name, PartialRep_EXPERIMENTAL in prop_info.specifiers))

                var.replicate()

        if not self.is_multicast:
            self.client = await self.make_mailbox("ue4", self.__class__.__name__, client.client_connection, remote_id=self.internal_id )

        await self.on_client_connected()


    async def on_client_connected(self):
        pass

    def get_subscriber(self, access_token):
        for subscribed_entity in self.subscribed_entities:
            if getattr(subscribed_entity, "access_token", None) == access_token:
                return subscribed_entity

    def on_lost_subscriber(self, subscriber):
        subscriber_client = subscriber
        if isinstance(subscriber, Entity):
            subscriber_client = subscriber.ue4client
            if subscriber in self.subscribed_entities:
                self.subscribed_entities.remove(subscriber)
        if subscriber_client in self.subscribed_clients:
            self.subscribed_clients.remove(subscriber_client)

    async def subscribe(self, entity_or_client):
        client: Mailbox = entity_or_client
        if isinstance(entity_or_client, Entity):
            client = entity_or_client.ue4client  # todo: review it
            self.subscribed_entities.add(entity_or_client)

        client << partial(self.on_lost_subscriber, entity_or_client)

        if client in self.subscribed_clients and self.is_multicast:
            return WARN_MSG(f"{client} already subscribed to {self}")

        if len(self.subscribed_clients) > 1 and not self.is_multicast:
            self.subscribed_clients.clear()
            # return WARN_MSG(f"Cannot subscribe {client} to {self}. Already has connection")

        self.subscribed_clients.append(client)
        if self.is_multicast:
            await self.all_clients.subscribe_connection(client)
            await self.all_clients_apps.subscribe_connection(client)
        await client.CreateClientEntity(self.__class__.__name__, self.internal_id)
        await self.client_connected(client)
        INFO_MSG(f"Client {client} subscribed to {self}")

    def unsubscribe(self, entity_or_client):
        client: Mailbox = entity_or_client
        if isinstance(entity_or_client, Entity):
            client = entity_or_client.ue4client  # todo: review it
            if entity_or_client in self.subscribed_entities:
                self.subscribed_entities.remove(entity_or_client)

        if client in self.subscribed_clients:
            self.subscribed_clients.remove(client)
        if self.is_multicast:
            self.all_clients.unsubscribe_connection(client)
            self.all_clients_apps.unsubscribe_connection(client)

        client.DestroyClientEntity(self.internal_id)


    def rep_all_from(self, other_entity: 'Entity'):
        for prop_name, prop_meta in other_entity.properties.items():
            if Replicated in prop_meta:
                var = getattr(other_entity, prop_name)
                var.rep_to(self)

    def get_properties(self, *specifiers):
        out_properties = dict()
        for prop_name, prop_info in self.properties.items():
            if set(specifiers) <= set(prop_info.specifiers):
                out_properties[prop_name] = prop_info
        return out_properties

    def set_lifespan(self, time_to_destroy):
        self.reanimate()
        self.timer_to_destroy = call_later(self.destroy, time_to_destroy)

    def reanimate(self):
        if self.timer_to_destroy:
            self.timer_to_destroy.cancel()

Entity.register_all_methods()

