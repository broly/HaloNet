import asyncio
from typing import Dict, TYPE_CHECKING

from Core import WARN_MSG, ERROR_MSG, INFO_MSG
# from Core.Entity import Entity
from Core.ExceptionsRegistry import ExceptionsRegistry
from Core.Utils import error
from Core.Common.Helpers import Singleton

if TYPE_CHECKING:
    from Core.Entity import Entity
    from Core.Service import Service


class FuturesManager(metaclass=Singleton):
    def __init__(self):
        self.futures = dict()
        self.next_future_id = 0

    def new_fid(self):
        fid = self.next_future_id
        self.next_future_id += 1
        return fid

    def new(self, mailbox, method_id):
        # INFO_MSG("Future created: %s, %i" % (mailbox, method_id))
        if not mailbox:
            return None

        future = asyncio.Future(loop=asyncio.get_event_loop())
        future_id = self.new_fid()
        future_data = self.futures[future_id] = {
            'future': future,
            # 'method': method,
            'method_id': method_id,
            'mailbox': mailbox,
            'future_id': future_id
        }
        return future_data

    def has_future(self, future_id, remote_entity_id, method_index):
        future_dict = self.futures.get(future_id, None)
        if future_dict is not None:
            if future_dict['method_id'] == method_index and future_dict['mailbox'].remote_id == remote_entity_id:
                return True
        WARN_MSG("Unable to get future with id %i, entity id %i and method index %i" % (future_id, remote_entity_id, method_index))
        return False

    def try_done(self, future_id, remote_entity_id, method_index, returns_data):
        # INFO_MSG("Tried done: %i, %i, %i" % (future_id, remote_entity_id, method_index))
        if self.has_future(future_id, remote_entity_id, method_index):
            caller = self.futures[future_id]['mailbox'].done_caller(self.futures[future_id]['future'], method_index, returns_data)
            asyncio.Task(caller)

    def try_error(self, future_id):

        from Core.ClientConnectionHandler import RemoteServerException
        future_data = self.futures.get(future_id, None)
        if future_data is not None:
            future_data['future'].set_exception(RemoteServerException())

    def try_exc(self, future_id, cls_name, args):
        future_data = self.futures.get(future_id, None)
        if future_data is not None:
            exception_class = ExceptionsRegistry.find(cls_name)
            if exception_class is not None:
                future_data['future'].set_exception(exception_class(args))
            else:
                ERROR_MSG("Invalid incoming exception %s" % cls_name)
                from Core.ClientConnectionHandler import RemoteServerException
                future_data['future'].set_exception(RemoteServerException())



    # def done(self, future_id, data):
    #     self.futures[future_id].set_result(result)


class EntitiesDispatcher(metaclass=Singleton):
    entities: Dict[int, 'Entity'] = dict()
    entities_by_dbid: Dict[int, 'Entity'] = dict()
    main: 'Service' = None
    id_counter = 1

    def register_new(self, obj):
        self.__register_default(obj) \
            if not obj.is_main_entity else  \
            self.__register_main(obj)

    async def execute_rmi(self, executor_connection, entity_id, method_index, future_id, access_token, params):
        entity = self.entities.get(entity_id, None)
        if entity is None:
            ERROR_MSG("Failed to call rmi %i. Entity with id %i not exists!" % (method_index, entity_id))
            return

        try:
            await entity.execute_rmi(executor_connection, method_index, future_id, access_token, params)
        except Exception as exc:
            ERROR_MSG("Failed to execute rmi on %s" % (entity))
            from traceback import print_exc
            print_exc()
            entity.send_exception(executor_connection, exc, future_id)
            return

    def remote_response_error(self, executor_connection, entity_id, future_id, error_message):
        entity = self.entities.get(entity_id, None)
        if entity:
            entity.send_error(executor_connection, error_message, future_id)

    def yield_rmi_result(self, future_id, remote_entity_id, method_index, returns_data):
        # INFO_MSG("Got return values %i %i %i %s" % (future_id, remote_entity_id, method_index, returns_data))
        FuturesManager().try_done(future_id, remote_entity_id, method_index, returns_data)

    def yield_rmi_error(self, future_id):
        FuturesManager().try_error(future_id)

    def yield_rmi_exception(self, future_id, exc, args):
        FuturesManager().try_exc(future_id, exc, args)

    def __register_default(self, obj):
        self.entities[self.id_counter] = obj
        obj.set_internal_id(self.id_counter)
        self.id_counter += 1

    def __register_main(self, obj):
        assert self.main is None or error("Cannot dispatch more than one main entities per executable!")
        self.main = obj
        self.entities[0] = obj
        obj.set_internal_id(0)

    def get_by_dbid(self, dbid):
        return self.entities_by_dbid.get(dbid, None)

    def register_dbid(self, obj, dbid):
        self.entities_by_dbid[dbid] = obj

    def destroy_entity_by_id(self, entity_id):
        if entity_id in self.entities:
            del self.entities[entity_id]

    def destroy_entity(self, entity):
        if entity.internal_id in self.entities:
            del self.entities[entity.internal_id]
        if hasattr(entity, 'dbid') and entity.dbid in self.entities_by_dbid:
            del self.entities_by_dbid[entity.dbid]