from Core.ConfigSystem.Bases import *


class DBConfigInfo(ConfigBase):
    Host: str = "127.0.0.1"
    Port: int = 5432
    Database: str = "Unknown"
    User: str = "Broly"
    Password: str = "123456"


class UserInfoConfig(ConfigBase):
    mail: str = "broly@gods.com"
    login: str = 'broly'
    password: str = 'lolushki'


class SMTPConfigInfo(ConfigBase):
    Use: bool = False
    Server: str = "unknown.com:123"
    Source = UserInfoConfig()


class SupervisorConfigBase(SingleApp):
    """ Supervisor service """
    Name = "Supervisor"
    Context = 'sv'


class DaemonConfigBase(StaticApp):
    """ Dæmon """
    Name = "Daemon"
    Context = 'da'


class LoginAppConfigBase(StaticApp):
    """ Сервис логина пользователей """
    Name = "LoginApp"
    Context = 'LoginApp'
    IsExposedApp = True


class BaseAppConfigBase(DynamicApp):
    """ Сервис бизнес-логики и различных других геймплейных операций """
    Name = "BaseApp"
    Context = "base"
    IsExposed = True


class DBAppConfigBase(DynamicApp):
    """ Сервис-контроллер базы данных """
    Name = "DBApp"
    Context = 'db'
    DBConfig = DBConfigInfo()


class SiteConfigBase(StaticApp):
    """ Сайт """
    Name = "Site"
    SMTP = SMTPConfigInfo()
    RoutingEndpoint = '0.0.0.0', 0


class UE4AppConfigBase(DynamicApp):
    """ Незапускаемый напрямую сервис-пустышка для генерации исходников HaloNet проекта UE4 """
    Name = "UE4App"
    Context = "ue4"
    IsClient = True
    NoPython = True
    GamePort = 7777
    Path = ("C:/Path/To/Your/UE4/Engine.exe", "C:/Optional/Path/To/Your/Project.uproject")
    Args = ('-server', '-log')
    CustomLocalNetworkVersion = 0


class GenConfigBase(SingleApp):
    """ Сервис-генератор """
    Name = "Gen"


class DevSrvConfigBase(SingleApp):
    Name = "DevSrv"