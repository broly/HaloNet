from Core import INFO_MSG
from MatchMaking.Match import Match
from Types import EGameType, EReqGameResponse

SURVIVAL_TIMEOUT = 30.
SURVIVAL_MIN_PLAYERS = 2

class SurvivalMatch(Match):

    game_type = EGameType.Survival

    async def __ainit__(self, match_making, id=0, ip="0.0.0.0", port=0, dedicated_server=None,
                        players=None, map_name=None, started=False, max_players=0, teams_assigned=False):
        await super().__ainit__(match_making, id, ip, port, dedicated_server, players, map_name, started, max_players, teams_assigned)

        self.timeout_timer = None

    def handle_start(self):
        self.close_game()

    async def enqueue_player(self, session):
        result = await super().enqueue_player(session)

        if result != EReqGameResponse.Denied and not self.timeout_timer and len(self.players) >= SURVIVAL_MIN_PLAYERS:
            INFO_MSG("Timeout started")
            if not self.fulfilled and not self.performing and not self.started:
                self.timeout_timer = self.call_later(self.perform, SURVIVAL_TIMEOUT)

        return result

    async def perform(self):
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None
        return await super().perform()

    def rollback(self):
        self.timeout_timer = self.call_later(self.perform, SURVIVAL_TIMEOUT)