import asyncio
from aiohttp import web

import HaloNet
from Config import SupervisorWebConfig
from Core import INFO_MSG
from Core.Globals import Globals
from Core.SiteUtils import web_run_app, route
from Core.Utils import runnable

from Supervisor import Supervisor


@runnable
class SupervisorWeb(Supervisor):
    config: SupervisorWebConfig

    async def start(self):
        await super().start()

        self.web_app = web.Application(loop=asyncio.get_event_loop())

        if hasattr(self, '__routes__'):
            for r in self.__routes__:
                self.web_app.router.add_route(r['method_type'], r['path'], getattr(self, r['method']))

        self.web_app.router.add_static('/static/', f"{Globals.workspace}/Services/Site/static",
                                       show_index=True,
                                       follow_symlinks=True)

        self.srv, self.srv_handler = await web_run_app(self.web_app,
                                                       host=self.config.RoutingEndpoint[0],
                                                       port=self.config.RoutingEndpoint[1],
                                                       print=INFO_MSG)

    @route(route_path='/')
    async def supervisor(self, req: web.Request):
        query = req.rel_url.query
        act = query.get('act', None)
        if act:
            if act == 'wakeup':
                daemon_id = query.get('daemon_id')
                app = query.get('app')
                await self.keep_lifetime_service(app)
            if act == 'stop':
                app = query.get('app')
                index = int(query.get('index'))
                if len(self.services[app]) > index:
                    srv = self.services[app].pop(index)
                    srv.Terminate()
        return dict(DAEMONS=self.daemons, SERVICES=self.services)