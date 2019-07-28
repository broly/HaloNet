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
