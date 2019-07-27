import sys

# import psycopg2

from Core import ERROR_MSG
from Core import Log
from Core.AsyncObj import AsyncObj


from aiopg.sa import create_engine

from Core.Common.Colors import Color

DB_INFO = Log("DB INFO", None, Color.Blue)


class ConnectionContextManager(object):
    """ Менеджер соединения """
    def __init__(self, engine):
        self.conn = None
        self.engine = engine

    async def __aexit__(self, exc_type, exc, tb):
        try:
            self.engine.release(self.conn)
            # await self.conn.close()  # todo: releasing conn from engine is closing them for now?
        finally:
            self.conn = None
            self.engine = None

    async def __aenter__(self):
        if self.engine:
            self.conn = await self.engine.acquire()
            return self.conn



class DatabaseDriver(AsyncObj):
    """ Драйвер базы данных """
    async def __ainit__(self, host, port, database, user, password):
        await super().__ainit__()
        try:
            DB_INFO(f"Login to database {host}:{port}: {database} with user {user}")
            self.engine = await create_engine(user=user, database=database, host=host, password=password, port=port)
        except psycopg2.OperationalError:
            ERROR_MSG("Operational error, probably database engine settings is wrong. Check your Config")
            sys.exit(0)
        DB_INFO("Connected to DB '%s' by user '%s' at '%s'" % (database, user, host))

    @property
    def connection(self):
        """ Получение нового коннекшина к БД """
        return ConnectionContextManager(self.engine)

    async def exec_raw(self, *args, **kwargs):
        """ Выполнить сырую команду
            @param args, kwargs: параметры передаваемые в SQL-экзекьютор
            @return открытый результат запроса
        """
        try:
            async with self.connection as conn:
                return await conn.execute(*args, **kwargs)
        except psycopg2.ProgrammingError as exc:
            ERROR_MSG("Unable to perform query: %s, \n%s" % (exc, args), depth=1)
            # from traceback import print_exc
            # print_exc()
            raise