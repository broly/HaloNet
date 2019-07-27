import asyncio
import datetime
from copy import copy

from Core import INFO_MSG, ERROR_MSG, Mailbox
from Core.Replication import Replication, Sync
from Core import WARN_MSG
from Core.Declarators.rmi import rmi
from Core.Declarators.Specs import Exposed, Persistent, BlueprintCallable, Transactional, Replicated, Exec, Latent, \
    PartialRep_EXPERIMENTAL, DeferredReturn
from Core.BaseEntity import BaseEntity
from Core.LocalDatatypes import FString
from Core.Service import WakeupError
from Core.Transaction import Transaction, ensure_locked
from Core.Type import TArray, TSet, FDateTime
from Core.Utils import deprecated
from Redmine import generate_bugreport
from Types import *
from Storages import *
import time


class Session(BaseEntity):
    is_exposed = True
    is_exec_capable = True

    # properties
    # just current username
    Username:               FString                         [Replicated]
    # Предметы игрока
    Items:                  TMap[int32, FItemInstance]      [Replicated, Persistent, Transactional, PartialRep_EXPERIMENTAL]
    # Порядок предметов: Инстанс-ИД: Индекс порядка (iiid: oid)
    ItemsOrder:             TMap[int32, int32]              [Replicated, Persistent, Transactional, PartialRep_EXPERIMENTAL]
    # Глобальный счетчик предметов
    ItemsCounter:           int32                           [Persistent, Transactional]
    # Экипированные предметы
    Equipment:              TMap[EEquipmentSlot, int32]     [Replicated, Persistent, PartialRep_EXPERIMENTAL]

    async def __ainit__(self, dbid, username):
        await super().__ainit__(dbid)
        self.username = self.Username = username
        self.client = None
        self.checker_time = None
        self.access_token = ""
        self.login_date = datetime.datetime.now()
        self.currently_in_game = False
        INFO_MSG("Hi!")

    def set_in_game(self, in_game=True):
        self.currently_in_game = in_game

    def set_user_meta(self, dictionary):
        self.user_meta = dictionary

    def __repr__(self):
        if not self.__isvalid__():
            return super().__repr__()
        return f'<Session "{self.username}":"{self.access_token}">'

    __str__ = __repr__

    def inform(self, info_text):
        self.ue4client.TextInform(info_text)

    def set_access_token(self, new_access_token):
        self.access_token = new_access_token

    @property
    def is_first_session(self):
        return not self.has_any_achievements("SIMPLE_BEGINNER")

    async def begin_play(self):
        await super().begin_play()
        await self.initialize()

    async def on_defaults(self):
        await self.initialize()

    async def initialize(self):
        pass

    def destroy(self):
        self.ue4client.destroy()
        super().destroy()

    def set_mailbox(self, remote_app_mbox: Mailbox):
        self.ue4client = remote_app_mbox
        asyncio.Task(self.subscribe(self.ue4client))

    @rmi(Exposed, access=0)
    async def LeaveGame(self):
        """ Покинуть игру 
            @warning не работает 
        """
        INFO_MSG("Leaved game")

    @rmi(Exec, Latent, Exposed, BlueprintCallable, access=0)
    async def RequestGameSession(self, game_type: EGameType) -> EReqGameResponse:
        """ Запрос игровой сессии 
            @param map_name: имя карты 
            @param char_id: ид персонажа для игры
        """
        return await self.base.request_quick_match(self, game_type)

    def join_session(self, ip, port):
        INFO_MSG("JoinSession call")
        self.ue4client.JoinSession(ip, port)

    @rmi(Exec, Exposed, access=0)
    async def PleaseFlushAll(self):
        await self.make_defaults()

    @rmi(Exec, BlueprintCallable, Exposed, access=0)
    async def ArenaExit(self):
        self.service.arena_exit(self)

    @rmi(Exposed, access=0)
    async def BugReport(self, title: FString, text: FString, image: FBytes) -> Bool:
        return await generate_bugreport(self.username, title, text, image)

    @rmi(Exec, Exposed, BlueprintCallable, access=0)
    def ExitFromCurrentGame(self):
        self.base.match_making.request_player_exit_from_game(self)

    def get_item_type_count(self, item_name):
        count = 0
        for item in self.Items.values():
            if item['Name'] == item_name:
                count += item['Count']
        return count

    def give_item(self, item_instance):
        """ @warning [Использовать в транзакции]
            Дать предмет игроку
        """
        if ensure_locked(self.Items, self.ItemsOrder):
            instance_id = item_instance['InstanceID']
            self.Items[instance_id] = item_instance
            order_values = self.ItemsOrder.values()
            for i in range(1000):
                if i not in order_values:
                    self.ItemsOrder[instance_id] = i
                    break

    def swap_items(self, iiid1, iiid2):
        """ @warning [Использовать в транзакции]
            Поменять местами предметы
        """
        if ensure_locked(self.ItemsOrder):
            self.ItemsOrder[iiid1], self.ItemsOrder[iiid2] = self.ItemsOrder[iiid2], self.ItemsOrder[iiid1]

    def move_item(self, iiid, order_index):
        """ @warning [Использовать в транзакции]
            Переместить предмет с места на место в инвентаре
        """
        if ensure_locked(self.ItemsOrder):
            order_values = self.ItemsOrder.values()
            if order_index in order_values:
                for existed_iiid, existed_order_index in self.ItemsOrder.items():
                    if order_index == existed_order_index:
                        if self.is_item_stackable(iiid) and self.is_item_stackable(existed_iiid):
                            if self.Items[iiid]["Name"] == self.Items[existed_iiid]["Name"]:
                                self.merge_items(iiid, existed_iiid)
                                return
                            else:
                                self.swap_items(iiid, existed_iiid)
                                return
                        else:
                            self.swap_items(iiid, existed_iiid)
                            return
            self.ItemsOrder[iiid] = order_index

    def is_item_stackable(self, iiid):
        item_instance = self.Items[iiid]
        item_info = ItemsCatalog.get_by("Name", item_instance["Name"])
        return item_info["MaxStack"] > 1

    def merge_items(self, source_id, target_id):
        if ensure_locked(self.ItemsOrder, self.Items):
            source_item = self.Items[source_id]
            target_item = self.Items[target_id]

            source_item_info = item_info = ItemsCatalog.get_by("Name", source_item["Name"])
            target_item_info = ItemsCatalog.get_by("Name", target_item["Name"])

            if source_item_info is None or target_item_info is None:
                ERROR_MSG(f"Failed to merge items with Names "
                          f"{source_item['Name']} & { target_item['Name']}. ItemsCatalog corrupted!")
                return

            if source_item_info["Name"] != target_item_info["Name"]:
                ERROR_MSG(
                    f"Failed to merge items with different ID {source_item_info['Name']} & {target_item_info['Name']}")
                return

            if source_item.Count >= item_info["MaxStack"] or target_item.Count >= item_info["MaxStack"]:
                self.swap_items(source_id, target_id)
            else:
                if (source_item.Count + target_item.Count) <= item_info["MaxStack"]:
                    target_item.Count = source_item.Count + target_item.Count
                    self.drop_item(source_id)
                else:
                    loc_count_item = item_info["MaxStack"] - self.Items[target_id].Count
                    if self.Items[source_id].Count >= loc_count_item:
                        with self.Items.edit(source_id):
                            target_item.Count += loc_count_item
                        with self.Items.edit(target_id):
                            source_item.Count -= loc_count_item
                        if source_item.Count == 0:
                            with self.Items.edit(source_id):
                                self.drop_item(source_id)
                    else:
                        with self.Items.edit(target_id):
                            target_item.Count += source_item.Count
                        self.drop_item(source_id)

    def drop_item(self, iiid):
        """ @warning [Использовать в транзакции]
            Убрать предмет из инвентаря
        """
        if ensure_locked(self.Items, self.ItemsOrder):
            del self.Items[iiid]
            del self.ItemsOrder[iiid]

    @rmi(Exposed, BlueprintCallable, access=0)
    async def MoveInventoryItem(self, item_instance_id: int32, new_index: int32):
        async with Transaction(self.Items, self.ItemsOrder):
            self.move_item(item_instance_id, new_index)

    @rmi(Exec, Exposed, BlueprintCallable, access=0)
    async def PleaseGiveItem(self, item_name: FName):
        item = self.make_default_item(item_name, 1)
        async with Transaction(self.Items, self.ItemsCounter, self.ItemsOrder):
            item.InstanceID = self.next_item_instance_id()
            self.give_item(item)

    @rmi(Exec, Exposed, BlueprintCallable, access=0)
    async def EquipItem(self, instance_id: int32):
        item_inst = self.Items.get(instance_id, None)

        if item_inst is None: return \
            WARN_MSG(f"There is no item instance with id={instance_id}")

        item_info = ItemsCatalog.get_by("Name", item_inst['Name'])

        if item_info is None: return \
            WARN_MSG(f"There is no item named {item_inst['Name']}")

        slot_id = item_info['CompatibleSlot']

        with Sync(self.Equipment):
            self.Equipment[slot_id] = instance_id

    def get_equipped_items(self):
        return list(FSlotItemPair(Slot=key, Item=self.Items[value]) for key, value in self.Equipment.items())

    def get_item_by(self, id, from_container=None):
        if from_container is None:
            from_container = self.Items
        if isinstance(from_container, list):
            for item in from_container:
                if item["InstanceID"] == id:
                    return item
        elif isinstance(from_container, dict):
            return from_container.get(id, None)

    def make_default_item(self, item_name, count=1):
        return FItemInstance(Name=item_name,
                             Count=count,
                             InstanceID=0)

    def next_item_instance_id(self):
        if ensure_locked(self.ItemsCounter):
            self.ItemsCounter += 1
            return self.ItemsCounter

    @rmi(Exposed, BlueprintCallable, Latent, access=0)
    async def GetTop100Players(self, game_type: EGameType) -> TArray[FStatisticsRecord]:
        return await self.base.db.GetTop100(game_type)