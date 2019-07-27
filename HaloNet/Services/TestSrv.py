import HaloNet

from Core import INFO_MSG
from Core.Declarators.Specs import *
from Core.Declarators.rmi import rmi
from Core.LocalDatatypes import *
from Core.Service import Service
from Core.Utils import runnable, make_default_service_mailbox
from Session import Session



@runnable
class TestSrv(Service):

    async def start(self):
        from LoginApp import LoginApp
        # mb = await self.make_mailbox('sv', "Supervisor", )
        
        self.loginapp: LoginApp = await LoginApp.make_mailbox("LoginApp", "LoginApp", ("0.0.0.0", 9090))
        mb, token = await self.loginapp.login("User0", "123")
        print(mb, token)