import argparse
import os
import sys
import signal
from functools import partial
from time import time

import psutil

from Core.CommandLine import CommandLine
from Core import ERROR_MSG, WARN_MSG, Log
from Core import INFO_MSG
from Core.Access import Access, AccessLevel
from Core.AsyncObj import AsyncObj
from Core.ConfigSystem.AppsConfig import UE4AppConfigBase
from Core.ConfigSystem.Bases import Configuration, AppConfig, AppConfigType, AppKind, ConfigGlobals
from Core.Declarators.Specs import CaptureConnection, Exposed
from Core.Declarators.rmi import rmi
from Core.Entity import Entity
from Core.ExceptionsRegistry import NetException
from Core.GlobalManagers import EntitiesDispatcher
from Core.LocalDatatypes import int32, FString
from Core.TCP.TestProtocolClient import TCPClient, create_connection
from Core.TCP.TestProtocolServer import create_server
from Core.ClientConnectionHandler import ClientConnectionHandler
from Core.Globals import Globals
import subprocess

import asyncio

from Core.Utils import is_valid, get_retcode_descr


class WakeupError(NetException):
    pass


class Service(Entity):
    is_main_entity = True
    is_exposed = False
    entity_type = "service"
    context_name = "unknown"

    endpoint = "0.0.0.0", 9900

    child_service_port_start = 9090
    max_services = 10  # unused
    max_dedicated_servers = 4

    @property
    def entities(self):
        return EntitiesDispatcher().entities

    def next_port(self):
        r = self.next_service_port
        self.next_service_port += 1
        return r

    def get_region(self):
        return CommandLine.get_arguments().region

    async def __ainit__(self):
        await super().__ainit__()
        self.started_time = time()
        args = self.get_args()

        self.next_service_port = self.child_service_port_start

        cls_name = self.__class__.__name__

        config: AppConfigType = Configuration()[cls_name]

        if not config:
            ERROR_MSG("Failed to read config! There is no section for %s" % cls_name)
        self.config = config

        Globals.no_logging = self.config.DisableLog

        # INFO_MSG('~')
        if self.config.Kind in [AppKind.Single, AppKind.Static]:
            self.endpoint = self.config.get_endpoint()
            self.exposed_ip = self.config.get_exposed_ip()

        # INFO_MSG("Test")
        if args.service_port is not None:
            self.endpoint = self.endpoint[0], args.service_port

        # ERROR_MSG(f"T {args.causer_exposed_ip}")
        if not args.causer_exposed_ip or args.causer_exposed_ip == '0.0.0.0':
            try:
                self.exposed_ip = self.config.get_exposed_ip()
            except NotImplementedError:
                self.exposed_ip = '...'

        serving = not self.config.NoServer
        self.tcp_server = await create_server(self.endpoint, serving)

        Globals.disabled_log_categories = ConfigGlobals.DisabledLogs

        if not self.get_args().silent:
            INFO_MSG("%s started! with %s" % (cls_name, self.get_args()))
            INFO_MSG("%s started at %s (%s)" % (cls_name, self.endpoint if serving else "None", self.get_region()))
            INFO_MSG("Version: %s, generator signature: %s" % (Globals.version, Globals.generator_signature))
            INFO_MSG("Description: %s" % self.config.Description)

        self.processes = dict()

        self.postfix = self.get_args().postfix

        if args.causer_exposed_ip and args.causer_exposed_ip != '0.0.0.0':
            self.exposed_ip = args.causer_exposed_ip
            INFO_MSG(f"Causer exposed {self.exposed_ip}")

        await self.start()

        self.dedicated_servers = list()

        if args.causer_ip is not None and args.causer_port is not None:
            INFO_MSG(f"Call to causer: {args.causer_ip}:{args.causer_port}")
            mbox = await Service.make_mailbox("base", "Service", (args.causer_ip, args.causer_port))
            await mbox.TellPID(os.getpid())
        # ERROR_MSG(f"{self.exposed_ip}")

    def terminate(self):
        INFO_MSG(f"Service {self.get_class_name()} going to be stopped")

        def on_terminate(proc):
            process_info = self.processes.get(proc.pid)
            status = proc.status()
            WARN_MSG("Process did't terminated after timeout. pid: %s, status: %s, info: %s", proc.pid, status, process_info)

        processes = []
        for pid, info in self.processes.items():
            process = psutil.Process(pid)
            processes.append(process)
            process.terminate()
            INFO_MSG(f"Service {self.get_class_name()}. Send terminate to {info['name']}, status: {process.status()}, pid_exists: {psutil.pid_exists(pid)}")

        if processes:
            try:
                from time import sleep
                # sleep(5)
                # for i in processes:
                #     INFO_MSG(f"1 Service {self.get_class_name()}. -- {i.pid} --, status: {i.status()}, pid_exists: {psutil.pid_exists(i.pid)}")
                gone, alive = psutil.wait_procs([i for i in processes if i.status() != psutil.STATUS_ZOMBIE], timeout=60, callback=on_terminate)
                # todo: Some strange sings here
            except Exception as e:
                WARN_MSG(f"Service {self.get_class_name()} exception {e}")
        INFO_MSG(f"Service {self.get_class_name()} is stopped")
        sys.exit(0)

    def time(self):
        return time() - 1_493_121_313.74268  # уменьшаем

    async def start(self):
        """ Вызывается при готовности работы сервиса """

    async def done(self):
        pass

    def sigterm_handler(self, signal, frame):
        INFO_MSG(f"sigterm_handler {self.get_class_name()} going to be stopped")
        self.terminate()

    @classmethod
    def __run__(cls, *args, **kwargs):
        Globals.access_token = Access().register_access("SUPER INTERNAL ACCESS", AccessLevel.Internal)
        Globals.service_name = cls.__name__ + CommandLine.get_arguments().postfix
        service_instance = cls(*args, **kwargs)
        Globals.this_service = service_instance

        signal.signal(signal.SIGTERM, service_instance.sigterm_handler)
        # signal.signal(signal.SIGBREAK, service_instance.sigterm_handler)
        signal.signal(signal.SIGINT, service_instance.sigterm_handler)

        try:
            asyncio.get_event_loop().run_until_complete(service_instance)  # this calls __await__
            asyncio.get_event_loop().run_until_complete(service_instance.done())
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            INFO_MSG("Preparing to shut down service...")
        except Exception as exc:
            from traceback import print_exc
            ERROR_MSG("Exception raised:", exc)
            print_exc()
            INFO_MSG("Press enter to continue")
            input()
            print("What's your name?\n> ", end="")
            name = input()
            print(f"{name}, how did you come to this?\n> ", end="")
            reason = input()
            WARN_MSG(f'The program has been stopped, the {name} provoked an error, and says: "{reason}". Dismiss him')

    async def create_client_connection(self, endpoint, on_lost=None):
        INFO_MSG(f"{endpoint}")
        if endpoint not in self.tcp_server.clients:
            _, connection = await create_connection(endpoint, on_lost=on_lost)#  await TCPClient(endpoint, ClientConnectionHandler, do_open_connection=True)
            if is_valid(connection):
                self.tcp_server.clients[endpoint] = connection
                connection.add_lost_callback(partial(self.on_lost_client, endpoint))
            return connection
        else:
            self.tcp_server.clients[endpoint].add_lost_callback(on_lost)
        connection = self.tcp_server.clients[endpoint]
        connection.add_lost_callback(partial(self.on_lost_client, endpoint))
        if not is_valid(connection):
            del self.tcp_server.clients[endpoint]
        return connection

    def on_lost_client(self, endpoint, connection):
        if endpoint in self.tcp_server.clients:
            del self.tcp_server.clients[endpoint]

    async def stop(self):
        await self.tcp_server.close()
        # await self.service_future.stop()
        asyncio.get_event_loop().stop()
        # asyncio.get_event_loop().call_soon_threadsafe(asyncio.get_event_loop().close)

    def get_args(self):
        return CommandLine.get_arguments()

    def open_process(self, service_path, arguments=list(), is_python_process=True, extented_param=None, **kwargs):
        cmd_kwargs = list()

        kwargs['no_color_patterns'] = CommandLine.get_arguments().no_color_patterns

        for key, value in kwargs.items():
            if CommandLine.has_arg(key):
                arg_type = CommandLine.get_arg_type(key)
                kwarg = "-%s=%s" % (key, arg_type(value))
                cmd_kwargs.append(kwarg)
            else:
                ERROR_MSG("Unable to pass %s parameter, not exists in CommandLine.py: Arguments class" % key)

        # cmd_kwargs = ["-%s=%s" % (key, value) for key, value in kwargs.items()]
        cmd_args = list()
        python_executable_name = ConfigGlobals.PythonExecutable
        if is_python_process:
            cmd_args.append(python_executable_name)
        cmd_args.extend(service_path) if isinstance(service_path, list) else cmd_args.append(service_path)
        if extented_param is not None:
            cmd_args.append(extented_param)
        cmd_args.extend(cmd_kwargs)
        cmd_args.extend(arguments)

        process = subprocess.Popen(cmd_args, shell=False)

        INFO_MSG(f"Opening process {process.pid}", cmd_args)
        # print(cmd_args)
        return process

    @rmi(CaptureConnection, Exposed, access=0)
    async def TellPID(self, connection, pid: int32):
        """
        Сообщить PID этому сервису
        @param pid: идентификатор процесса
        """
        if pid in self.processes and not self.processes[pid]['future'].done():
            INFO_MSG(f"{connection} ({self.processes[pid]['name']}) tells pid {pid} in {round(time() - self.processes[pid]['opened_at'], 6)} seconds")
            self.processes[pid]['future'].set_result( await self.create_client_connection(self.processes[pid]['endpoint']) )
        else:
            ERROR_MSG("Failed to tell PID! "
                      f"There are no processes runned with pid {pid} or this process already told PID."
                      "Probably you run process which lanuched child process (be sure if this is UE4 dedicated server, "
                      "check the right path, not a PROJECTNAME.exe in root dir)")

    async def async_wakeup_service_locally(self, service_path, arguments, port, is_python_process=True, index=0, name=None):
        INFO_MSG(f"{service_path}, {arguments}, {port}, {is_python_process}, {index}, {name}")
        if arguments is None:
            arguments = dict()
        access_token = Access().generate(AccessLevel.Internal)

        # WARN_MSG(f"Opening (causer {self.exposed_ip}")
        proc = self.open_process(service_path, is_python_process=is_python_process,
                                 service_port=port,
                                 causer_ip=self.endpoint[0],
                                 causer_exposed_ip=self.exposed_ip,
                                 causer_port=self.endpoint[1],
                                 postfix=('[%i]' % index) if index else "",
                                 region=self.config.get_region(),
                                 **arguments,

                                 access_token=access_token,
                                 is_child_process=True)
        future_data = self.processes[proc.pid] = {
            'future': asyncio.Future(loop=asyncio.get_event_loop()),
            'endpoint': (self.endpoint[0], port),
            'opened_at': time(),
            'name': name
        }

        try:
            service_connection = await future_data['future']
        except Exception as e:
            ERROR_MSG("Something went wrong in future", e)
            return None

        return service_connection, proc

    async def async_wakeup_dedicated_server_locally(self, service_path, map_name, base_ip, base_port, ue4_arguments, arguments, keyword_arguments, port, is_python_process=True, index=0, name=None):
        if len(self.dedicated_servers) >= self.max_dedicated_servers:
            raise WakeupError("Unable to wakeup dedicated server. Out of limit")

        if keyword_arguments is None:
            keyword_arguments = dict()

        extented_param = None
        if ue4_arguments is not None:
            extented_param = map_name
            for idx, (key, value) in enumerate(ue4_arguments.items()):
                extented_param += ("?" if idx == 0 else "&") + "%s=%s" % (key, value)

        INFO_MSG("Opening '%s' '%s'" % (service_path, extented_param))

        access_token = Access().generate(AccessLevel.Internal)
        custom_local_network_version = Configuration()['UE4App'].CustomLocalNetworkVersion
        custom_local_network_version = custom_local_network_version if custom_local_network_version else 0

        proc = self.open_process(service_path, is_python_process=is_python_process,
                                 service_port=port,
                                 causer_exposed_ip=self.exposed_ip,
                                 causer_ip=self.endpoint[0],
                                 causer_port=self.endpoint[1],
                                 base_ip=base_ip,
                                 base_port=base_port,
                                 postfix=('[%i]' % index) if index else "[0]",
                                 local_network_version=custom_local_network_version,
                                 arguments=arguments,
                                 **keyword_arguments,

                                 access_token=access_token,
                                 is_child_process=True,
                                 extented_param=extented_param)
        future_data = self.processes[proc.pid] = {'future': asyncio.Future(loop=asyncio.get_event_loop()),
                                                  'endpoint': (self.endpoint[0], port),
                                                  'opened_at': time(),
                                                  'name': name}

        try:
            service_connection = await future_data['future']
            self.dedicated_servers.append(service_connection)
            service_connection.add_lost_callback(lambda conn: self.dedicated_servers.remove(conn))
            INFO_MSG("Total dedicated servers %i" % len(self.dedicated_servers))
        except Exception as e:
            ERROR_MSG("Something went wrong in future", e)
            return None

        return service_connection, proc

    def on_service_connection_lost(self, process: subprocess.Popen, connection):
        try:
            process.wait(1.0)
        except subprocess.TimeoutExpired:
            WARN_MSG(f"Something went wrong with process {process.pid}. Timeout expired")
            return

        if process.returncode:
            WARN_MSG(f"Process {process.pid} has been disconnected with return code {process.returncode} ({get_retcode_descr(process.returncode)}) ")
        else:
            WARN_MSG(f"Process {process.pid} just disconnected")

    async def async_wakeup_service_locally_by_name(self, service_name, arguments=None, port=0, index=0):
        service_config: AppConfigType = Configuration()[service_name]
        if port == 0:
            if service_config.Kind in [AppKind.Static, AppKind.Single]:
                port = service_config.get_endpoint()[1]
            else:
                port = self.next_port()

        if service_config is not None:
            path = service_config.Path
            is_python_service = not service_config.NoPython
            if path is None:
                path = service_name + ".py"
            connection, process = await self.async_wakeup_service_locally(path, arguments, port=port, is_python_process=is_python_service, index=index, name=service_name)
            connection.add_lost_callback(partial(self.on_service_connection_lost, process))
            mailbox = await Service.make_mailbox('base', "Service", connection)
            mailbox.set_service_info(service_name)
            return mailbox, process.pid

    async def async_wakeup_dedicated_server_locally_by_name(self, service_name, map_name, base_ip, base_port, ue4_arguments=None, keyword_arguments=None, port=0, index=0):
        service_config: UE4AppConfigBase = Configuration()[service_name]
        if service_config is not None:
            path = service_config.Path
            is_python_service = not service_config.NoPython
            arguments = service_config.Args
            if path is None:
                path = service_name + ".py"
            connection, process = await self.async_wakeup_dedicated_server_locally(path, map_name, base_ip, base_port, ue4_arguments, arguments, keyword_arguments, port=port, is_python_process=is_python_service, index=index, name=service_name)
            connection.add_lost_callback(partial(self.on_service_connection_lost, process))
            mailbox = await Service.make_mailbox('ue4', "Service", connection)
            mailbox.set_service_info(service_name)
            return mailbox, process.pid

    async def get_single_service(self, service_name):
        service_config: AppConfigType = Configuration()[service_name]
        mailbox = await Service.make_mailbox(service_config.Context, service_name, service_config.Endpoint)
        return mailbox

    @rmi(access=2)
    def Terminate(self):
        """ Завершить процесс """
        asyncio.get_event_loop().call_soon(self.terminate)

    @rmi(access=2)
    async def ExecuteCode(self, code_string: FString) -> FString:
        """
        Выполнить произвольный код 
        @param code_string: строка кода
        @return: результат выполнения кода
        """
        code_string = code_string.replace("$$20", "\n")
        try:
            result = eval(code_string)
            return str(result).replace("<", "&lt;").replace(">", "&gt")
        except Exception as e:
            try:
                code = compile(code_string, "<string>", 'exec')
                exec(code)
            except Exception as e:
                from traceback import print_exc, format_exc
                # print_exc()
                return format_exc()

        return ""
