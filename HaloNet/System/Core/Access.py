import random
from Core.Common.Helpers import Singleton

gen_code_length = 25
gen_code_symbols = "QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm1234567890"


class AccessLevel:
    Unauthorized = 0
    User = 1
    Internal = 2


class Access(metaclass=Singleton):
    def __init__(self):
        self.tokens = dict()

    def generate(self, access_rights):
        access_token = "".join(random.choice(gen_code_symbols) for i in range(gen_code_length))
        if access_token in self.tokens:
            access_token = self.generate(access_rights)
        else:
            self.register_access(access_token, access_rights)
        return access_token

    def register_access(self, access_token, access_rights):
        self.tokens[access_token] = access_rights
        return access_token

    def get_access_level(self, access_token):
        return self.tokens.get(access_token, AccessLevel.Unauthorized)

    def has_access(self, access_token, access_rights):
        access_level = self.get_access_level(access_token)
        return access_level >= access_rights


