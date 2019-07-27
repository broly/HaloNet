import HaloNet

from Core import INFO_MSG, WARN_MSG
from Core.Access import Access, AccessLevel
from Core.ConfigSystem.AppsConfig import LoginAppConfigBase
from Core.Declarators.Specs import *
from Core.Declarators.rmi import rmi
from Core.LocalDatatypes import *
from Core.OSS import Steam
from Core.OSS.Steam import SteamError
from Core.Service import Service
from Core.Type import TBaseMailbox
from Core.Utils import runnable, make_default_service_mailbox

from Types import *
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from DBApp import DBApp
    from BaseApp import BaseApp
    from Supervisor import Supervisor


LOGIN_DIGEST = 55456

@runnable
class LoginApp(Service):
    config: LoginAppConfigBase

    def get_region(self):
        return self.config.get_region()

    async def start(self):
        # self.db: DBApp = await DBApp.make_mailbox("db", "DBApp", ("127.0.0.1", 9002))
        # self.make_mailbox('sv', "Supervisor", )
        self.supervisor: 'Supervisor' = await make_default_service_mailbox("Supervisor")
        self.db: 'DBApp' = await self.supervisor.RequestService("DBApp")

        self.loggedin_users = dict()


    @rmi(access=2)
    async def RegisterUser(self, username: FString, mail: FString, password: FString, reg_with_mail: Bool) -> (Bool, int32, FString):
        """ Регистрация пользователя
            @param username: имя пользователя
            @param password_hash: хэш пароля
            @return: успех, идентификатор пользователя
        """
        exists = await self.db.GetUserIsExists(username)
        if not exists:
            entity_dbid = await self.db.CreateDefaultEntity("Session")
            register_date = FDateTime.now()
            exists, user_id, digest = await self.db.RegisterUser(username, password, reg_with_mail, mail, AccessLevel.User, entity_dbid, register_date)
            return True, user_id, digest
        return False, 0, ""

    @rmi(access=2)
    async def RegisterUserWithoutPassword(self, username: FString, nickname: FString) -> (Bool, int32):
        """ Регистрация пользователя
            @param username: имя пользователя
            @param password_hash: хэш пароля
            @return: успех, идентификатор пользователя
        """
        exists = await self.db.GetUserIsExists(username)
        if not exists:
            entity_dbid = await self.db.CreateDefaultEntity("Session")
            register_date = FDateTime.now()
            exists, user_id = await self.db.RegisterUserWithoutPassword(username,
                                                                        nickname,
                                                                        AccessLevel.User,
                                                                        entity_dbid,
                                                                        register_date)
            return True, user_id
        return False, 0

    @rmi(Latent, Exposed, BlueprintCallable, access=0)
    async def LoginViaSteam(self,
                            SessionTicket: FString,
                            digest: int32) -> (TBaseMailbox('BaseApp'),
                                               ELoginResult,
                                               FString):
        try:
            steam_id, nickname = Steam.BeginAuthSession(SessionTicket)
            return await self.GenericLogin("Steam", steam_id, digest=digest, nickname=nickname)
        except SteamError:
            return None, ELoginResult.InvalidSessionToken, ""


    @rmi(Latent, Exposed, BlueprintCallable, access=0)
    async def Login(self,
                    username: FString,
                    password: FString,
                    digest: int32) -> (TBaseMailbox('BaseApp'),
                                       ELoginResult,
                                       FString):
        """ Логин пользователя
            @param username: имя пользователя
            @param password: пароль
            @return мейлбокс сессии, успех, токен доступа
        """
        return await self.GenericLogin('NULL', username, password=password, digest=digest)

    async def GenericLogin(self, login_type, unique_id, password=None, digest=None, nickname=None):
        INFO_MSG(f"Logging in the user {unique_id}: {password} (via {login_type})")
        if digest != LOGIN_DIGEST:
            return None, ELoginResult.InternalError, ""

        if password is not None:
            login_result_status, id, access, dbid, reg_date = await self.db.FindUserForLogin(unique_id, password)
        else:
            login_result_status, id, access, dbid, reg_date = await self.db.FindUserForLoginWithoutPassword(unique_id)

        # TODO: Temporary
        if login_result_status == ELoginResult.NotExists:
            WARN_MSG("Login failed, register it and try again")
            if password is not None:
                await self.RegisterUser(unique_id, "", password, False)
            else:
                if nickname is None:
                    raise NotImplementedError("Login without password is not supported without nickname")
                await self.RegisterUserWithoutPassword(unique_id, nickname)
            return await self.GenericLogin(login_type, unique_id, password=password, digest=digest, nickname=nickname)

        if login_result_status != ELoginResult.Success:
            return None, login_result_status, ""

        success = False
        access_token = ""

        if id not in self.loggedin_users:
            region = self.config.get_region()
            base: 'BaseApp' = await self.supervisor.RequestBaseAppForLogin(region)
            if base:
                access_token = Access().generate(access)

                if nickname is None:  # todo: temp
                    nickname = unique_id

                success = await base.PrepareForJoin(nickname, access_token, id, dbid, self)

                if success:
                    self.loggedin_users[id] = {
                        'base': base,
                        'access_token': access_token,
                    }
                else:
                    WARN_MSG(f"BaseApp does not want to take user {unique_id}")
                    login_result_status = ELoginResult.Rejected
            else:
                login_result_status = ELoginResult.InternalError
                WARN_MSG(f"Failed to login user, there are no active BaseApps")

        else:
            base = self.loggedin_users[id]['base']
            access_token = self.loggedin_users[id]['access_token']
            success = True

        if not success:
            WARN_MSG(f"Failed to login user {unique_id} ({login_result_status})")
            base = None
            access_token = ""

        return base.as_exposed(), login_result_status, access_token

    @rmi()
    def InternalLogout(self, base: TBaseMailbox('BaseApp'), user_id: int32):
        INFO_MSG(f"User {user_id} logout")
        del self.loggedin_users[user_id]
        self.supervisor.Relax(base)