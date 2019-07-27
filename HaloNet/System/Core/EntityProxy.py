from Core.AsyncObj import AsyncObj
from Core.Globals import Globals
from Core.Type import MailboxProxyDatatype


class EntityProxy(MailboxProxyDatatype):
    @property
    def service(self):
        return Globals.this_service

    async def create_client_connection(self, endpoint, on_lost=None):
        raise NotImplementedError("This function can be called only in services!")

    def get_class_name(cls):
        raise NotImplementedError("Should be implemented in Entity and Mailbox classes")

    def get_endpoint(self):
        raise NotImplementedError("Should be implemented in Entity and Mailbox classes")

    def get_id(self):
        raise NotImplementedError("Should be implemented in Entity and Mailbox classes")

    def get_context(self):
        raise NotImplementedError("Should be implemented in Entity and Mailbox classes")

    # def add_lost_callback(self, cb):
    #     raise NotImplementedError("Should be implemented only in Mailbox class")

    # def serialize(self):
    #     sr = BinarySerialization()
    #     sr << self.get_endpoint()[0]
    #     sr << self.get_endpoint()[1]
    #     sr << self.get_id()
    #     sr << self.get_context()
    #     sr << self.get_class_name()
    #     return sr.get_archive()
    #
    # @classmethod
    # def deserialize(cls, serialized_value):
    #     srp = BinarySerialization(serialized_value).proxy()
    #     endpoint = [None, None]
    #     endpoint[0] = srp >> str
    #     endpoint[1] = srp >> int
    #     id          = srp >> int
    #     context     = srp >> str
    #     cls_name    = srp >> str
    #
    #     symbol = SymbolsRegistry().get_by_context(context, cls_name)
    #     return Mailbox(symbol, endpoint, id, context)