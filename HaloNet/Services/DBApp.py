import HaloNet
from Core.Services.DatabaseService import DatabaseService
from Core.Framework import *
from Core.Type import FDateTime
from Types import FOnlineStatisticEntry, EGameType, FStatisticsRecord


@runnable
class DBApp(DatabaseService):

    async def start(self):
        await super().start()
        # INFO_MSG("DBApp started %s" % self.service)


    @rmi(Exposed)
    async def Handshake(self, s: FString, mbox: TMailbox("base", "BaseApp")):
        INFO_MSG("Handshaked", mbox)


    @rmi()
    async def DumpOnline(self, service_name: FString, timestamp: FDateTime, online: int32, ingame: int32):
        await self.driver.exec_raw(""" INSERT INTO ccu (app_name, dump_time, online_count, in_game_count) 
                                       VALUES ('{0}', '{1}', {2}, {3});
                                   """.format(service_name, timestamp, online, ingame,))

    @rmi()
    async def LoadOnline(self) -> TArray[FOnlineStatisticEntry]:
        out_result = TArray[FOnlineStatisticEntry]()
        result = await self.driver.exec_raw(""" SELECT * FROM ccu; """)
        for r in result:
            app_name, dump_time, online_count, in_game_count = (r[i] for i in range(4))
            out_result.append(FOnlineStatisticEntry(
                AppName=app_name,
                Date=dump_time,
                OnlineCount=online_count,
                InGameCount=in_game_count,
            ))

        return out_result


    @rmi()
    async def MakeStatisticsRecordScores(self, user_id: int32, username: FString, game_mode: EGameType, score: int32):
        # todo assert not True  # we must use user_id instead username!

        await self.driver.exec_raw(""" INSERT INTO statistics (user_id, username, score, game_mode) 
                                       VALUES ({0}, '{1}', {2}, {3})
                                       ON CONFLICT (username, game_mode) DO 
                                       UPDATE SET score = {2}; """.format(user_id, username, score, int(game_mode)))

    @rmi()
    async def GetTop100(self, game_type: EGameType) -> TArray[FStatisticsRecord]:
        records = await self.driver.exec_raw(""" SELECT username, score FROM statistics 
                                                 WHERE game_mode = {0} 
                                                 ORDER BY score DESC
                                                 LIMIT 100; """.format(int(game_type)))
        result = TArray[FStatisticsRecord]()
        for record in records:
            result.append({'Username': record[0], 'Score': record[1]})
        return result
