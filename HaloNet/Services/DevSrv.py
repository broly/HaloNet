import asyncio
from time import time

import HaloNet
from Core.Framework import *
from Core.Logging import EMPHASIS

if False: from Supervisor import Supervisor

@runnable
class DevSrv(Service):
    async def start(self):
        t = time()
        await self.async_wakeup_service_locally_by_name("Daemon", arguments={'test': 1})
        print('test')
        sv: 'Supervisor' = await self.async_wakeup_service_locally_by_name("SupervisorWeb")
        INFO_MSG("All services started in %.3f secs" % round(time() - t, 3))
        # from BaseApp import BaseApp
        # base: BaseApp = await sv.Wakeup("BaseApp", {})
        # await sv.Wakeup("Site", {})
        # ue4 = await sv.Wakeup("UE4App", {'port': "7776"})
        # print('lolz')
        # from Core.TCP.TestProtocolClient import create_connection
        #
        # endp = base.client_connection.endpoint
        # # endp = endp[0], endp[1] + (i+1)
        #
        # conns = list()
        #
        # for i in range(600):
        #     _, conn = await create_connection(endp)
        #     conn.transport.pause_reading()
        #     conns.append(conn)
        # await asyncio.sleep(2)
        # INFO_MSG("Created connections")
        # for i, conn in enumerate(conns):
        #     INFO_MSG("resuming %i" % i)
        #     conn.transport.resume_reading()
        # await asyncio.sleep(10)
        # INFO_MSG("Rs")
        # conn.transport.resume_reading()
