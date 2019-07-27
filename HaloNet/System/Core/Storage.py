import hashlib

import json

from Core.Entity import Entity
from Core.Globals import Globals
from Core.intrinsic.Serialization import BinarySerialization
from Core.Type import TArray
from Core.Utils import is_valid

from Core.Common.JSONHaloNetEncoder import JSONHaloNetEncoder

class Storage(Entity):
    entity_type = "base"

    def __init_subclass__(cls, **kwargs):
        pass
        # print('reg storage')
        # cls.register_typename("storage", cls.__name__, cls)
        # cls.register_all_methods()
        # cls.register_all_properties()

    async def __ainit__(self, storage_name, storage_type, primary_key):
        self.type = storage_type
        self.name = storage_name
        self.primary_key = primary_key
        self.db = Globals.this_service.db
        self.failed = False
        self.data = dict()
        self.data_as_list = list()
        self.indices = set()
        self.md5hash = None
        Storages.new_storage(self)
        await super().__ainit__()

    def __repr__(self):
        return "<Storage object %s>" % (getattr(self, 'name', "Undefined"))

    async def __apostinit__(self):
        await self.load_table()
        await super().__apostinit__()

    def __isvalid__(self):
        return super().__isvalid__() and not self.failed

    def get(self):
        return self.data_as_list

    def get_by(self, field_name, value):
        if field_name == self.primary_key:
            return self.data.get(value, None)

        for entry in self.data_as_list:
            if entry[field_name] == value:
                return entry

    def get_all_by(self, field_name, value):
        return list(filter(lambda data: data[field_name] == value, self.get()))

    async def load_table(self):
        if not is_valid(self.db):
            self.failed = True
            return

        class_name = self.type.__name__
        T = self.find_type(class_name)
        serialized_data = await self.db.GetStorageData(self.name, class_name)
        # self.md5hash = hashlib.md5(serialized_data).hexdigest()
        self.data_as_list = TArray[T].deserialize(serialized_data)

        data = json.loads(json.dumps(self.data_as_list, cls=JSONHaloNetEncoder))
        import pickle
        self.md5hash = hashlib.md5(pickle.dumps(data)).hexdigest()

        self.data = dict()
        for entry in self.data_as_list:
            if self.primary_key in entry:
                self.data[entry[self.primary_key]] = entry
                self.indices.add(entry[self.primary_key])
            else:
                self.primary_key = list(entry.keys())[0]
                self.data[entry[self.primary_key]] = entry
                self.indices.add(entry[self.primary_key])


        # srp = BinarySerialization(serialized_data_array).proxy()
        # for prop_name, prop_info in self.properties.items():
        #     prop_value = srp >> bytes
        #     value = prop_info.prop_type(prop_info.prop_type.deserialize(prop_value))
        #     value.set_db_interface(DatabaseVariableProxy(self.db, self.dbid, class_name, prop_name, prop_info))
        #     self.set_property_value(prop_name, value)

    # def save_all(self):
    #     for v in self.properties_values.values():
    #         v.save()
    #
    # async def async_save_all(self):
    #     for v in self.properties_values.values():
    #         await v.async_save()


class StorageMcs(type):
    def __getitem__(cls, item) -> Storage:
        return cls.storages[item]
    
    


class Storages(metaclass=StorageMcs):
    storages = dict()

    @classmethod
    def new_storage(cls, storage):
        cls.storages[storage.name] = storage