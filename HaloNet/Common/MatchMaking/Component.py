from Core import INFO_MSG, WARN_MSG
from Core.Declarators.Specs import DisplayThis
from Core.Declarators.metainfo import metainfo
from Core.Entity import Entity
from Core.Service import WakeupError
from MatchMaking.GameBase import GameBase
import asyncio
from typing import Dict, List, Type

import typing

from MatchMaking.SimpleMatch import SimpleMatch
from MatchMaking.SurvivalMatch import SurvivalMatch

if typing.TYPE_CHECKING:
    from BaseApp import BaseApp

from Core import INFO_MSG
from MatchMaking.Match import Match, MatchMakingError
from Types import *


class MatchMaking(Entity):
    """ Класс-компонент для организации матч-мейкинга """

    base: DisplayThis
    games: DisplayThis
    ports_counter: DisplayThis
    players_games_mapping: DisplayThis

    counter = 0

    @classmethod
    def new_id(cls):
        cls.counter += 1
        return cls.counter

    async def __ainit__(self, base):
        await super().__ainit__(self)
        self.base: 'BaseApp' = base

        self.games: Dict[EGameType, List[GameBase]] = dict()
        for game_type in EGameType.__members__:
            self.games[game_type] = list()

        self.ports_counter = 7500
        self.players_games_mapping = dict()

    def get_all_games(self) -> List[GameBase]:
        result = list()
        for game_type, games in self.games.items():
            for game in games:
                result.append(game)
        return result

    def get_games_info(self):
        return [game.get_match_info() for game in self.get_all_games()]

    @staticmethod
    def get_game_class(game_type) -> Type[GameBase]:
        return {
            EGameType.Simple: SimpleMatch,
            EGameType.Survival: SurvivalMatch,
        }.get(game_type, None)

    def get_games(self, game_type) -> List[GameBase]:
        return self.games[game_type]

    def new_dedicated_server_port(self):
        """
        Инкремент порта
        @return: порт
        """
        self.ports_counter += 1
        return self.ports_counter

    def is_session_already_requested(self, player_session):
        return player_session in self.players_games_mapping.keys()

    def get_preparing_game_info(self, game_type):
        """
        Получить подготавливаемые быстрые матчи (по вместимости игроков)
        @return: существующий матч
        """
        games = self.get_games(game_type)
        if games:
            for game_info in games:
                if game_info.joinable:
                    return game_info
        return None

    async def request_game_info(self, game_type, extra=None) -> GameBase:
        """
        Запросить матч по вместимости
        @return: новый или существуюищй матч
        """
        game = self.get_preparing_game_info(game_type)
        if game is None:
            game_class = self.get_game_class(game_type)

            game = await game_class.create_prepared(self, game_type, extra)

            games = self.get_games(game_type)

            games.append(game)

        return game

    async def request_game_for_player(self, game_type, player_session, extra=None):
        """
        Запрос быстрого матча для игрока
        @param player_session: сессия игрока
        @param extra: дополнительные опции
        @return:
        """
        INFO_MSG(f"Requesting game with session {player_session}")
        if player_session in self.players_games_mapping:
            if self.players_games_mapping[player_session].return_back_player(player_session):
                return EReqGameResponse.Success

        try:
            game = await self.request_game_info(game_type, extra)
        except MatchMakingError:
            return EReqGameResponse.Denied

        if game and not self.is_session_already_requested(player_session):
            result = await game.enqueue_player(player_session)
            self.lock_player_for_game(player_session, game)
            return result
        else:
            INFO_MSG(f"Cannot request new game: game={game}, "
                     f"already requested? {self.is_session_already_requested(player_session)}")
            return EReqGameResponse.Denied

    def destroy_game(self, game_to_destroy):
        INFO_MSG(f"{game_to_destroy}")
        for games in self.games.values():
            for game in games:
                if game.is_subgame(game_to_destroy):
                    game.reset()
                    for player_session in game_to_destroy.players:
                        self.free_player(player_session)
                    return

            if game_to_destroy in games:
                games.remove(game_to_destroy)
                for player_session in game_to_destroy.players:
                    self.free_player(player_session)
                return
        WARN_MSG(f"Cannot destroy game {game_to_destroy}, not found")

    def request_player_exit_from_game(self, session):
        """ Запрос выхода игрока из матча
            @param session: сессия игрока
        """
        INFO_MSG(f"{session}")
        for games in self.games.values():
            for game in games:
                if game.conditional_dequeue_player(session):
                    self.free_player(session)


    def lock_player_for_game(self, player_session, game):
        INFO_MSG(f"Player {player_session} locked for game {game}")
        self.players_games_mapping[player_session] = game
        player_session.set_in_game(True)

    def free_player(self, player_session):
        if player_session in self.players_games_mapping:
            del self.players_games_mapping[player_session]
        INFO_MSG(f"{player_session} is free")
        player_session.set_in_game(False)

    def done_game(self, game_id, winners, winner_team_id):
        """ Конец матча
            @param game_id: идентификатор игры
            @param winners: победители
        """
        INFO_MSG(f"Done game id={game_id}, winners={winners}, winner_team_id={winner_team_id}")
        for games in self.games.values():
            for game in games:
                INFO_MSG(f"game: {game}")
                if game.id == game_id:
                    asyncio.Task(game.done(winners, winner_team_id))
                    games.remove(game)
                    for player_session in game.players:
                        self.free_player(player_session)
                    break
                if game.is_subgame_id(game_id):
                    asyncio.Task(game.done_subgame(winners, winner_team_id))
                    break

    def get_game(self, game_id) -> 'GameBase':
        for games in self.games.values():
            for game in games:
                if game.id == game_id:
                    return game
        return None

    def make_record(self): pass

    def start_default_game(self):
        game_type = EGameType.Simple
        extra = {}
        asyncio.Task(self.request_game_info(game_type, extra))

    def exec_cmd(self, id, cmd):
        for games in self.games.values():
            for game in games:
                if game.id == id:
                    game.cmd(cmd)
                    return