import asyncio

from Core import WARN_MSG
from MatchMaking.Match import Match

class SimpleMatch(Match):


    async def __ainit__(self, match_making, id=0, ip="0.0.0.0", port=0, dedicated_server=None,
                        players=None, map_name=None, started=False, max_players=0, teams_assigned=False):
        await super().__ainit__(match_making, id, ip, port, dedicated_server, players, map_name, started, max_players, teams_assigned)

        await self.perform()

    def return_back_player(self, session):
        if session in self.players:
            asyncio.Task(self.accept_player_to_started_game(session, self.players[session], player_returned=True))
            return True
        WARN_MSG("Failed to return back player")
        return False
