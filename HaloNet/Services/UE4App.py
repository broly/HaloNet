import HaloNet

from Core.Framework import *


# @runnable
from Core.Services.UE4AppBase import UE4AppBase
from Core.Type import TArray, TMailbox
from Types import *


class UE4App(UE4AppBase):
    is_client_side = True


    @rmi(Exposed)
    def RunConsoleCommand(self, command: FString):
        """
        Запустить консольную команду
        @param command: строка-команда
        """

    @rmi(Exposed)
    async def ResetDedicatedServer(self):
        """
        Сбросить dedicated server
        """

    @rmi(Exposed)
    def JoinSession(self, ip: FString, port: int32):
        """
        Вход в сессию с IP, port и character_id
        @param ip: айпи
        @param port: порт
        """

    @rmi(Exposed)
    async def GetDedicatedServerInfo(self) -> FDedicatedServerInfo:
        """
        Запрос о информации Dedicated server'а
        @return: информация
        """

    @rmi(Exposed)
    async def RegisterPlayerForMatch(self, username: FString, access_token: FString, equipped_items: TArray[FSlotItemPair]):
        """
        Регистрация игрока для матча на Dedicated Server
        @param character_id: ид персонажа
        @param access_token: токен
        """

    @rmi(Exposed)
    def UnregisterPlayer(self, access_token: FString):
        """
        
        @param access_token: 
        @return: 
        """

    @rmi(Exposed)
    def MatchStart(self, match_id: int32):
        """
        Старт матча
        @return: 
        """

    @rmi(Exposed)
    def OnMatchDone(self): ...


    @rmi(Exposed)
    def TextInform(self, text: FText):
        pass

    @rmi(Exposed)
    async def SetupGame(self, max_players: int32):
        """
        Установка параметров игрового режима для DedicatedServer

        @param max_players: максимальное количество игроков
        """

    @rmi(Exposed)
    async def PrepareMatch(self): ...

    @rmi(Exposed)
    def DropClient(self): ...




# print(UE4App.rmi_methods)
#
# from collections import namedtuple
#
# MyStruct = namedtuple('MyStruct', ['someName', 'anotherName'])
# aStruct = MyStruct('aValue', 'anotherValue')
#
# print(aStruct.someName)