import asyncio
from functools import partial

from typing import TYPE_CHECKING, Dict, Any, List

from Config import DaemonConfig
from Core.ConfigSystem.Bases import Configuration
from Execptions import TestError

if TYPE_CHECKING:
    from BaseApp import BaseApp
    from UE4App import UE4App

import HaloNet

from Core.Framework import *
from Types import *

LOAD_WEIGHT_LIMIT = 1000


class DaemonInfo:
    def __init__(self, mailbox, daemon_id, load_weight, mac, region):
        self.mailbox = mailbox
        self.daemon_id = daemon_id
        self.load_weight = load_weight
        self.mac = mac
        self.region = region


class ServiceInfo:
    def __init__(self, service_type, mailbox, region="Unknown", load_weight=0):
        self.service_type = service_type
        self.mailbox = mailbox
        self.load_weight = load_weight
        self.region = region

    def inc_load(self):
        self.load_weight += 1

    def dec_load(self):
        self.load_weight -= 1



@runnable
class Supervisor(Service):

    def get_region(self):
        return self.config.get_region()

    async def start(self):
        self.daemons: Dict[Any, DaemonInfo] = dict()
        self.print_total_daemons()
        self.services_names = list()
        self.services: Dict[str, List['Service']] = dict()
        self.is_baseapp_loading = False

        self.services_infos: Dict['Service', 'ServiceInfo'] = dict()

        self.ue4_dedicated_servers = dict()
        await self.start_default_services()

    async def start_default_services(self):
        # todo: be sure the daemon started here
        await self.keep_lifetime_service('DBApp')
        await self.keep_lifetime_service('BaseApp', 1)  # todo temporal
        await self.keep_lifetime_service('LoginApp')
        await self.keep_lifetime_service('Site')

    async def keep_lifetime_service(self, service_name, count=1, region="Unknown"):
        """
        Поднять указанный сервис по имени и следить за его жизнедеятельностью
        Если указан сервис в одном экземпляре, то вернуть его
        @param service_name: название
        @param count: количество
        @param region: регион
        @return: если в одном экземпляре, то вернуть сервис
        """
        for i in range(count):
            srv, pid = await self.Wakeup(service_name, region, {})
            srv.add_lost_callback(lambda: self.on_service_dropped(service_name, srv))
            if count == 1:
                return srv

    async def resurrect_service(self, service_name, srv):
        """
        Вернуть сервис на место
        @param service_name: имя
        @param srv: старый мейлбокс
        """
        if srv in self.services[service_name]:
            self.services[service_name].remove(srv)

            del self.services_infos[srv]

            WARN_MSG(f"{service_name} fell! The service attempts to resurrect them")
            await self.keep_lifetime_service(service_name)

    def on_service_dropped(self, service_name, srv):
        """
        Срабатывает при потере соединия с удалённым сервисом
        @param service_name: имя сервиса
        @param srv: мейлбокс
        """
        asyncio.Task(self.resurrect_service(service_name, srv))

    def weed_daemon(self, daemon):
        """
        Выкинуть демона
        @param daemon: коннекшин на демона
        """
        if daemon in self.daemons:
            del self.daemons[daemon]
        self.print_total_daemons()

    def get_service(self, service_name, index) -> Service:
        services = self.services.get(service_name, list())
        if len(services) > index:
            return services[index]

    @rmi(CaptureConnection)
    async def NewDaemon(self, connection, mac: FString) -> int32:
        """
        Поднять нового демона
        @return: идентификатор демона
        """
        from Daemon import Daemon
        if connection not in self.daemons:
            new_daemon = await Daemon.make_mailbox("da", "Daemon", connection)
            new_daemon.add_lost_callback(partial(self.weed_daemon, connection))
            daemon_id = len(self.daemons)

            daemon_conf: DaemonConfig = Configuration()['Daemon']

            region = daemon_conf.Machines[mac].Region
            self.daemons[connection] = DaemonInfo(new_daemon, daemon_id, 1, mac, region)
            self.print_total_daemons()
            return daemon_id
        return self.daemons[connection].mailbox

    @rmi()
    async def GetBaseAppsGenericStatesInfo(self) -> TArray[FBaseAppGenericStateInfo]:
        state_infos = TArray[FBaseAppGenericStateInfo]()
        for baseapp in self.services.get("BaseApp", list()):
            state_info = await baseapp.GetGenericStateInfo()
            state_infos.append(state_info)
        return state_infos

    @rmi()
    async def GetDedicatedServersCount(self) -> int32:
        """
        Получить количество dedicated серверов
        @return: количество сервисов
        """
        return len(self.services.get("UE4App", list()))

    @rmi()
    async def GetDedicatedServersInfo(self) -> TArray[FDedicatedServerInfo]:
        """
        Получение информации о dedicated серверах
        @return: список информации о dedicated серверах
        """
        result = list()
        for dedic in self.services.get("UE4App", list()):
            dedic: 'UE4App'
            info = await dedic.GetDedicatedServerInfo()
            result.append(info)
        return result

    @rmi()
    async def ExecuteCommandOnDedicatedServer(self, dedicated_server_index: int32, command: FString):
        """
        Запусть команду на dedicated server
        @param dedicated_server_index: индекс сервера
        @param command: текстовая команда
        """
        services = self.services.get("UE4App", list())
        if len(services) > dedicated_server_index:
            service: 'UE4App' = services[dedicated_server_index]
            service.RunConsoleCommand(command)

    @rmi()
    async def ShutdownDedicatedServer(self, dedicated_server_index: int32):
        """
        Положить dedicated server 
        @param dedicated_server_index: индекс сервера 
        """
        services = self.services.get("UE4App", list())
        if len(services) > dedicated_server_index:
            service: 'UE4App' = services[dedicated_server_index]
            service.RunConsoleCommand("quit")
            services.remove(service)

    @rmi()
    async def ResetDedicatedServer(self, dedicated_server_index: int32):
        """
        Перезагрузить dedicated server
        @param dedicated_server_index: индекс сервера 
        """
        dedic = self.get_service("UE4App", dedicated_server_index)
        if dedic:
            await dedic.ResetDedicatedServer()

    @rmi()
    async def Wakeup(self, service_name: FString, region: FString, arguments: TMap[FString, FString]) -> (Service, int32):
        """
        Поднять процесс
        @param service_name: имя сервиса
        @param arguments: аргументы
        @return: мейлбокс сервиса
        """

        daemons_sorted = sorted(self.daemons.values(), key=lambda daemon_info: daemon_info.load_weight)

        if daemons_sorted:
            for daemon_info in daemons_sorted:
                if region != "Unknown" and region != daemon_info.region:
                    continue
                INFO_MSG("Waking up service %s" % service_name)
                srv, pid, region = await daemon_info.mailbox.WakeupServiceLocally(service_name, 0, self.services_names.count(service_name), arguments)
                daemon_info.load_weight += 1
                self.services_names.append(service_name)
                srv.set_service_info(service_name)
                if service_name not in self.services:
                    self.services[service_name] = list()
                self.services[service_name].append(srv)

                self.services_infos[srv] = ServiceInfo(service_name, srv, region)

                return srv, pid

        WARN_MSG("Could not wakeup service! No daemons!")
        await asyncio.sleep(1.0)
        return await self.Wakeup(service_name, region, arguments)

    @rmi()
    async def RequestService(self, service_name: FString) -> Service:
        if service_name not in self.services:
            await self.Wakeup(service_name, {})
        if len(self.services[service_name]) > 0:
            return self.services[service_name][0]
        return None


    @rmi()
    async def WakeupDedicatedServer(self, service_name: FString, map_name: FString, base_ip: FString, base_port: int32, ue4_arguments: TMap[FString, FString], kwarguments: TMap[FString, FString]) -> (Service, int32):
        """
        Поднять dedicated server
        @param service_name: имя сервиса
        @param map_name: имя карты
        @param ue4_arguments: аргументы для UE4 парсера
        @param kwarguments: аргументы командной строки
        @return: мейлбокс сервиса
        """
        for daemon_info in self.daemons.values():
            INFO_MSG("Waking up service %s" % service_name)
            srv, pid = await daemon_info.mailbox.WakeupDedicatedServerLocally(service_name, map_name, base_ip, base_port, 0, self.services_names.count(service_name), ue4_arguments, kwarguments)
            if not srv:
                WARN_MSG("Unable to wakeup dedicated server")
                return None, 0
            srv.add_lost_callback(partial(self.on_lost_dedicated_server, srv))
            self.services_names.append(service_name)
            srv.set_service_info(service_name)
            if service_name not in self.services:
                self.services[service_name] = list()
            self.services[service_name].append(srv)
            return srv, pid
        await asyncio.sleep(1.0)
        return await self.WakeupDedicatedServer(service_name, map_name, base_ip, base_port, ue4_arguments, kwarguments)

    def on_lost_dedicated_server(self, srv):
        if "UE4App" in self.services:
            if srv in self.services['UE4App']:
                self.services["UE4App"].remove(srv)

    @rmi()
    async def RequestDedicatedServer(self, map_name: FString, base_ip: FString, base_port: int32, ue4_arguments: TMap[FString, FString], kwarguments: TMap[FString, FString]) -> Service:
        srv, pid = await self.WakeupDedicatedServer("UE4App", map_name, base_ip, base_port, ue4_arguments, kwarguments)
        return srv

    @rmi()
    async def RequestBaseAppForLogin(self, region: FString) -> TBaseMailbox('BaseApp'):
        """
        Запускает BaseApp в указанном регионе и возвращает Mailbox на него
        @param region: сигнатура региона
        @return: мейлбокс BaseApp'а
        """
        # Ищем BaseApp в списке поднятых и возвращаем его в случае если найденный бейзапп не перегружен
        for srv_info in self.services_infos.values():
            if srv_info.service_type != 'BaseApp' or srv_info.load_weight >= LOAD_WEIGHT_LIMIT:
                continue
            srv_info.inc_load()
            return srv_info.mailbox
        # В ином случае поднимаем новый...
        else:
            # Если в данный момент BaseApp не загружается поднимаем новый и сразу возвращаем его
            if not self.is_baseapp_loading:
                self.is_baseapp_loading = True
                srv = await self.keep_lifetime_service('BaseApp', 1, region)
                self.is_baseapp_loading = False
                return srv
            # В ином случае ждём пока запустится
            else:
                WARN_MSG("BaseApp requested while it's loading")
                await asyncio.sleep(1.0)
                return await self.RequestBaseAppForLogin(region)

    @rmi()
    def Relax(self, srv: Service):
        if srv in self.services_infos:
            self.services_infos[srv].dec_load()

    @rmi()
    async def GetBaseApp(self) -> TBaseMailbox('BaseApp'):
        return self.services['BaseApp'][0]

    async def restart_services(self):
        INFO_MSG("Prepare to restart all services")
        for service_type_name, services_list in self.services.items():
            services_list_copy = list(services_list)
            services_list.clear()
            for service in services_list_copy:
                service.Terminate()
        await asyncio.sleep(.4)
        INFO_MSG("All services terminated")
        await self.start_default_services()



    def print_total_daemons(self):
        INFO_MSG("Total daemons: %i" % len(self.daemons))


    @rmi()
    async def minitest(self):
        print('minitest')
        raise TestError("qwe")