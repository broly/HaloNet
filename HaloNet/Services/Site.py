import asyncio
import json
from copy import deepcopy
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from typing import TYPE_CHECKING

from aiohttp import web

import HaloNet

from Core.ConfigSystem.AppsConfig import SiteConfigBase
from Core.Framework import *
from Types import FOnlineStatisticEntry

if TYPE_CHECKING:
    from BaseApp import BaseApp

from Core.SiteUtils import route, web_run_app, from_file
from Core.Type import TypeBase
from Core.Utils import PyCharm_go_to, UnrealEngine4_go_to
import smtplib
from email.mime.text import MIMEText



@runnable
class Site(Service):
    config: SiteConfigBase

    async def start(self):
        from Supervisor import Supervisor
        self.sv = await self.get_single_service("Supervisor")
        self.base: 'BaseApp' = await self.sv.RequestService("BaseApp")
        self.supervisor: Supervisor = await make_default_service_mailbox("Supervisor")

        self.web_app = web.Application(loop=asyncio.get_event_loop())

        for r in self.__routes__:
            self.web_app.router.add_route(r['method_type'], r['path'], getattr(self, r['method']))

        self.web_app.router.add_static('/static/', f"{Globals.workspace}/Services/{self.__class__.__name__}/static",
                                       show_index=True,
                                       follow_symlinks=True)
        # self.web_init()

        if self.smtp_used:
            self.smtp = smtplib.SMTP(self.config.SMTP.Server)
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.config.SMTP.Source.login, self.config.SMTP.Source.password)
        else:
            self.smtp = None


        self.srv, self.srv_handler = await web_run_app(self.web_app,
                                                       host=self.config.RoutingEndpoint[0],
                                                       port=self.config.RoutingEndpoint[1],
                                                       print=INFO_MSG)

    def __adel__(self):
        if self.smtp:
            self.smtp.quit()

    @property
    def smtp_used(self):
        return self.config.SMTP.Use

    @route(route_path='/')
    async def index(self, req: web.Request):
        return dict(BASE_ACTIVE=is_valid(self.base))

    # @route()
    # async def reg(self, req: web.Request):
    #     if is_valid(self.base):
    #         query = req.rel_url.query
    #         if query.get('act', None) == 'reg':
    #             username = query.get('username', None)
    #             mail = query.get('mail', None)
    #             password = query.get('password', None)
    #             if username and password and mail:
    #
    #                 try:
    #                     success, user_id, digest = await asyncio.wait_for( self.base.RegisterUser(username, mail, password, self.smtp_used), 5 )
    #
    #                     if digest and self.smtp:
    #
    #                         data = from_file("Site/mail_template.html", **dict(
    #                                             ADDRESS=f"http://{self.config.RoutingEndpoint[0]}:{self.config.RoutingEndpoint[1]}/reg?act=confirm&digest={digest}"
    #                                          )).decode()
    #
    #                         msg = MIMEMultipart('alternative')
    #                         msg['Subject'] = "HaloNetExample"
    #                         msg['From'] = self.config.SMTP.Source.mail
    #                         msg['To'] = mail
    #
    #                         part1 = MIMEText('Hello!', 'plain')
    #                         part2 = MIMEText(data, 'html')
    #                         msg.attach(part1)
    #                         msg.attach(part2)
    #
    #                         self.smtp.sendmail(self.config.SMTP.Source.mail, [mail], msg.as_string())
    #
    #                     return dict(BASE_ACTIVE=is_valid(self.base),
    #                                 DONE_DATA={
    #                                     "success": success,
    #                                     "username": username,
    #                                     "user_id": user_id
    #                                 })
    #                 except asyncio.TimeoutError:
    #                     return dict(BASE_ACTIVE=is_valid(self.base),
    #                                 TIMEOUT=True)
    #         if query.get('act', None) == 'confirm':
    #             digest = query.get('digest')
    #             success, username = await asyncio.wait_for( self.base.ConfirmUser(digest, True), 5)
    #             return dict(BASE_ACTIVE=is_valid(self.base),
    #                         CONFIRM_DATA={
    #                             "success": success,
    #                             "username": username,
    #                         })


        return dict(BASE_ACTIVE=is_valid(self.base), REG_WITH_MAIL=self.smtp_used)

    @route()
    async def dedicateds(self, req: web.Request):

        # servers_count = await self.supervisor.GetDedicatedServersCount()

        servers_info = await self.supervisor.GetDedicatedServersInfo()

        if is_valid(self.base):

            query = req.rel_url.query

            if query.get('act', None) == "stop":
                index = query.get('index', None)
                try:
                    await asyncio.wait_for(self.supervisor.ShutdownDedicatedServer(int(index)), 5)
                except asyncio.TimeoutError:
                    return dict(BASE_ACTIVE=is_valid(self.base),
                                SERVERS=[],
                                TIMEOUT=True)

            if query.get('act', None) == "reset":
                index = query.get('index', None)
                try:
                    await asyncio.wait_for(self.supervisor.ResetDedicatedServer(int(index)), 5)
                except asyncio.TimeoutError:
                    return dict(BASE_ACTIVE=is_valid(self.base),
                                SERVERS=[],
                                TIMEOUT=True)

            servers_info = await self.supervisor.GetDedicatedServersInfo()

            if query.get('act', None) == 'run':
                index = query.get('index', None)
                command = query.get('command', None)
                if index and command:
                    try:
                        await asyncio.wait_for(self.supervisor.ExecuteCommandOnDedicatedServer(int(index), command), 5)
                        return dict(BASE_ACTIVE=is_valid(self.base),
                                    SERVERS=servers_info)
                    except asyncio.TimeoutError:
                        return dict(BASE_ACTIVE=is_valid(self.base),
                                    SERVERS=servers_info,
                                    TIMEOUT=True)

        return dict(BASE_ACTIVE=is_valid(self.base), SERVERS=servers_info)

    @route()
    async def storages(self, req: web.Request):
        if is_valid(self.base):
            query = req.rel_url.query
            act = query.get('act', None)

            if act == 'reload':
                try:
                    await asyncio.wait_for(self.base.ReloadStorages(), 5)
                    return dict(BASE_ACTIVE=is_valid(self.base))
                except asyncio.TimeoutError:
                    return dict(BASE_ACTIVE=is_valid(self.base), TIMEOUT=True)
            if act == 'upload_configs':
                try:

                    await asyncio.wait_for(self.base.UploadStoragesFromConfigs(), 5)
                    return dict(SUCCESS=True, BASE_ACTIVE=is_valid(self.base))
                except asyncio.TimeoutError:
                    return dict(BASE_ACTIVE=is_valid(self.base), TIMEOUT=True)

            if act == 'view':
                try:
                    storage_info = None
                    storage_list = await asyncio.wait_for(self.base.GetStorageNames(), 5)
                    storage_name = query.get('storage', None)
                    if storage_name is not None:
                        storage_typename, storage_data = await asyncio.wait_for(self.base.GetStorageData(storage_name), 5)
                        T = TArray[TypeBase.find_type(storage_typename)]
                        ds = T.deserialize(storage_data)
                        self.interact_storage(ds)
                        storage_info = json.dumps(ds, indent="&nbsp;&nbsp;&nbsp;&nbsp;", separators=(",", ": ")).replace("\n", "<br>").replace("^^", '"')
                    return dict(STORAGE_INFO=storage_info, BASE_ACTIVE=is_valid(self.base), STORAGES=storage_list)
                except asyncio.TimeoutError:
                    return dict(BASE_ACTIVE=is_valid(self.base), TIMEOUT=True)


        return dict(BASE_ACTIVE=is_valid(self.base))

    def parse_asset(self, asset_path):
        true_path = None
        if asset_path.startswith("Blueprint'") and asset_path.endswith("'"):
            true_path = asset_path[10:-1] + "_C"
        elif asset_path.startswith("/Game") and asset_path.endswith("_C"):
            true_path = asset_path

        if true_path is not None:
            return f"""<a href='javascript:;' role=^^button^^ onclick='UnrealEngine4_Goto(^^{true_path}^^)'>{asset_path}</a> """
        else:
            return asset_path

    def interact_storage(self, st_data):
        if isinstance(st_data, list):
            for i, entry in enumerate(st_data):
                if isinstance(entry, (list, dict)):
                    self.interact_storage(entry)
                elif isinstance(entry, set):
                    st_data[i] = list(entry)
                elif isinstance(entry, str):
                    st_data[i] = self.parse_asset(st_data[i])
        elif isinstance(st_data, dict):
            for key, value in st_data.items():
                if isinstance(value, (list, dict)):
                    self.interact_storage(value)
                elif isinstance(value, set):
                    st_data[key] = list(value)
                elif isinstance(value, str):
                    st_data[key] = self.parse_asset(st_data[key])


    @route()
    async def docs(self, req: web.Request):
        query = req.rel_url.query
        generated_info = deepcopy(ConfigurationGenerator().generated_info)


        entities = dict()

        types = deepcopy(ConfigurationGenerator().generated_types)

        for entity_name, entity_info in generated_info.items():
            if entity_name not in entities.keys():
                entities[entity_name] = dict(context_data=dict())

            for context_name, context_data in entity_info.items():
                if context_name not in entities[entity_name]['context_data']:
                    entities[entity_name]['context_data'][context_name] = context_data

            additional_entity_info = dict()
            additional_entity_info['Doc'] = None

            if 'base' in entity_info:
                additional_entity_info['Doc'] = entity_info['base']['Doc']
            else:
                additional_entity_info['Doc'] = list(entity_info.values())[0]['Doc']

            additional_entity_info['ContextName'] = None
            if len(entity_info) == 1 and list(entity_info.values())[0].get("IsApplication", None):
                additional_entity_info['ContextName'] = list(entity_info.keys())[0]

            additional_entity_info['IsApp'] = len(entity_info) == 1 and list(entity_info.values())[0].get("IsApplication", None)
            additional_entity_info['IsExposedApp'] = len(entity_info) == 1 and list(entity_info.values())[0].get("Exposed", None)

            entities[entity_name].update({'additional': deepcopy(additional_entity_info)})

        if query.get('cat', None) == 'entities':
            return dict(ENTITIES=entities, BACK=True)

        elif query.get('cat', None) == 'types':
            return dict(TYPES=types, BACK=True)

        elif query.get('act', None) == 'pycharm_goto':
            PyCharm_go_to(query.get('filename', ""), query.get('linenumber', ""))
            return dict()

        elif query.get('act', None) == 'ue4_goto':
            UnrealEngine4_go_to(query.get('asset', ""))
            return dict()

        entity = query.get('entity', None)
        if entity is not None and entity in generated_info:
            return dict(ENTITY=entities[entity], ENTITY_NAME=entity, BACK=True)

        return dict(BROWSE_ALL=True)

    @route()
    async def debug(self, req: web.Request):
        if is_valid(self.base):
            query = req.rel_url.query
            exec = query.get("exec", None)
            result = ""
            if exec is not None:
                result = await self.base.ExecuteCode(exec)

            entity_info = ""
            query = req.rel_url.query
            if query.get('act', None) == "view":
                entity_id = query.get('id', None)

                action_name = query.get('action', None)
                if action_name:
                    await self.base.CallDisplayAction(entity_id, action_name)

                if entity_id is not None:
                    entity_info = await self.base.GetEntityViewInfo(entity_id)

            debug_info = await self.base.GetDebugInfo()
            return dict(BASE_ACTIVE=is_valid(self.base),
                        ENTITIES=debug_info,
                        RESULT=result,
                        VIEW_STRUCTURE=entity_info)
        return dict(BASE_ACTIVE=is_valid(self.base))

    @route()
    async def visor(self, req: web.Request):
        if is_valid(self.supervisor):
            query = req.rel_url.query
            if query.get('act', None) == "exec":
                cmd = query.get('cmd', None)
                id = query.get('id', None)
                if cmd and id:
                    self.base.ExecuteMatchConsoleCommand(id, cmd)
                else:
                    WARN_MSG("Wrong query for 'exec'")

            if query.get('act', None) == "test":
                try:
                    await self.supervisor.minitest()
                except Exception:
                    print('test2')

            states = await self.supervisor.GetBaseAppsGenericStatesInfo()
            online: TArray[FOnlineStatisticEntry] = [] # await self.base.RequestOnline()

            new_online = list()
            last_online = None
            for o in online:
                if last_online is None:
                    last_online = o
                    new_online.append(last_online)

                if o['Date'] - last_online['Date'] > timedelta(minutes=15):
                    new_online.append(o)
                    last_online = o
                    continue

                if o['OnlineCount'] > last_online['OnlineCount']:
                    last_online['OnlineCount'] = o['OnlineCount']

                if o['InGameCount'] > last_online['InGameCount']:
                    last_online['InGameCount'] = o['InGameCount']

            return dict(INFO=states, ONLINE=new_online)

        return dict()