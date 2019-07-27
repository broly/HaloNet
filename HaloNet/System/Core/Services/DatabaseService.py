import asyncio
import json
import random
from datetime import datetime

# import psycopg2

import bcrypt

from Core import INFO_MSG, ERROR_MSG
from Core import WARN_MSG
from Core.CommandLine import CommandLine
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator
from Core.ConfigSystem.AppsConfig import DBAppConfigBase
from Core.ConfigSystem.Bases import ConfigGlobals
from Core.DatabaseDriver import DatabaseDriver
from Core.Declarators.Specs import Persistent
from Core.Declarators.rmi import rmi
from Core.BaseEntity import BaseEntity
from Core.LocalDatatypes import int32, FString, Bool, uint8, FBytes, FPropertyInfo, ELoginResult
from Core.intrinsic.Serialization import BinarySerialization
from Core.Service import Service
from Core.Type import TArray, TMap, TypeBase, EnumBase, storage_list, StructBase, reconstruct, UJsonRaw, FDateTime
from jinja2 import Template
from asyncio import Queue

from Core.Common.JSONHaloNetEncoder import JSONHaloNetEncoder

from Core.Common import JSONHaloNetEncoder as JSONEncoderModule
JSONEncoderModule.c_make_encoder = None

def pg_str(v):

    if isinstance(v, EnumBase):
        return ("'%s'" % v).replace('"', '')
    elif isinstance(v, Bool):
        return str(bool(v))
    elif isinstance(v, str):
        return "'%s'" % v.replace("'", "''")
    elif isinstance(v, dict):
        return "'%s'::jsonb" % str(json.dumps(v, cls=JSONHaloNetEncoder)).replace("'", "''")
    elif isinstance(v, list):
        return "'%s'::jsonb" % str(json.dumps(v, cls=JSONHaloNetEncoder)).replace("'", "''")
    elif isinstance(v, set):
        return pg_str(sorted(list(v)))
    elif isinstance(v, int):
        return str(v)
    elif v is None:
        return "null"
    elif isinstance(v, datetime):
        return f"'{str(v)}'"
    return v

def get_rows(rows, num):
    return [rows[i] for i in range(num)]


class DatabaseService(Service):
    config: DBAppConfigBase

    async def start(self):
        self.types = list()
        config = self.get_db_config()
        self.driver: DatabaseDriver = await DatabaseDriver(config.DBConfig.Host,
                                                           config.DBConfig.Port,
                                                           config.DBConfig.Database,
                                                           config.DBConfig.User,
                                                           config.DBConfig.Password)
        await self.refresh_database()
        self.transactions_queue = Queue()
        asyncio.Task(self.transactions_worker())
        self.types = await self.get_types()

    async def refresh_database(self):
        """ Обновляет основную структуру если она нарушена """
        try:
            await self.driver.exec_raw("""  CREATE TABLE IF NOT EXISTS public.users  --- список пользователей
                                            (
                                                id SERIAL PRIMARY KEY NOT NULL,    -- ID пользователя
                                                unique_name VARCHAR(255) NOT NULL,    -- имя пользователя
                                                nickname VARCHAR(255),
                                                mail VARCHAR(255) NOT NULL,
                                                hash VARCHAR(255),                -- пароль
                                                salt VARCHAR(255),
                                                auth INT2,                         -- аутентификация
                                                account_dbid SERIAL,               -- DB-идентификатор сущности-аккаунта 
                                                register_date TIMESTAMP,
                                                confirmed BOOLEAN DEFAULT FALSE
                                            );
                                            CREATE UNIQUE INDEX IF NOT EXISTS users_id_uindex ON public.users (id);
                                            
                                            CREATE INDEX IF NOT EXISTS idx_users_name ON public.users (unique_name);
                                            
                                            CREATE TABLE IF NOT EXISTS public.users_uncofirmed
                                            (
                                              id SERIAL PRIMARY KEY NOT NULL,
                                              digest VARCHAR(255)
                                            );
    
                                            CREATE TABLE IF NOT EXISTS public.entities  --- список сущностей (DB-идентификатор - имя класса)
                                            (
                                                db_id SERIAL PRIMARY KEY NOT NULL,    -- DB-идентификатор сущности
                                                class_name VARCHAR(255)               -- имя класс
                                            );
                                            CREATE UNIQUE INDEX IF NOT EXISTS entities_db_id_uindex ON public.entities (db_id);
    
                                            CREATE TABLE IF NOT EXISTS public.classes  --- имформация о классах в базе данных
                                            (
                                                class_name VARCHAR(255) PRIMARY KEY NOT NULL,  -- имя класса
                                                class_data JSONB                               -- данные класса
                                            );
                                            CREATE UNIQUE INDEX IF NOT EXISTS classes_class_name_uindex ON public.classes (class_name);
                                            
                                            CREATE TABLE IF NOT EXISTS public.types  --- имформация о типах
                                            (
                                                type_name VARCHAR(255) PRIMARY KEY NOT NULL,  -- имя типа
                                                type_data JSONB                               -- данные типа
                                            );
                                            CREATE UNIQUE INDEX IF NOT EXISTS types_type_name_uindex ON public.types (type_name);                 
                                            CREATE TABLE IF NOT EXISTS ccu
                                            (
                                                app_name VARCHAR(255),
                                                dump_time TIMESTAMP,
                                                online_count INTEGER,
                                                in_game_count INTEGER
                                            );                     
                                            --- CREATE TABLE IF NOT EXISTS public.storages  --- имформация о хранилищах в базе данных
                                            --- (
                                            ---     storage_name VARCHAR(255) PRIMARY KEY NOT NULL,  -- имя хранилища
                                            ---     storage_data JSONB                               -- данные хранилища
                                            --- );
                                            --- CREATE UNIQUE INDEX IF NOT EXISTS storages_class_name_uindex ON public.storages (storage_name);
                                            CREATE TABLE IF NOT EXISTS public.statistics
                                            (
                                                id SERIAL PRIMARY KEY NOT NULL,
                                                user_id INTEGER,    -- ID пользователя
                                                username VARCHAR(255),
                                                score INTEGER DEFAULT 0,
                                                game_mode INTEGER,
                                                deaths INTEGER DEFAULT 0,
                                                wins INTEGER DEFAULT 0,
                                                CONSTRAINT unique_entry UNIQUE (username, game_mode)
                                            );               
                                            
                                       """)
        except psycopg2.ProgrammingError as e:
            WARN_MSG(f"Unable to refresh database due to errors: {e}")

    async def empty_database(self):
        INFO_MSG("Clear database")
        await self.driver.exec_raw("""  DROP TABLE IF EXISTS public.users;
                                        DROP TABLE IF EXISTS public.entities;
                                        DROP TABLE IF EXISTS public.classes;
                                        DROP TABLE IF EXISTS public.users_uncofirmed;
                                        DROP TABLE IF EXISTS public.types;
                                        DROP TABLE IF EXISTS public.statistics;
                                        --- DROP TABLE IF EXISTS public.storages;
                                   """)
        # await self.refresh_database()


    def get_db_config(self):
        return self.config

    @rmi(access=2)
    async def GetUserIsExists(self, username: FString) -> Bool:
        """ Возвращает правду если пользователь с заданным именем существует
            @param username
            @return
        """
        res = await self.driver.exec_raw(""" SELECT * 
                                             FROM public.users 
                                             WHERE unique_name=%s; """, username)
        exists = res.rowcount > 0
        res.close()
        return exists

    @rmi(access=2)
    async def RegisterUser(self, username: FString, password: FString, reg_with_mail: Bool, mail: FString, authority: int32, account_dbid: int32, register_date: FDateTime) -> (Bool, int32, FString):
        exists = await self.GetUserIsExists(username)

        salt = bcrypt.gensalt()
        final_hash = bcrypt.hashpw(password.encode(), salt)

        id = 0
        digest = ""
        if not exists:
            id_row = await self.driver.exec_raw(""" INSERT INTO public.users (unique_name, nickname, mail, hash, salt, auth, account_dbid, register_date, confirmed) 
                                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                                                    RETURNING id; 
                                                """, username, username, mail, final_hash.decode(), salt.decode(), authority, account_dbid, register_date, not reg_with_mail)
            for id_proxy in id_row:
                id = id_proxy[0]

            if reg_with_mail:
                digest_symbols = "QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm1234567890"
                digest = "".join(random.choice(digest_symbols) for i in range(25))
                await self.driver.exec_raw(""" INSERT INTO public.users_uncofirmed (id, digest) 
                                               VALUES (%s, %s);""", id, digest)

        return exists, id, digest

    @rmi(access=2)
    async def RegisterUserWithoutPassword(self,
                                          unique_name: FString,
                                          nickname: FString,
                                          authority: int32,
                                          account_dbid: int32,
                                          register_date: FDateTime) -> (Bool, int32):
        exists = await self.GetUserIsExists(unique_name)

        id = 0
        if not exists:
            id_row = await self.driver.exec_raw(""" INSERT INTO public.users (unique_name, nickname, mail, hash, salt, auth, account_dbid, register_date, confirmed) 
                                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                                                    RETURNING id; 
                                                   """, unique_name, nickname, "", "", "", authority, account_dbid, register_date, True)
            for id_proxy in id_row:
                id = id_proxy[0]


        return exists, id

    @rmi(access=2)
    async def ConfirmUser(self, digest: FString) -> (Bool, FString):
        unconfirmeds = await self.driver.exec_raw(""" SELECT * FROM public.users_uncofirmed WHERE digest=%s; """, digest)

        for unconfirmed_user in unconfirmeds:
            id, digest = get_rows(unconfirmed_user, 2)

            users = await self.driver.exec_raw(""" SELECT unique_name FROM public.users WHERE id=%s; """, id)

            for user in users:
                await self.driver.exec_raw(""" UPDATE public.users 
                                               SET confirmed = TRUE 
                                               WHERE id=%s; 
                                               
                                               DELETE FROM users_uncofirmed WHERE id=%s; 
                                           """, id, id)
                username = user[0]
                INFO_MSG(f"User {username} confirmed")
                return True, username
            else:
                WARN_MSG(f"No user with id={id} and digest={digest}")
        return False, ""


    @rmi(access=2)
    async def FindUserForLogin(self, username: FString, password: FString) -> (ELoginResult, int32, uint8, int32, FDateTime):
        """
        Поиск пользователя для логина
        @param username: имя
        @param password: хэш пароля
        @return: успех, ИД, доступ, ДБИД
        """
        res = await self.driver.exec_raw(""" SELECT * 
                                             FROM public.users 
                                             WHERE LOWER(unique_name)=LOWER(%s); 
                                         """, username)

        for row in res:
            id, _, __, mail, pass_hash, salt, access, dbid, reg_time, confirmed = get_rows(row, 10)

            # final_hash = bcrypt.hashpw(password.encode(), salt.encode()).decode()
            # if pass_hash == final_hash:
            #     if not confirmed:
            #         WARN_MSG(f"User {username} is unconfirmed")
            #         return ELoginResult.Unconfirmed, 0, 0, 0, FDateTime(0, 0, 0)
            #
            #     res.close()
            return ELoginResult.Success, id, access, dbid, reg_time

        WARN_MSG(f"User {username} not found or wrong password")

        return ELoginResult.NotExists, 0, 0, 0, FDateTime.invalid()

    @rmi(access=2)
    async def FindUserForLoginWithoutPassword(self, username: FString) -> (ELoginResult, int32, uint8, int32, FDateTime):
        """
        Поиск пользователя для логина
        @param username: имя
        @param password: хэш пароля
        @return: успех, ИД, доступ, ДБИД
        """
        res = await self.driver.exec_raw(""" SELECT id, auth, account_dbid, register_date, confirmed 
                                             FROM public.users 
                                             WHERE LOWER(unique_name)=LOWER(%s); 
                                         """, username)

        for row in res:
            id, access, dbid, reg_time, confirmed = get_rows(row, 5)

            return ELoginResult.Success, id, access, dbid, reg_time

        WARN_MSG(f"User {username} not found or wrong password")

        return ELoginResult.NotExists, 0, 0, 0, FDateTime.invalid()

    @rmi(access=2)
    async def CreateClassTable(self, class_name: FString, fields: TMap[FString, FString]):
        """
        Создать таблицу класса
        @param class_name: имя класса
        @param fields: поля {имя: тип}
        """
        INFO_MSG(f"Create class table {class_name}, {fields}")
        # await self.driver.exec_raw(""" DROP TABLE IF EXISTS public.Class_{0}; """.format(class_name))

        fields_substitute = str()
        for field_name, field_typedata in fields.items():
            T = self.find_type(field_typedata)
            pg_spec = T.pg_spec if T else 'INTEGER'
            default = ConfigurationGenerator().generated_entities_info.get_by_name(class_name).get_property('base', field_name).default

            fields_substitute += ', "%s" %s DEFAULT %s' % (field_name, pg_spec, pg_str(default))

        self.username = None

        current_data = await self.driver.exec_raw("""  SELECT class_data 
                                                       FROM public.classes 
                                                       WHERE class_name='{0}';
                                                  """.format(class_name))
        for c in current_data:
            r = c['class_data']
            deleted_columns = list()
            new_columns = list()
            changed_columns = list()
            alter_strings = list()
            for column_name, column_type in fields.items():
                T = self.find_type(column_type)
                pg_spec = T.pg_spec if T else 'INTEGER'
                default = ConfigurationGenerator().generated_entities_info.get_by_name(class_name).get_property('base', column_name).default
                default = pg_str(default)

                if column_name not in r:
                    new_columns.append((column_name, column_type))
                    alter_strings.append("ADD COLUMN {0} {1} DEFAULT {2}".format(column_name, pg_spec, default))
                elif column_name in r and r[column_name] != column_type:
                    changed_columns.append((column_name, r[column_name], column_type))
                    alter_strings.append("ALTER COLUMN {0} TYPE {1}, ALTER COLUMN {0} SET DEFAULT {2}".format(column_name, pg_spec, default))

            for column_name, column_type in r.items():
                if column_name not in fields:
                    alter_strings.append("DROP COLUMN {0}".format(column_name))
                    deleted_columns.append(column_name)

            if deleted_columns or changed_columns or new_columns:
                try:
                    await self.driver.exec_raw("""  ALTER TABLE IF EXISTS "class_{0}" {1};
                                               """.format(class_name,
                                                          ", ".join(alter_strings)))
                except Exception as e:
                    ERROR_MSG("An exception occurred, returning...", e)
                    return

                if deleted_columns:
                    WARN_MSG("Deleted columns in %s %i: [%s]" % (class_name, len(deleted_columns), ", ".join(deleted_columns)))

                if changed_columns:
                    WARN_MSG("Changed columns in %s %i: [%s]" % (class_name, len(changed_columns), ", ".join(["%s from %s to %s" % c for c in changed_columns])))

                if new_columns:
                    INFO_MSG("New columns in %s %i: [%s]" % (class_name, len(new_columns), ", ".join("%s %s" % c for c in new_columns)))
        INFO_MSG(class_name, fields, fields_substitute)
        await self.driver.exec_raw("""  INSERT INTO public.classes (class_name, class_data) VALUES ('{0}', '{1}')
                                        ON CONFLICT (class_name) DO
                                        UPDATE SET class_data = '{1}';
                                   """.format(class_name, json.dumps(fields)))

        await self.driver.exec_raw("""  CREATE TABLE IF NOT EXISTS "class_{0}"
                                        (
                                            rec_id SERIAL PRIMARY KEY NOT NULL,
                                            db_id SERIAL {1}
                                        );
                                        CREATE UNIQUE INDEX IF NOT EXISTS "class_{0}_rec_id_uindex" ON "class_{0}" (rec_id);
                                   """.format(class_name, fields_substitute))

        INFO_MSG(fields)
        # await self.driver.exec_raw("""  ALTER TABLE IF EXISTS public.class_session
        #                                     ADD COLUMN "qwe" int, ADD COLUMN "das" int;
        #                            """)

    @rmi(access=2)
    async def CreateDefaultEntity(self, entity_class: FString) -> int32:
        """
        Создать дефолтную сущность
        @param entity_class: имя класса
        @return: ДБИД сущности
        """
        async with self.driver.connection as conn:
            db_id_row = await conn.execute(""" INSERT INTO public.entities (class_name) 
                                               VALUES ('%s') 
                                               RETURNING db_id; """ % (entity_class))
            for db_id_proxy in db_id_row:
                db_id = db_id_proxy[0]
                await conn.execute(""" INSERT INTO "class_{0}" (db_id) 
                                       VALUES ({1});""".format(entity_class, db_id))
                return db_id

    @rmi(access=2)
    async def GetEntityClassName(self, entity_dbid: int32) -> FString:
        """
        Получить имя класса по ДБИД 
        @param entity_dbid: ДБИД сущности
        @return: имя класса
        """
        class_name_row = await self.driver.exec_raw(""" SELECT class_name 
                                                        FROM public.entities 
                                                        WHERE db_id=%s """, entity_dbid)
        for class_name_proxy in class_name_row:
            class_name = class_name_proxy[0]
            return class_name
        return "None"

    @rmi(access=2)
    async def GetEntityData(self, entity_dbid: int32, entity_class: FString) -> FBytes:
        """
        Получение бинарных данных о сущности
        @param entity_dbid: ДБИД сущности
        @param entity_class: класс сущности
        @return: сериализованные байты (по классу)
        """
        properties = ConfigurationGenerator().generated_entities_info.get_by_name(entity_class).get_properties('base', only_persistent=True)

        props_templ = ", ".join([f'"{key}"' for key in properties.keys()])

        res = await self.driver.exec_raw(""" SELECT {0} 
                                             FROM "class_{1}"
                                             WHERE db_id={2}; """.format(props_templ, entity_class, entity_dbid))
        sr = BinarySerialization()
        for data in res:
            values = tuple(data.values())
            for index, (prop_name, prop_data) in enumerate(properties.items()):
                print(prop_name, prop_data)
                T = self.find_type(prop_data.typename, BaseEntity)
                value = values[index]
                value = T.pg_null(value)
                sr << T.serializable_value(value).serialize()
            return sr.get_archive()


    @rmi(access=2)
    async def UpdateEntityVariable(self, entity_dbid: int32, entity_class: FString, variable_name: FString, variable_type: FString, variable_data: FBytes):
        """
        Обновить значение переменной у сущности
        @param entity_dbid: ДБИД сущности
        @param entity_class: класс сущности
        @param variable_name: имя переменной
        @param variable_type: тип переменной
        @param variable_data: значение переменной
        """
        T = TypeBase.find_type(variable_type)
        ds = T.deserialize(variable_data)
        await self.driver.exec_raw(""" UPDATE "class_{0}"
                                       SET "{1}"={2} 
                                       WHERE db_id={3}; """.format(entity_class, variable_name, pg_str(ds), entity_dbid))

    @rmi(access=2)
    async def UpdateVariablesTransactionally(self, old_variables: TArray[FPropertyInfo], new_variables: TArray[FPropertyInfo]) -> Bool:
        """
        Обновление переменных транзакционно
        @param old_variables: старые значения переменных (для проверки)
        @param new_variables: новые значения переменных (для изменения)
        @return: успех транзакции
        """
        olds = list()
        news = list()
        for var in old_variables:
            entity_class = var["EntityClass"]
            variable_name = var["PropertyName"]
            variable_data = var["SerializedValue"]
            variable_type = var["PropertyTypeName"]
            entity_dbid = var["EntityDBID"]
            T = TypeBase.find_type(variable_type)
            ds = T.deserialize(variable_data)

            olds.append((entity_class, variable_name, pg_str(ds), entity_dbid))

        for var in new_variables:
            entity_class = var["EntityClass"]
            variable_name = var["PropertyName"]
            variable_data = var["SerializedValue"]
            variable_type = var["PropertyTypeName"]
            entity_dbid = var["EntityDBID"]
            T = TypeBase.find_type(variable_type)
            ds = T.deserialize(variable_data)

            news.append((entity_class, variable_name, pg_str(ds), entity_dbid))

        future = asyncio.Future()
        await self.transactions_queue.put((future, olds, news))

        future_res = await future
        return future_res

    async def UpdateVariablesTransactionally_cycle(self, future, olds, news):

        async with self.driver.connection as conn:
            Templ = Template(""" 
                    CREATE OR REPLACE FUNCTION public.last_transaction_function()
                    RETURNS BOOLEAN AS
                    $$
                    
                    BEGIN
                        {% for entity_class, variable_name, data, entity_dbid in old_variables %}
                        IF (SELECT "{{variable_name}}" FROM "class_{{entity_class}}" WHERE db_id={{entity_dbid}} FOR UPDATE LIMIT 1) <> {{data}} THEN
                          RETURN FALSE;
                        END IF;
                        {% endfor %}
                        
                        {% for entity_class, variable_name, data, entity_dbid in new_variables -%}
                        UPDATE "class_{{entity_class}}" SET "{{variable_name}}"={{data}} WHERE db_id={{entity_dbid}};
                        {% endfor %}
                        RETURN TRUE;
                    END
                    $$
                    LANGUAGE 'plpgsql'
                    VOLATILE
                    CALLED ON NULL INPUT
                    SECURITY INVOKER;
                    START TRANSACTION READ WRITE;
                        SELECT * FROM public.last_transaction_function();
            """).render(old_variables=olds, new_variables=news)
            try:
                res = await conn.execute(Templ)
            except psycopg2.ProgrammingError:
                ERROR_MSG("Unable to perform query %s" % Templ)
                raise
            await conn.execute(""" COMMIT; """)

            for r in res:
                future.set_result(r[0])

    async def transactions_worker(self):
        while True:
            await asyncio.sleep(0.1)
            while not self.transactions_queue.empty():
                future, olds, news = await self.transactions_queue.get()
                await self.UpdateVariablesTransactionally_cycle(future, olds, news)


    @rmi(access=2)
    async def Test(self, i: int32, s: FString):
        INFO_MSG("! %i : %s" % (i, s))

    @rmi(access=2)
    async def GetIsEntityValid(self, entity_dbid: int32, entity_class: FString):
        """
        Проверка на валидность сущности
        @param entity_dbid: ДБИД сущности
        @param entity_class: класс сущности
        @warning не используется
        @return: 
        """
        await self.driver.exec_raw(""" SELECT * 
                                       FROM entities 
                                       WHERE db_id=%s;
                                   """, entity_dbid)

    @rmi(access=2)
    async def CreateStorage(self, storage_name: FString, storage_type_name: FString):
        """
        Создание нового хранилища
        @param storage_name: имя хранилища
        @param storage_type_name: имя типа по которому создаётся хранилище
        """
        storage_type = self.find_type(storage_type_name)

        fields_substitute = list()
        for field_name, field_type in storage_type.fields:
            pg_spec = field_type.pg_spec if field_type else 'INTEGER'
            default = storage_type.defaults.get(field_name, field_type())

            fields_substitute.append('"%s" %s DEFAULT %s' % (field_name, pg_spec, pg_str(default)))
        await self.driver.exec_raw(""" CREATE TABLE IF NOT EXISTS storage_{0} ({1}); """.format(storage_name, ", ".join(fields_substitute)))

    @rmi(access=2)
    async def GetStorageData(self, storage_class_name: FString, storage_type_name: FString) -> FBytes:
        """
        Получение данных из хранилища
        @param storage_class_name: имя класса хранилища
        @param storage_type_name: имя типа хранилища
        @return: 
        """
        result = await self.driver.exec_raw(""" SELECT * 
                                                FROM storage_{0}; 
                                            """.format(storage_class_name))

        result_list = list()

        for r in result:
            entry = dict()
            for name, value in r.items():
                entry[name] = value
            result_list.append(entry)
        storage_type = self.find_type(storage_type_name)

        res = TArray[storage_type](result_list)
        return res.serialize()

    @rmi()
    async def UploadStorages(self):
        """ Загрузить хранилища """
        for storage in storage_list:
            with open("Configs/storage_%s.json" % storage.name.lower()) as f:
                try:
                    d = json.loads(f.read())
                    queries = list()
                    for entry in d:
                        s = [str(pg_str(v)) for v in entry.values()]
                        queries.append("""INSERT INTO "storage_{0}" ({1}) VALUES ({2});
                                       """.format(storage.name.lower(), ", ".join([f'"{key}"' for key in entry.keys()]), ", ".join([str(pg_str(v)) for v in entry.values()])) )
                    await self.driver.exec_raw(""" DELETE FROM storage_{0}; 
                                                   {1}
                                               """.format(storage.name.lower(), "\n".join(queries)))
                except json.JSONDecodeError:
                    INFO_MSG("Storage:%s",storage)

    @rmi()
    async def Synchronize(self):
        """ Синхронизировать ( типы ) """
        for T in TypeBase.all_types['types'].values():
            if issubclass(T, StructBase) and T is not StructBase:
                d = dict()
                for column_name, column_type in T.fields:
                    d[column_name] = column_type.__name__
                await self.driver.exec_raw("""  INSERT INTO public.types (type_name, type_data) VALUES ('{0}', '{1}')
                                                ON CONFLICT (type_name) DO
                                                UPDATE SET type_data = '{1}'::jsonb;""".format(T.__name__, json.dumps(d)))
        self.types = await self.get_types()

        classes = dict()
        result = await self.driver.exec_raw("""  SELECT * FROM classes; """)
        for r in result:
            class_name, data = r[0], r[1]
            classes[class_name] = data

        reconstructed_classes_info = dict()
        result = await self.driver.exec_raw("""  SELECT * FROM entities; """)

        for r in result:
            dbid, class_name = r[0], r[1]
            res = await self.driver.exec_raw("""  SELECT * FROM "class_{class_name}" WHERE db_id = {dbid} 
                                             """.format(class_name=class_name, dbid=dbid))
            class_data = classes[class_name]
            dictionary = dict()
            for r in res:
                for field_name, field_type in class_data.items():
                    for key, value in r.items():
                        T = TypeBase.find_type(field_type)
                        if T is not None:
                            if field_name == key:
                                dictionary[field_name] = reconstruct(T, value)
            reconstructed_classes_info[(dbid, class_name)] = dictionary

        for (dbid, class_name), class_info in reconstructed_classes_info.items():
            lst = list()
            for key, value in class_info.items():
                lst.append('"%s" = %s' % (key, pg_str(value)))
            update_str = ", ".join(lst)
            if lst:
                await self.driver.exec_raw("""  UPDATE "class_{class_name}" SET {update_str} WHERE db_id = {db_id};
                                           """.format(class_name=class_name, db_id=dbid, update_str=update_str))
            else:
                WARN_MSG(f"There are no '{class_name}' entry with dbid {dbid}")
                if ConfigGlobals.ClearMissingEntitiesDBIDs:
                    await self.driver.exec_raw(""" DELETE FROM entities WHERE db_id = {db_id};
                                               """.format(db_id=dbid))

    @rmi()
    async def ClearDatabase(self):
        await self.empty_database()


    async def get_types(self):
        ret_types = dict()
        types = await self.driver.exec_raw(""" SELECT * FROM public.types; """)
        for t_data in types:
            ret_types[t_data[0]] = t_data[1]
        return ret_types