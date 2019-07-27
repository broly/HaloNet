import asyncio

import HaloNet
from Config import DBAppConfig

from Core.CodeGen import CodeGen
from Core.CommandLine import CommandLine
from Types import *
from Storages import *
from Execptions import *

from Core.Globals import Globals

Globals.IsInGenerator = True

code_gen = CodeGen()

Globals.IsInGenerator = False


Globals.HaloNet_imported = True

from DBApp import DBApp
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator

ConfigurationGenerator().load_generated_info()

from Core.LocalDatatypes import *
from Core.Logging import INFO_MSG, ERROR_MSG
from Core.Service import Service
from Core.Utils import runnable, is_valid


@runnable
class Gen(Service):
    async def start(self):
        self.db, _ = await self.async_wakeup_service_locally_by_name("DBApp")
        if is_valid(self.db):
            if CommandLine.get_arguments().clearall:
                await self.db.ClearDatabase()
                return

            for cls_name, cls_info_by_context in code_gen.classes_info.items():
                if 'base' in cls_info_by_context:
                    cls_info = cls_info_by_context['base']
                    await self.update_class_properties(cls_name, cls_info['Properties'])

            for storage_name, storage_info in code_gen.storage_info.items():
                await self.update_storage(storage_name, storage_info['Type'])

            await self.db.Synchronize()

            enums = dict()
            for name, info in code_gen.types_info.items():
                if info['Kind'] == "Enum":
                    enums[name] = info['Members'].keys()
            # if enums:
            #     await self.update_enums(enums)
            self.db.Terminate()
        else:
            ERROR_MSG("Failed to connect to DB")

    async def update_storage(self, name, typename):
        await self.db.CreateStorage(name, typename)

    async def update_class_properties(self, class_name, properties_info):
        new_properties = dict()
        for prop in properties_info:
            if prop['Persistent']:
                new_properties[prop['Name']] = prop['Type']
        INFO_MSG("Updating properties for class %s" % class_name)
        await self.db.CreateClassTable(class_name, new_properties)


    async def done(self):
        await self.stop()