import asyncio

import sys
from typing import TypeVar, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from Core.Type import TypeBase

from Core import INFO_MSG
from Core.Declarators.Specs import Transactional, Replicated
from Core.Logging import LOCK_LOG, ERROR_MSG, WARN_MSG
from Core.intrinsic.Serialization import BinarySerialization


class SliceReplicationKind:
    Full = 0
    Clear = 1
    EditEntry = 2
    Add = 3
    RemoveEntry = 4
    Extend = 5
    Nop = 255  # using in replication context

class SliceReplicationDataType:
    Map = 0
    Array = 1


class PropertyMetadata(object):
    def __init__(self, prop_type, *specifiers):
        self.specifiers = specifiers
        self.prop_type: 'TypeBase' = prop_type
        self.outer_class_frame = sys._getframe(1)
        self.default = None
        self.comment = None
        self.line_number = -1
        self.source = "inline"
        self.has_default = False
        self.__doc__ = None


    def __contains__(self, item):
        return item in self.specifiers

    def __repr__(self):
        return "<%s of %s>" % (self.__class__.__name__, self.prop_type.get_type_name())

    def set_default(self, default):
        self.default = default

    def set_comment(self, comment):
        self.comment = comment

    def set_line_number(self, lnum):
        self.line_number = lnum

    def set_has_default(self):
        self.has_default = True

    def set_source(self, src):
        self.source = src

    def __matmul__(self, new_doc):
        self.__doc__ = new_doc
        return self


class DatabaseVariableProxy():
    def __init__(self, db, owner_dbid, owner_class_name, owner_property_name, prop_info):
        self.db = db
        self.owner_dbid = owner_dbid
        self.owner_class_name = owner_class_name
        self.owner_property_name = owner_property_name
        self.prop_info = prop_info

    async def async_set_value(self, value):
        INFO_MSG("saving", self.owner_dbid, self.owner_class_name, self.owner_property_name, self.prop_info.prop_type.get_type_name())
        from Core.BaseEntity import BaseEntity
        if isinstance(value, BaseEntity):
            from Core.LocalDatatypes import int32
            await self.db.UpdateEntityVariable(self.owner_dbid, self.owner_class_name, self.owner_property_name, 'int32', int32(value.dbid).serialize())
        else:
            await self.db.UpdateEntityVariable(self.owner_dbid, self.owner_class_name, self.owner_property_name, self.prop_info.prop_type.get_type_name(), value.serialize())

class ClientVariableProxy():
    def __init__(self, client, entity_id, owner_property_name, with_partial_replication=False):
        self.entity_id = entity_id
        self.client = client
        self.owner_property_name = owner_property_name
        self.with_partial_replication = with_partial_replication

    # noinspection PyTypeChecker
    def replicate_value(self, value):
        if not self.with_partial_replication or not value.replication_buffer:
            serialized = value.serialize()
            self.client.UpdateClientEntityVariable(self.entity_id, self.owner_property_name, serialized)
        else:
            sr = BinarySerialization()
            sr << SliceReplicationDataType.Map
            for rep_kind, rep_data in value.replication_buffer:
                if rep_kind == SliceReplicationKind.Nop:
                    continue

                sr << rep_kind
                if rep_kind == SliceReplicationKind.Full:
                    sr << value.serialize()
                elif rep_kind == SliceReplicationKind.Clear:
                    pass
                elif rep_kind == SliceReplicationKind.EditEntry:
                    sr << value.serialize_entry(rep_data)
                elif rep_kind == SliceReplicationKind.RemoveEntry:
                    sr << value.serialize_key(rep_data[0])
            self.client.UpdateClientEntityVariableSlice(self.entity_id, self.owner_property_name, sr.get_archive())



    def replicate_value_to(self, value, other_entity):
        serialized = value.serialize()
        other_entity.ue4client.UpdateClientEntityVariable(self.entity_id, self.owner_property_name, serialized)

class DatabaseStorageEntryProxy():
    def __init__(self, db, class_name, property_name, prop_info):
        self.db = db
        self.owner_class_name = class_name
        self.owner_property_name = property_name
        self.prop_info = prop_info

    # async def async_set_value(self, value):
    #     INFO_MSG("saving", self.owner_class_name, self.owner_property_name, self.prop_info.prop_type.get_type_name())
    #     await self.db.UpdateStorageEntry(self.owner_class_name, self.owner_property_name, self.prop_info.prop_type.get_type_name(), value.serialize())


class PropertyMcs(type):

    T = TypeVar('T')
    def __getitem__(self: T, specifiers) -> T:
        self.outer_class_frame = sys._getframe(1)
        if specifiers is Ellipsis:
            return PropertyMetadata(self)

        if not isinstance(specifiers, tuple):
            specifiers = specifiers,
        return PropertyMetadata(self, *specifiers)

    def __matmul__(self, other):
        raise NotImplementedError()

    # def __matmul__(self, other):
    #     return self[...].__matmul__(other)


class Property(
    metaclass=PropertyMcs
):
    def destroy_property(self):
        for inf in ['_db_interface', '_client_interface', '_owner', '_property_name']:
            if hasattr(self, inf):
                delattr(self, inf)

    @property
    def db_interface(self) -> DatabaseVariableProxy:
        return getattr(self, '_db_interface', None)

    @property
    def client_interface(self) -> ClientVariableProxy:
        return getattr(self, '_client_interface', None)

    @property
    def locked(self):
        return getattr(self, '_locked', False)
        # return self.get_lock().locked()

    def get_lock(self):
        return self.owner.properties_locks[self.property_name]

    async def waitforunlock(self):
        if self.locked:
            await asyncio.sleep(0.1)


    async def lock(self, locker):
        # LOCK_LOG("Locking %s by %s (%s)" % (self.property_name, locker, id(self.get_lock())))
        self._locked = True
        # self._locker = locker
        # if self.locked:
        #     LOCK_LOG("Unable to lock, waiting for unlock")
        #     await self.get_lock()
        # await self.get_lock().acquire()

    @property
    def locker(self):
        return None
        # LOCK_LOG("Getting locker of %s (%s)" % (self.property_name, id(self.get_lock())))
        # if not hasattr(self, '_locker'):
        #     return None
        # return self._locker

    @locker.setter
    def locker(self, new_locker):
        self._locker = new_locker

    def do_unlock(self):
        self.get_lock().release()

    async def do_lock(self):
        await self.get_lock().acquire()

    def unlock(self):
        self._locked = False
        # if not self.locked:
        #     ERROR_MSG("Already unlocked")
        # LOCK_LOG("Releasing lock of %s with locker %s" % (self.property_name, self.locker))
        # self.do_unlock()
        # if self.locked:
        #     LOCK_LOG("... Unable to unlock")
        # # LOCK_LOG("Deleting locker of %s" % id(self.get_lock()))
        # del self._locker

    def initialize_property(self, owner, property_name):
        self._owner = owner
        self._property_name = property_name
        self._replication_buffer = list()
        self.initialized = True

    def flush_replication_buffer(self):
        self._replication_buffer.clear()

    @property
    def replication_buffer(self):
        if not hasattr(self, '_replication_buffer'):
            self._replication_buffer = list()
        return self._replication_buffer

    @replication_buffer.setter
    def replication_buffer(self, value):
        self._replication_buffer = value

    @property
    def is_property_initialized(self):
        return getattr(self, 'initialized', False)

    async def async_set(self, value):
        # if self.locked:
        #     await self.get_lock()
        # await self.lock(self.owner)
        if hasattr(self, "_owner"):
            setattr(self._owner, self._property_name, value)
        if self.db_interface:
            await self.db_interface.async_set_value(self)
        self.unlock()
        if self.client_interface:
            self.client_interface.replicate_value(self)
        self.replicate()

    def sync(self):
        async def action():
            await self.async_set(self)
            self.flush_replication_buffer()
        asyncio.Task(action())

    @property
    def owner(self):
        return getattr(self, '_owner', None)

    @property
    def property_name(self):
        return getattr(self, '_property_name', None)

    def set_db_interface(self, db_interface):
        self._db_interface = db_interface

    def set_client_interface(self, client_interface):
        self._client_interface = client_interface

    def save(self):
        if self.db_interface:
            asyncio.Task(self.db_interface.async_set_value(self))
        self.replicate()

    async def async_save(self):
        if self.locked:
            await self.get_lock()

        await self.lock(self.owner)
        if self.db_interface:
            await self.db_interface.async_set_value(self)
        self.unlock()
        if self.client_interface:
            self.client_interface.replicate_value(self)
        self.replicate()

    def replicate(self):
        if self.owner is None:
            raise RuntimeError("Something went wrong")
        if Replicated in self.owner.properties[self.property_name]:
            if self.client_interface:
                # INFO_MSG(f"Replicated {self.property_name}")
                self.client_interface.replicate_value(self)
            # else:
            #     WARN_MSG(f"Replication failed: Cannot find client interface for {self.property_name}!")

    def rep_to(self, other_entity):
        if self.owner is None:
            raise RuntimeError("Something went wrong")
        if Replicated in self.owner.properties[self.property_name]:
            if self.client_interface:
                self.client_interface.replicate_value_to(self, other_entity)

    def get_specs(self):
        if self.owner:
            return self.owner.properties[self.property_name].specifiers
        return tuple()

    @property
    def is_transactional(self):
        return Transactional in self.get_specs()
