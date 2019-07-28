from Core.ConfigSystem.AppsConfig import *
from Core.ConfigSystem.Bases import ConfigGlobals, OutputStyle


class SupervisorConfig(SupervisorConfigBase):
    Endpoint = "127.0.0.1", 9004


class SupervisorWebConfig(SupervisorConfigBase, name="SupervisorWeb"):
    Endpoint = "127.0.0.1", 9004
    RoutingEndpoint = '127.0.0.1', 8005


class DaemonConfig(DaemonConfigBase):
    Machines = {
        "02:06:51:50:31:61": StaticAppInfo(Endpoint=("127.0.0.1", 8001), ExposedIP="127.0.0.1", Region='RU', Index=0)
    }


class LoginAppConfig(LoginAppConfigBase):
    Machines = {
        "02:06:51:50:31:61": StaticAppInfo(Endpoint=("127.0.0.1", 9000), ExposedIP="127.0.0.1", Region='RU', Index=0)
    }


class BaseAppConfig(BaseAppConfigBase):
    StartupServices = {
        "RU": 2
    }


class DBAppConfig(DBAppConfigBase):
    DBConfig: DBConfigInfo
    DBConfig.Host = "127.0.0.1"
    DBConfig.Port = 5432
    DBConfig.Database = "viper"
    DBConfig.User = "broly"
    DBConfig.Password = "123456"


class SiteConfig(SiteConfigBase, name="Site"):
    Machines = {
        "02:06:51:50:31:61": StaticAppInfo(Endpoint=("127.0.0.1", 8003), Region='RU'),
    }
    RoutingEndpoint = '127.0.0.1', 8004
    SMTP: SMTPConfigInfo
    SMTP.Use = False
    SMTP.Server = "smtp.gmail.com:587"
    SMTP.Source.mail = "theupperdivine@gmail.com"
    SMTP.Source.login = "theupperdivine@gmail.com"
    SMTP.Source.password = "geratestdivinepassword"


class UE4AppConfig(UE4AppConfigBase):
    Path = [
        "C:\\Program Files\\Epic Games\\UE_4.19\\Engine\\Binaries\\Win64\\UE4Editor.exe",
        "C:\\HaloNet\\Example\\Example.uproject"
    ]
    Args += '-debug',
    CustomLocalNetworkVersion = 100500


class GenConfig(GenConfigBase):
    Endpoint = "127.0.0.1", 8000


class DevSrvConfig(DevSrvConfigBase):
    Endpoint = "127.0.0.1", 8111


class Tests(SingleApp, basic=True):
    Endpoint = "127.0.0.1", 8111


class GameConfig(ConfigBase, basic=True):
    campaign_kick_after_logout_time = 120.
    campaign_time_to_autoselect_battleside = 60.

    player_live_in_offline_timeout = 10.

    time_to_dump_online = 60
    time_to_start_dump_online = 60

# class DevSrv(SingleApp, name="DevSrv"):
#     pass

ConfigGlobals.UE4GeneratorSourcePath = 'C:/HaloNet/Example/Source/Example/HaloNet'
ConfigGlobals.UE4GeneratorSourceEditorPath = "C:/HaloNet/Example/Source/Example/HaloNet"
ConfigGlobals.UE4EditorGameModuleName = "ExampleEditor"
ConfigGlobals.Redmine = {
                          "host": "http://62.76.114.56:3000",
                          "api_access_key": "b4d3fe82f464c68c280e510794fb7f24cc3cf6ab",
                          "project_id": 1
                        }
ConfigGlobals.UseVersionGeneratorSignature = True
ConfigGlobals.OutputEntryStyle = OutputStyle.FullPythonStyle
ConfigGlobals.ProjectName = "Example"
