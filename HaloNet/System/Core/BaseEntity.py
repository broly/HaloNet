import asyncio

from Core.Declarators.Specs import Exposed, Persistent, Replicated, Transactional
from Core.Entity import Entity
from Core.GlobalManagers import EntitiesDispatcher
from Core.Globals import Globals
from Core.LocalDatatypes import int32
from Core.Property import DatabaseVariableProxy, ClientVariableProxy
from Core.intrinsic.Serialization import BinarySerialization
from Core.Transaction import Transaction
from Core.Type import TypeBase
from Core.Utils import is_valid


class BaseEntity(Entity, TypeBase):
    entity_type = "base"
    pg_spec = 'int4'
    context_name = "base"

    async def __ainit__(self, entity_dbid, *, outer=None):
        self.dbid = entity_dbid
        self.outer = outer
        EntitiesDispatcher().register_dbid(self, entity_dbid)
        self.db = Globals.this_service.db
        self.failed = False
        self.properties_locks = dict()
        await super().__ainit__()

    async def on_entity_created(self):
        pass

    @classmethod
    def pg_null(cls, value):
        if isinstance(value, int):
            return value
        return 0

    @property
    def base(self):
        return Globals.this_service

    @classmethod
    def serializable_value(cls, *value):
        return int32(0 if len(value) == 0 else value[0])

    async def __apostinit__(self):
        await self.load_persistents()
        await super().__apostinit__()
        # await self.begin_play()

    def __isvalid__(self):
        return super().__isvalid__() and not self.failed

    async def load_persistents(self):
        if not is_valid(self.db):
            self.failed = True
            return

        class_name = self.__class__.__name__
        serialized_data = await self.db.GetEntityData(self.dbid, class_name)
        srp = BinarySerialization(serialized_data).proxy()
        for prop_name, prop_info in self.properties.items():
            if Persistent in prop_info.specifiers:
                if not issubclass(prop_info.prop_type, BaseEntity):
                    prop_value = srp >> bytes
                    if "FDateTime" in prop_info.prop_type.__name__:
                        print(",,,")
                    deserialized = prop_info.prop_type.deserialize(prop_value)
                    T = prop_info.prop_type
                    value = T.instantiate(deserialized)

                    value.set_db_interface(DatabaseVariableProxy(self.db, self.dbid, class_name, prop_name, prop_info))

                    value.initialize_property(self, prop_name)
                    self.properties_locks[prop_name] = asyncio.Lock()
                else:
                    prop_value = srp >> int32
                    value = EntitiesDispatcher().get_by_dbid(prop_value)
                    if value is None:
                        is_new_entity = False
                        if prop_value == 0:
                            prop_value = await self.db.CreateDefaultEntity(prop_info.prop_type.__name__)
                            is_new_entity = True


                        value = await prop_info.prop_type(prop_value, outer=self)
                        value.initialize_property(self, prop_name)
                        value.set_db_interface(DatabaseVariableProxy(self.db, self.dbid, class_name, prop_name, prop_info))

                        if is_new_entity:
                            await value.on_entity_created()

                        if is_new_entity:
                            await value.async_save()

                # ERROR_MSG("Lolz %s %s" % (prop_name, value))
                # if issubclass(prop_info.prop_type, BaseEntity):
                #     if value
                self.set_property_value(prop_name, value)

    def save_all(self):
        for v in self.properties_values.values():
            v.save()

    async def async_save_all(self):
        for v in self.properties_values.values():
            await v.async_save()


    async def make_defaults(self):
        vars = dict()
        defaults = dict()
        properties = self.get_properties(Transactional)
        for prop_name, prop_info in properties.items():
            if not issubclass(prop_info.prop_type, Entity):
                var = getattr(self, prop_name)
                vars[prop_name] = var
                defaults[prop_name] = prop_info.default

        async with Transaction(*list(vars.values()), name=f"making defaults for {self}"):
            for prop_name in vars.keys():
                setattr(self, prop_name, defaults[prop_name])


        await self.on_defaults()

    async def on_defaults(self):
        pass


class UE4Entity(Entity, TypeBase):
    context_name = "ue4"