import asyncio
import sys
from functools import partial

# from win32con import DETACHED_PROCESS

import HaloNet
from Config import SupervisorConfig
from Core.Common.Helpers import get_mac
from Core.ConfigSystem.AppsConfig import DaemonConfigBase
from Core.ConfigSystem.Bases import ConfigGlobals
from Core.Framework import *
import subprocess
import time

from Core.Service import WakeupError
from Core.Utils import call_later
import os
from subprocess import call
# from os import fork


@runnable
class Daemon(Service):
    config: DaemonConfigBase

    def get_region(self):
        return self.config.get_region()

    async def done(self):
        self.supervisor_loop_task = asyncio.Task(self.supervisor_find_loop())
        self.supervisor_mailbox = None
        self.daemon_registered = False
        self.registed_daemon_id = None
        self.dedicated_server_port_counter = 7070

        # await asyncio.sleep(5)
        # self.terminate()

    def terminate(self):
        # args = list(sys.argv)[1:]
        # proc = subprocess.Popen([ConfigGlobals.PythonExecutable, "updater.py", ConfigGlobals.PythonExecutable, __file__] + args, creationflags=DETACHED_PROCESS)
        # time.sleep(1.)
        super().terminate()

    async def supervisor_find_loop(self):
        INFO_MSG("Search for supervisor started")
        while True:
            await asyncio.sleep(1.0)
            if self.supervisor_mailbox is None or not is_valid(self.supervisor_mailbox):
                supervisor_endpoint = SupervisorConfig.Endpoint
                self.supervisor_mailbox = await self.make_mailbox("sv", "Supervisor", supervisor_endpoint)
                self.daemon_registered = False
                if is_valid(self.supervisor_mailbox):
                    INFO_MSG("Supervisor found")
                    while not self.daemon_registered:
                        try:
                            self.registed_daemon_id = await asyncio.wait_for( self.supervisor_mailbox.NewDaemon(get_mac()), 10 )
                            self.daemon_registered = True
                            INFO_MSG("Daemon registered in supervisor with id=%i!" % self.registed_daemon_id)
                        except asyncio.TimeoutError:
                            WARN_MSG("Failed to register daemon, TimeoutError")
                else:
                    WARN_MSG("Supervisor not found... Search again")

    @rmi()
    async def WakeupServiceLocally(self,
                                   service_name:    FString,
                                   port:            int32,
                                   index:           int32,
                                   arguments:       TMap[FString, FString]) -> (Service, int32, FString):
        """
        Поднять процесс сервиса
        @param service_name: имя сервиса
        @param port: серверный прот для прослушивания
        @param index: индекс сервиса
        @param arguments: мапа аргументов
        @return: мейлбокс сервиса
        """
        region = self.config.get_region()
        mbox, pid = await self.async_wakeup_service_locally_by_name(service_name, arguments, port, index)
        return mbox, pid, region

    @rmi()
    async def WakeupDedicatedServerLocally(self,
                                           service_name:    FString,
                                           map_name:        FString,
                                           base_ip:         FString,
                                           base_port:       int32,
                                           port:            int32,
                                           index:           int32,
                                           ue4_arguments:   TMap[FString, FString],
                                           arguments:       TMap[FString, FString]) -> (Service, int32):
        """
        Поднять Dedicated Server
        @param service_name: имя сервиса
        @param map_name: имя карты для сервера
        @param port: порт для игры
        @param index: индекс сервиса
        @param ue4_arguments: аргументы для движка вида (?param=value&param2=value2)
        @param arguments: мапа аргументов
        @return: мейлбокс сервиса
        """
        if port == 0:
            port = self.dedicated_server_port_counter
            self.dedicated_server_port_counter += 1
        return await self.async_wakeup_dedicated_server_locally_by_name(service_name, map_name, base_ip, base_port, ue4_arguments, arguments, port, index)
