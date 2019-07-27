import asyncio
from functools import partial
from typing import Dict

from Core import WARN_MSG, INFO_MSG, ERROR_MSG
from Core.AsyncObj import AsyncObj
from Core.Declarators.Specs import DisplayThis
from Types import FMatchInfo, EReqGameResponse


class GameBase(AsyncObj):
    id: DisplayThis
    players: DisplayThis
    max_players: DisplayThis
    performing: DisplayThis
    started: DisplayThis
    teams_assigned: DisplayThis

    game_type = None


    async def __ainit__(self, match_making, id, players_max, started=False, players=None, teams_assigned=False):
        from MatchMaking.Component import MatchMaking
        from BaseApp import BaseApp
        from Session import Session
        from UE4App import UE4App
        # self.base: BaseApp = base
        self.players: Dict[Session, GamePlayerInfo] = players if players else dict()
        self.match_making: MatchMaking = match_making
        self.id = id
        self.max_players = players_max
        self.performing = False
        self.started = started
        self.teams_assigned = teams_assigned
        self.closed_game = False

    def cmd(self, cmd):
        pass

    @classmethod
    async def create_prepared(cls, match_making, game_type, extra=None):
        raise NotImplementedError()

    def conditional_dequeue_player(self, session):
        self.dequeue_player(session)
        return True

    def close_game(self):
        INFO_MSG(f"Game {self} closed")
        self.closed_game = True

    def kick_player(self, session):
        self.dequeue_player(session)
        self.match_making.free_player(session)

    def on_client_dropped(self, session):
        if self.conditional_dequeue_player(session):
            self.match_making.free_player(session)


    async def enqueue_player(self, session):
        """ Добавить в очередь игрока
            Запускает матч, если список игроков заполнен
            @param session: сессия игрока
            @param character_id: ИД персонажа
        """
        INFO_MSG(f"Enqueueing player {session}")
        request_result = EReqGameResponse.Wait
        if self.fulfilled:
            WARN_MSG(f"Can't enqueue {session}. Game is fulfilled")
            return EReqGameResponse.Denied
        self.players[session] = GamePlayerInfo(session=session)
        session.ue4client.add_lost_callback(partial(self.on_client_dropped, session))
        # Начать выполнение матча. Можно только если команда заполнена и матч на данный момент не выполняется
        if self.fulfilled and not self.performing:
            asyncio.Task(self.perform())

        # Допустить игрока (дополнительного игрока, для восполнения) в матч (можно только если уже начат)
        if self.started:
            await self.accept_player_to_started_game(session, self.players[session])
            request_result = EReqGameResponse.Success

        return request_result

    def return_back_player(self, session):
        asyncio.Task(self.accept_player_to_started_game(session, self.players[session], player_returned=True))

    def dequeue_player(self, session):
        INFO_MSG(f"Dequeueing player {session}")
        if session in self.players:
            del self.players[session]

    def is_subgame(self, game):
        return False

    def reset(self):
        pass

    def is_subgame_id(self, id):
        return False

    async def done_subgame(self, winners, winner_team_id):
        pass

    async def perform(self):
        raise NotImplementedError()

    async def accept_player_to_started_game(self, session, game_player_info, force_use_team_id=None, player_returned=False):
        raise NotImplementedError()

    async def done(self, winners, winner_team_id):
        raise NotImplementedError()

    def handle_start(self):
        pass

    @property
    def fulfilled(self) -> bool:
        return len(self.players) >= self.max_players

    @property
    def joinable(self) -> bool:
        return not (self.fulfilled or self.closed_game)

    @property
    def base(self):
        return self.match_making.base if self.match_making else None

    def assign_teams(self):
        if not self.teams_assigned:
            for index, (session, player_info) in enumerate(self.players.items()):
                player_info.team_id = 1 if index % 2 else 2
            self.teams_assigned = True

    def get_match_info(self) -> FMatchInfo:
        raise NotImplementedError()

class GamePlayerInfo:
    """ Информация о игроке, участвующего в матче """
    def __init__(self, session=None, joined_game=False, team_id=0):
        from Session import Session
        self.session: Session = session
        self.joined_game = joined_game

    def join(self, ip, port):
        if not self.session:
            ERROR_MSG("Session is invalid")
        self.session.join_session(ip, port)