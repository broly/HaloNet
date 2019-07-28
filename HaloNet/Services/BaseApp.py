import hashlib
import random
from datetime import datetime
from functools import partial
from typing import Dict, List

from typing import TYPE_CHECKING

import zlib
import HaloNet
from Config import UE4AppConfig, GameConfig

from Core.Declarators.metainfo import metainfo
from Core.LocalDatatypes import ELoginResult

if TYPE_CHECKING:
    from DBApp import DBApp
    from LoginApp import LoginApp


from BaseAppUtils import get_maps_shortcuts
from Core.ClientConnectionHandler import RemoteServerException
from Core.Framework import *
from Core.GlobalManagers import EntitiesDispatcher
from Core.Type import FTimespan, FDateTime
from Core.Utils import to_json, get_uclass_name, get_uclass_true_path, call_later
from MatchMaking.Component import MatchMaking
from Types import *
from Storages import *
import asyncio
from UE4App import UE4App
from Session import Session

GAMEPLAY_PORTS_BEGIN_RANGE = 7000

# время записи онлайна в базу данных
TIME_TO_DUMP_ONLINE = GameConfig.time_to_dump_online
# время старта записи онлайна в базу данных
TIME_TO_START_DUMPING_ONLINE = GameConfig.time_to_start_dump_online


class JoinedPlayerInfo:
    def __init__(self, username, access_token, id, dbid, loginapp):
        self.username = username
        self.access_token = access_token
        self.joined = False
        self.session = None
        self.id = id
        self.dbid = dbid
        self.loginapp = loginapp


@runnable
class BaseApp(Service):

    is_exposed = True
    context_name = "base"
    endpoint = "0.0.0.0", 9002

    supervisor: DisplayThis
    db: DisplayThis
    storages_hash: DisplayThis
    match_making: DisplayThis
    sessions: DisplayThis

    async def start(self):
        from Supervisor import Supervisor
        # self.db: DBApp = await DBApp.make_mailbox("db", "DBApp", ("127.0.0.1", 9002))
        # self.make_mailbox('sv', "Supervisor", )
        self.supervisor: Supervisor = await make_default_service_mailbox("Supervisor")
        self.db: 'DBApp' = await self.supervisor.RequestService("DBApp")
        self.db.add_lost_callback(lambda: WARN_MSG("BaseApp lost connection to DBApp"))
        if not self.db:
            WARN_MSG("This BaseApp has no connection to DBApp")
        # self.ports_counter = GAMEPLAY_PORTS_BEGIN_RANGE
        self.dedicated_servers_counter = 0
        self.storages_hash = ""

        self.matches = dict()
        self.match_making = await MatchMaking(self)

        self.players: Dict[str, JoinedPlayerInfo] = dict()

        total_hash = str()
        for storage in storage_list:
            try:
                await storage  # async init storage
                if storage.md5hash:
                    total_hash += storage.md5hash
            except RemoteServerException:
                WARN_MSG("Unable to load storage %s due to loading errors. Please upload storages again with correct data" % storage.name)
            # print(storage.name, to_json(storage.get()))
        self.storages_hash = hashlib.md5(total_hash.encode()).hexdigest()
        INFO_MSG("Storages hash %s" % self.storages_hash)


        # await self.db.Handshake("hi, i'm baseapp", self)
        self.sessions = dict()
        self.sessions_to_destroy: Dict[Session, asyncio.TimerHandle] = dict()

        # self.call_later(self.online_parser, TIME_TO_START_DUMPING_ONLINE)

        # self.match_making.start_default_game()

    async def online_parser(self):
        online, ingame = self.get_online_players_count()
        if self.db:
            await self.db.DumpOnline(Globals.service_name, datetime.now(), online, ingame)
        else:
            WARN_MSG("Can't dump online due to DBApp is disconnected")
        self.call_later(self.online_parser, TIME_TO_DUMP_ONLINE)

    @rmi()
    async def RequestOnline(self) -> TArray[FOnlineStatisticEntry]:
        result = await self.db.LoadOnline()
        return result

    @rmi()
    async def ReloadStorages(self):
        """ Перезагрузка хранилищ """
        for storage in storage_list:
            await storage.load_table()  # async init storage

    @rmi()
    async def UploadStoragesFromConfigs(self):
        """ Загрузка хранилищ из конфигов """
        INFO_MSG("Test")
        await self.db.UploadStorages()

    @rmi()
    async def GetStorageNames(self) -> TArray[FString]:
        return [s.name for s in storage_list]

    @rmi()
    async def GetStorageData(self, storage_name: FString) -> (FString, FBytes):
        for st in storage_list:
            if st.name == storage_name:
                type_name = st.type.__name__
                storage_data = TArray[st.type](st.data_as_list).serialize()
                return type_name, storage_data
        return "", b''

    @rmi()
    async def PrepareForJoin(self, username: FString, access_token: FString, id: int32, dbid: int32, loginapp: TMailbox('LoginApp', 'LoginApp')) -> Bool:
        if access_token not in self.players:
            self.players[access_token] = JoinedPlayerInfo(username, access_token, id, dbid, loginapp)
        else:
            WARN_MSG(f"Player {username} already preparing or joined")
        return True

    @rmi(CaptureConnection, Latent, Exposed, BlueprintCallable, access=0)
    async def Join(self, connection, access_token: FString) -> (Session, EJoinResult):
        INFO_MSG(f"Join request by access_token: {access_token}")
        if access_token in self.players:
            player_join_info = self.players[access_token]

            session: Session = player_join_info.session

            if session is None:
                INFO_MSG(f"Joining player {player_join_info.username}")
                Access().register_access(access_token, AccessLevel.User)
                session = player_join_info.session = await self.bring_entity(player_join_info.dbid, player_join_info.username)

                session.set_user_meta({
                    'RegisterDate': "unknown"
                })

                self.sessions[player_join_info.id] = session, access_token
                session.set_access_token(access_token)
            else:
                INFO_MSG(f"Rejoining player {player_join_info.username}")
                if session in self.sessions_to_destroy:
                    self.sessions_to_destroy.pop(session).cancel()
                # if session.ue4client:  # todo: check for relogin
                #     session.ue4client.DropClient()
                #     session.ue4client = None 

            remote_app_mbox: UE4App = await UE4App.make_mailbox("ue4", "UE4App", connection, remote_id=0)
            session.set_mailbox(remote_app_mbox)
            remote_app_mbox.add_lost_callback(partial(self.on_session_lost, player_join_info.id, session))

            player_join_info.joined = True

            return session, EJoinResult.Admitted
        else:
            WARN_MSG(f"Join disallowed for token {access_token}")
            return None, EJoinResult.Disallowed


    def on_session_lost(self, user_id, session):
        seconds_to_destroy = GameConfig.player_live_in_offline_timeout
        INFO_MSG(f"User {session} come out, will be dropped after {seconds_to_destroy} seconds")
        self.sessions_to_destroy[session] = self.call_later(partial(self.drop_session, user_id, session), seconds_to_destroy)

    def drop_session(self, user_id, session):
        INFO_MSG(f"Drop user session {session}")
        self.match_making.request_player_exit_from_game(session)
        if user_id in self.sessions:
            del self.sessions[user_id]
        if session.access_token in self.players:
            player_info = self.players.pop(session.access_token)
            player_info.loginapp.InternalLogout(self, user_id)
        session.destroy()

    @rmi(Exposed, access=0)
    async def GetServerTime(self) -> Float:
        """ Возвращает время на сервисе """
        return self.service.time()

    @rmi(Exposed, access=0)
    async def GetServiceTime(self) -> FDateTime:
        from datetime import datetime
        return datetime.now()

    @rmi(access=0)
    async def ConfirmUser(self, confirm_code: FString) -> (Bool, FString):
        return await self.db.ConfirmUser(confirm_code)

    @rmi(Exposed, CaptureConnection, access=0)
    async def OnClientEntityCreated(self, connection, entity_id: int32) -> Bool:
        INFO_MSG("Entity created on client %i" % entity_id)
        return True

    async def bring_entity(self, dbid, *args, **kwargs) -> BaseEntity:
        """ Достать сущность из БД
            @param dbid: идентификатор сущности в БД
            @return: инстанция сущности
        """
        entity_class_name = await self.db.GetEntityClassName(dbid)
        cls = self.find_type(entity_class_name, context='base')
        if issubclass(cls, BaseEntity):
            entity = await cls(dbid, *args, **kwargs)
            return entity

    async def request_quick_match(self, player_session: Session, game_type,  force_use_map=None):
        """ Запрос игры
            @param player_session: сессия запрашивающего игрока
            @param game_type: тип игры
            @param force_use_map: принудительное использование карты
        """
        extra = {'force_use_map': force_use_map}
        return await self.match_making.request_game_for_player(game_type, player_session, extra)

    @rmi(Exposed, access=0)
    def OnDedicatedServerReset(self, dedic_id: int32):
        """ Вызывается dedicated сервером при его сбросе
            @param dedic_id: идентификатор dedicated сервера
        """
        INFO_MSG(f"Match/dedicated with id={dedic_id} server reseted")
        self.match_making.reset_match(dedic_id)

    @rmi(Latent, Exposed, BlueprintCallable, access=0)
    async def GetExposedStorages(self, digest: FString) -> (Bool, FBytes, FString):
        """ Возвращает все открытые хранилища запрашивающему клиенту
            @return сериализованный архив данных
        """
        INFO_MSG(f"Request storages. User digest: {digest}, service digest: {self.storages_hash}")

        if digest == self.storages_hash:
            return False, bytes(b"\0\0\0\0"), str()
        else:
            serialized = BinarySerialization()
            for storage in storage_list:
                if AvailableEverywhere in storage.specifiers:
                    try:
                        serialized << storage.get().serialize()
                    except AttributeError:
                        ERROR_MSG("Failed to serialize %s" % storage.name)

            archive = serialized.get_archive()
            compressed = zlib.compress(archive, 1)

            archived = BinarySerialization()
            archived << len(archive)
            archived << compressed

            return True, archived.get_archive(), self.storages_hash

    @rmi(Exposed, BlueprintCallable, access=0)
    async def PrintTime(self):
        INFO_MSG(f"Time now: {self.time()}")

    def arena_exit(self, session):
        """ Выход сессии из арены и выписывание её из списка
            @param session: сессия игрока
        """
        self.match_making.request_player_exit_from_game(session)

    @rmi(Exposed, BlueprintCallable, access=0)
    async def TestTimespan(self, T: FTimespan) -> FTimespan:
        INFO_MSG(T)
        from datetime import timedelta
        return T

    @rmi(Exposed, BlueprintCallable, access=0)
    async def MatchDone(self, match_id: int32, winner_team_id: int32):
        INFO_MSG("Match done %i" % (match_id))
        self.match_making.done_game(match_id, winner_team_id)

    @rmi()
    async def GetDebugInfo(self) -> TMap[int32, FString]:
        entities = EntitiesDispatcher().entities

        result = dict()
        for e in entities.values():
            result[e.internal_id] = f"Entity [{'%3s' % getattr(e, 'internal_id', ' - ')} / {'%3s' % getattr(e, 'dbid', ' - ')}] {e.__class__.__name__}: {repr(e)}".replace("<", "&lt").replace(">", "&gt;")
        return result

    @rmi()
    async def GetEntityViewInfo(self, entity_id: int32) -> FString:
        entity = EntitiesDispatcher().entities.get(entity_id, None)
        if entity is None:
            return f"[No entity with id {entity_id}]"

        result = f"Entity {repr(entity).replace('>', '&gt;').replace('<', '&lt;')} <br> <table><tr><td>"

        result += "<table>"
        for property_name, property_info in entity.properties.items():
            result += f"""<tr><td><font color=blue>{property_name}</font>: {repr(getattr(entity, property_name, None)).replace('>', '&gt;').replace('<', '&lt;')}</td></tr>"""
        result += "</table>"

        result += "</td></tr><tr><td>"

        result += "<hr><table>"
        for display_attributes_name in entity.display_attributes:
            result += f"""<tr><td><font color=gray>{display_attributes_name}</font>: {repr(getattr(entity, display_attributes_name, None)).replace('>', '&gt;').replace('<', '&lt;')}<br></td></tr>"""
        result += "</table>"

        result += "</td></tr></table>"

        if hasattr(entity, 'display_actions'):
            for action_function in entity.display_actions:
                result += f'''<input type="button" size="40" value="{action_function.__name__}" onclick="CallDisplayAction('{action_function.__name__}', {entity_id});"> '''

        result += '<hr>'

        return result

    @rmi()
    async def GetGenericStateInfo(self) -> FBaseAppGenericStateInfo:
        info = FBaseAppGenericStateInfo(
            AppName=Globals.service_name,
            Players=[{"username": ses[0].username,
                      "register_date": str(ses[0].user_meta.get("RegisterDate", None)),
                      "online_date": str(ses[0].login_date),
                      } for ses in self.sessions.values()],
            Games=self.match_making.get_games_info()
        )

        return info

    def get_online_players_count(self):
        online = len(self.sessions)
        in_game = len([ses[0] for ses in self.sessions.values() if ses[0].currently_in_game])
        return online, in_game

    @rmi()
    async def CallDisplayAction(self, entity_id: int32, action_name: FString):
        entity = EntitiesDispatcher().entities.get(entity_id, None)
        if entity is not None:
            action = getattr(entity, action_name, None)
            if action is not None:
                action()

    def find_user_by_access_token(self, access_token) -> 'Session':
        for ses, token in self.sessions.values():
            if access_token == token:
                return ses

    @rmi(Exposed, access=0)
    def CrashReport(self, pid: int32, error_hist: FString, error_message: FString, existent_access_token: FString, is_server: Bool):
        username = "[unknown]"
        ses = None
        if existent_access_token:
            ses = self.find_user_by_access_token(existent_access_token)
            username = ses.username if ses else "[DEDICATED SERVER]"
        ERROR_MSG(f"Application UE4App ({'server' if is_server else 'client'}) {pid} has been crashed\n"
                  f"Error message: {error_message}\n"
                  f"Error history: {error_hist}\n"
                  f"{'Possibly by user' if ses else 'By'} {username}\n")

    @rmi(Exposed, access=0)
    def PlayerLogout(self, access_token: FString):
        session = self.find_user_by_access_token(access_token)
        if session:
            INFO_MSG(f"Player {access_token} logged out")
            self.match_making.request_player_exit_from_game(session)

    @rmi(Exposed, access=0)
    async def RequestCustomLocalNetworkVersion(self) -> int32:
        local_network_version = UE4AppConfig.CustomLocalNetworkVersion
        return local_network_version if local_network_version else 0

    @rmi()
    def ExecuteMatchConsoleCommand(self, match_id: int32, cmd: FString):
        INFO_MSG(f"Exec console command at {match_id}: {cmd}")
        self.match_making.exec_cmd(match_id, cmd)

    @rmi(Exposed, access=0)
    async def MakeStatisticsRecordScoresFromDedicatedServer(self, user_access_token: FString, game_id: int32, scores: int32):
        INFO_MSG(f"Make statistics record for {user_access_token} {game_id}: {scores}")
        user = self.find_user_by_access_token(user_access_token)
        if user:
            game = self.match_making.get_game(game_id)
            game_type = game.game_type
            await self.db.MakeStatisticsRecordScores(0, user.Username, game_type, scores)