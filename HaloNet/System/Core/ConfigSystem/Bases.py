# from Core.Utils import error
from copy import copy
from functools import partial
from typing import Dict, Union, Type, TypeVar

import os
import sys

from Core.Common.Helpers import classprop, Singleton, get_mac
from Core.ExceptionsRegistry import NetException

__all__ = 'AppKind', "UnknownRegion", "ConfigBase", "StaticAppInfo", "AppConfig", "SingleApp", \
    "StaticApp", "DynamicApp", "Configuration"


class AppKind:
    Unknown = 0
    Single = 1
    Static = 2
    Dynamic = 3


UnknownRegion = "UnknownRegion"


class Configuration(metaclass=Singleton):

    configs: Dict[str, 'ConfigBase'] = dict()

    def register(self, name, cls):
        self.configs[name] = cls

    def __getitem__(self, item) -> 'ConfigBase':
        return self.configs.get(item, None)


class ConfigBaseMeta(type):
    @classmethod
    def __prepare__(mcs, cls_name, bases, **kwargs):
        result = dict()
        for base in bases:
            for name, value in base.__dict__.items():
                if isinstance(value, (ConfigBase, str, tuple, list, int, float)):
                    result[name] = copy(value)

        return result


class ConfigBase(metaclass=ConfigBaseMeta):
    Description = "No description"
    Name = None

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __init_subclass__(cls, **kwargs):
        if cls.__doc__:
            cls.Description = cls.__doc__

        for kw_key in kwargs:
            if kw_key.lower() == 'name':
                cls.Name = kwargs[kw_key]
        else:
            if kwargs.get('basic', False):
                cls.Name = cls.__name__

        Configuration().register(cls.Name, cls)

    def __copy__(self):
        result = self.__class__()
        for name, value in self.__dict__.items():
            if not name.startswith('__'):
                value = copy(value)
                setattr(result, name, value)
        return result

    T = TypeVar('T')
    @classmethod
    def get(cls: T) -> T:
        return Configuration()[cls.Name]


class StaticAppInfo(ConfigBase):
    Endpoint = '0.0.0.0', 0
    ExposedIP = '0.0.0.0'
    Region = UnknownRegion
    Index = 0  # todo for view name with index in console



class AppConfig(ConfigBase):
    __by_context:       Dict[str, 'AppConfigType'] = dict()
    __by_name:          Dict[str, 'AppConfigType'] = dict()
    __context_by_name:  Dict[str, str] = dict()


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.Context and cls.Name:
            cls.__by_context[cls.Context] = cls
            cls.__by_name[cls.Name] = cls
            cls.__context_by_name[cls.Name] = cls.Context


    @classprop
    def by_context(cls):
        return cls.__by_context

    @classprop
    def by_name(cls):
        return cls.__by_name

    @classprop
    def context_by_name(cls):
        return cls.__context_by_name

    @classmethod
    def get_endpoint(cls):
        raise NotImplementedError()

    @classmethod
    def get_exposed_ip(cls):
        raise NotImplementedError()

    @classmethod
    def get_region(cls):
        raise NotImplementedError()

    Name = None
    Context = None
    IsExposed = False
    IsClient = False
    IsExposedApp = False
    Kind = AppKind.Unknown
    Path = None
    Args = ()
    NoPython = False
    NoServer = False
    Machines: Dict[str, StaticAppInfo]
    DisableLog = False



AppConfigType = Union[AppConfig, StaticAppInfo]


class SingleApp(AppConfig, StaticAppInfo):
    Kind = AppKind.Single

    @classmethod
    def get_endpoint(cls):
        return cls.Endpoint

    @classmethod
    def get_exposed_ip(cls):
        return cls.ExposedIP

    @classmethod
    def get_region(cls):
        return cls.Region


class NotConfiguredError(NetException):
    pass


class StaticApp(AppConfig):
    Kind = AppKind.Static
    Machines: Dict[str, StaticAppInfo] = dict()

    @classmethod
    def get_endpoint(cls):
        mac = get_mac()
        if mac in cls.Machines:
            return cls.Machines[get_mac()].Endpoint
        else:
            raise NotConfiguredError(f"StaticApp not configured, MAC address {mac} not specified")

    @classmethod
    def get_exposed_ip(cls):
        mac = get_mac()
        if mac in cls.Machines:
            return cls.Machines[get_mac()].ExposedIP
        else:
            raise NotConfiguredError(f"StaticApp not configured, MAC address {mac} not specified")

    @classmethod
    def get_region(cls):
        mac = get_mac()
        if mac in cls.Machines:
            return cls.Machines[mac].Region
        else:
            raise NotConfiguredError(f"StaticApp not configured, MAC address {mac} not specified")

class DynamicApp(AppConfig):
    Kind = AppKind.Dynamic
    StartupServices: Dict[str, int] = dict()

class OutputStyle:
    Absent = 0
    FullPythonStyle = 1
    CPPStyle = 2
    ShortInformative = 3


class ConfigGlobals(ConfigBase):
    Name = "Globals"
    UE4GeneratorSourcePath = ""
    UE4GeneratorSourceEditorPath = ""
    PythonExecutable = "python"
    UE4EditorGameModuleName = ""
    Version = "1.0"
    UseVersionGeneratorSignature = False
    DisabledLogs = []
    Sentry = None
    LatentFunctionsSupported = True
    SuppressedWarnings = ["TYPE_NEGLECT"]
    LoggingFilename = os.path.join("logs", "viper")
    ClearMissingEntitiesDBIDs = False  ## TODO: bugous
    OutputEntryStyle = OutputStyle.ShortInformative
    ProjectName = None
