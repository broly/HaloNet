from Core.Declarators.Specs import *
from Core.Declarators.rmi import rmi
from Core.LocalDatatypes import *
from Core.Service import Service


class UE4AppBase(Service):

    @rmi(Exposed, SystemInternal, DeferredReturn)
    async def CreateClientEntity(self, entity_class_name: FString, entity_id: int32):
        """
        Создать клиентскую сущность на UE4App
        @param entity_class_name: имя класса сущности
        @param entity_id: идентификатор
        """

    @rmi(Exposed, SystemInternal)
    def DestroyClientEntity(self, entity_id: int32):
        """
        Уничтожить клиентскую сущность
        @param entity_id: ИД сущности
        """

    @rmi(Exposed, SystemInternal)
    def UpdateClientEntityVariable(self, entity_id: int32, property_name: FString, data: FBytes):
        """
        Обновление переменной клиентской сущности
        @param entity_id: ид сущности
        @param property_name: название переменной (свойства)
        @param data: данные
        @return: 
        """

    @rmi(Exposed, SystemInternal)
    def UpdateClientEntityVariableSlice(self, entity_id: int32, property_name: FString, data: FBytes):
        """
        Обновление части переменной клиентской сущности
        @param entity_id: ид сущности
        @param property_name: название переменной (свойства)
        @param data: данные
        @return:
        """

