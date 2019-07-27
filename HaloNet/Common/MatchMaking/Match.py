import asyncio
import random
from typing import Dict

from Core import INFO_MSG, WARN_MSG, ERROR_MSG
from Core.Declarators.metainfo import metainfo
from Core.Entity import Entity
from Core.Globals import Globals
from Core.LocalDatatypes import FName, int32
from Core.Service import WakeupError
from Core.Type import TMap, TArray, DisplayThis
from Core.Utils import get_uclass_true_path
from MatchMaking.GameBase import GameBase, GamePlayerInfo
from Storages import Maps
from Types import EMatchState, FMapInfo, EGameType, FMatchInfo

if False:
    from UE4App import UE4App


class MatchMakingError(Exception):
    pass


class Match(Entity, GameBase):
    """

    Матч. Хранит состояние и управляет соответствующими ему серверами

    """
    ip: DisplayThis
    port: DisplayThis
    dedicated_server: DisplayThis
    map_name: DisplayThis
    state: DisplayThis

    game_type = EGameType.Simple

    async def __ainit__(self, match_making, id=0, ip="0.0.0.0", port=0, dedicated_server=None,
                        players=None, map_name=None, started=False, max_players=0, teams_assigned=False):
        await GameBase.__ainit__(self, match_making, id, max_players, started=started, players=players, teams_assigned=teams_assigned)
        await Entity.__ainit__(self)

        self.ip = ip        # ip dedicated server'а
        self.port = port    # порт вступления в dedicated server
        self.dedicated_server: 'UE4App' = dedicated_server  # мейлбокс dedicated server'а
        self.map_name = map_name        # имя выбранной карты
        self.state = EMatchState.Idle   # состояние матча
        self.on_game_done = None
        self.empty_match_timer_handle = None
        INFO_MSG(f"Created and prepared new match {self}")

    def __repr__(self):
        return f"<Match id={self.id}, state={self.state}; {self.ip}:{self.port} ({'STARTED' if self.dedicated_server else 'INITIALIZING'} and {'FULFILLED' if self.fulfilled else 'INVITES FOR PLAYERS'})>"

    @classmethod
    async def create_prepared(cls, match_making, game_type, extra=None):
        """
        Создаёт новый инстанс матча
        @param match_making:
        @param game_type:
        @return:
        """
        maps_by_type = Maps.get_all_by("Type", game_type)
        INFO_MSG("Maps: %s" % maps_by_type)

        if not maps_by_type:
            raise RuntimeError("Gameplay maps list is empty")

        selected_map: FMapInfo = random.choice(maps_by_type)

        if isinstance(extra, dict):
            if extra.get('force_use_map', None):
                selected_map = Maps.get_by("Name", extra['force_use_map'])

        return await cls(match_making,
                         id=match_making.new_id(),
                         map_name=selected_map.Name,
                         max_players=selected_map.PlayersMax)

    def return_back_player(self, session):
        return True

    def cmd(self, cmd):
        if self.dedicated_server:
            self.dedicated_server.RunConsoleCommand(cmd)
        else:
            WARN_MSG("Can't execute command while server loading")

    def dequeue_player(self, session):
        """
        Убрать игрока
        @param session: сессия игрока
        @return:
        """
        # session.ue4client.RunConsoleCommand("disconnect")
        if self.dedicated_server:
            self.dedicated_server.UnregisterPlayer(session.access_token)
        super().dequeue_player(session)

        if not len(self.players):
            if self.empty_match_timer_handle:
                self.empty_match_timer_handle.cancel()
            INFO_MSG(f"Preparing to close and exit game {self}")
            self.empty_match_timer_handle = self.call_later(self.handle_empty_match, 120.0)

    def handle_empty_match(self):
        INFO_MSG(f"Closing and exiting game  {self} [second chance (todo)]")  # todo
        self.empty_match_timer_handle = None
        if not len(self.players):
            self.close_game()
            if self.dedicated_server.dedicated_server:
                asyncio.Task(self.dedicated_server.ExecuteCode("quit"))
            self.match_making.destroy_game(self)

    def get_info(self):
        pass

    async def register_player_info(self, match_player_info):
        equipped_items = match_player_info.session.get_equipped_items()
        await self.dedicated_server.RegisterPlayerForMatch(match_player_info.session.username,
                                                           match_player_info.session.access_token,
                                                           equipped_items)

    async def accept_player_to_started_game(self, session, match_player_info, force_use_team_id=None, player_returned=False):

        await self.register_player_info(match_player_info)

        match_player_info.join(self.ip, self.port)

    def rollback(self):
        self.performing = False
        self.dedicated_server = None

    async def perform(self):
        """ Запуск текущего матча """
        INFO_MSG(f"Performing match {self}")
        if self.dedicated_server: return \
            ERROR_MSG(f"The match {self} already performing")
        self.performing = True

        self.update_state(EMatchState.Preparing)

        try:
            await self.wake_up_dedicated_server_for_match()
        except WakeupError:
            self.rollback()
            raise MatchMakingError("Unable to wakeup dedicated server for match")

        await self.dedicated_server.SetupGame(self.max_players)

        self.assign_teams()
        self.started = True

        for player_info in self.players.values():
            await self.register_player_info(player_info)


        self.update_state(EMatchState.InGame)
        self.dedicated_server.MatchStart(self.id)

        self.handle_start()

        for session, player_info in self.players.items():
            player_info.join(self.ip, self.port)

    async def done(self, winners, winner_team_id):
        INFO_MSG(f"Done match {self}")
        await asyncio.sleep(3.)
        if self.dedicated_server:
            self.dedicated_server.OnMatchDone()
        # if self.on_game_done:
        #     self.on_game_done(winner_team_id)
        # for winner in winners:
        #     for player_session, player_info in self.players.items():
        #         if player_session.access_token == winner['AccessToken']:
        #             character_id = player_info.character_id
        #             await player_session.give_character_experience(character_id, winner['CharacterExperience'])
        #             arch = player_session.get_archetype(character_id)
        #             await player_session.give_archetype_experience(arch['ArchetypeName'], winner['ArchetypeExperience'])

                    # # <RANDOM 10 ITEMS>
                    # ITEMS_COUNT = 10
                    # items_to_give = TMap[FName, int32]()
                    # for i in range(ITEMS_COUNT):
                    #     if random.randrange(0, 2):
                    #         all_items = ItemsCatalog.get()
                    #         random_item_info: FItemTypeInfo = all_items[random.randrange(0, len(all_items))]
                    #         item_name = random_item_info.InternalName
                    #         if item_name not in items_to_give:
                    #             items_to_give[item_name] = 1
                    #         else:
                    #             items_to_give[item_name] += 1
                    # items_to_give_info = TArray[FCityResource]()
                    # for item_name, item_count in items_to_give.items():
                    #     items_to_give_info.append(FCityResource(Name=item_name,
                    #                                             Value=item_count))
                    # # </RANDOM 10 ITEMS>
                    #
                    # await player_session.CityInstance.give_items(items_to_give)
                    #
                    # player_session.client.InformPresent(arch['ArchetypeName'],
                    #                                     character_id,
                    #                                     winner['ArchetypeExperience'],
                    #                                     winner['CharacterExperience'],
                    #                                     items_to_give_info)

    async def wake_up_dedicated_server_for_match(self):
        """ Поднять сервер для этого матча """
        INFO_MSG(f"Waking up dedicated server for match {self}")
        map_info: FMapInfo = Maps.get_by("Name", self.map_name)

        if not map_info:
            return ERROR_MSG(f"Missing map {self.map_name}")

        port = self.match_making.new_dedicated_server_port()
        map_parameters = f"{ map_info.Asset }?listen&port={ port }&game={ get_uclass_true_path(map_info.GameMode) }"
        kw_params = dict(port=str(port), dedic_id=self.id, MaxPlayers=map_info.PlayersMax, BotsCount=map_info.PlayersMax)
        # MaxPlayers is BotsCount
        base_ip, base_port = self.service.endpoint


        self.dedicated_server = await self.base.supervisor.RequestDedicatedServer(map_parameters, self.service.exposed_ip, base_port, {}, kw_params)

        await self.dedicated_server.PrepareMatch()
        INFO_MSG(f"Dedicated server waked up for match {self}")
        self.dedicated_server.add_lost_callback(lambda: self.on_dedicated_server_dropped(self.dedicated_server))
        self.port = port
        self.ip = Globals.this_service.exposed_ip

        return self.dedicated_server

    def on_dedicated_server_dropped(self, dedicated_server):
        INFO_MSG("Dedicated server dropped")
        if self.dedicated_server == dedicated_server:
            self.match_making.destroy_game(self)

    def update_state(self, state: EMatchState):
        """ Обновление стейта текущего матча """
        self.state = state

        for session in self.players:
            session.client.UpdateMatchState(state)

    def get_match_info(self) -> FMatchInfo:
        return FMatchInfo(
            MatchState=self.state,
            MatchMax=self.max_players,
            MatchUsers=[session.username for session in self.players],
            MapName=self.map_name,
            GameType=self.game_type,
            Additional="",
            ID=self.id
        )
