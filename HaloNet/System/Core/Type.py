import struct
import sys
from datetime import datetime, timedelta
import pytimeparse
import collections

import asyncio
from typing import List, Set, TypeVar, Sequence, Generic, Type, Dict, GenericMeta, Union  # , GenericMeta

import json

import math

from Core.Globals import Globals
from Core.Common.Enum import IntEnum
from Core.ConfigSystem.GeneratorConfig import ConfigurationGenerator
from Core.ConfigSystem.Bases import AppConfig

pythonic_types_mapping = dict()

from Core.Declarators.Specs import *
# from Core.LocalDatatypes import FString, int32, Bool, Float, FBytes

from Core.Logging import INFO_MSG, ERROR_MSG, WARN_MSG

# class TypeMeta(type):
#     def __repr__(self):
#         return "<class TypeBase '%s'>" % self.__name__


# class BoolMeta(type):
#     def __instancecheck__(cls, instance):
#         print('lol')
#         if isinstance(instance, bool):
#             return True
#         return super().__instancecheck__(instance)
from Core.Property import Property, PropertyMcs, SliceReplicationKind
from Core.intrinsic.Serialization import BinarySerialization, SerializationError
from Core.intrinsic._DateTime import _DateTime

from Core.intrinsic._BasicTypes import _pack_int8, _pack_uint8,_pack_int16, _pack_uint16, _pack_int32, _pack_uint32, _pack_int64, \
    _pack_uint64, _pack_float, _pack_double, _unpack_int8, _unpack_uint8, _unpack_int16, _unpack_uint16, _unpack_int32, \
    _unpack_uint32, _unpack_int64, _unpack_uint64, _unpack_float, _unpack_double, _pack_str, _unpack_str, _pack_bytes, \
    _unpack_bytes

def register_pythonic_type(py_type, T):
    global pythonic_types_mapping
    pythonic_types_mapping[py_type] = T


validated_containers = set()


class TypeBase(Property):
    pack_spec = ""
    pg_spec = "int4"
    all_types = dict()
    const_ref = False
    literals = None
    py_type = None
    is_local_datatype = False
    blueprint_atomic = False

    serializer = None
    deserializer = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.register_typename("types", cls.__name__, cls)

    @classmethod
    def pg_null(cls, value):
        if value is None:
            return cls()
        return value

    @classmethod
    def register_typename(cls, context, typename, type):
        if context not in cls.all_types:
            cls.all_types[context] = dict()
        cls.all_types[context][typename] = type

    @classmethod
    def find_type(cls, in_typename, default=None, context=None):
        ret: cls = default
        if context is None:
            for context_data in cls.all_types.values():
                for typename, type in context_data.items():
                    if type.get_type_name() == in_typename:
                        ret = type
                        break
        else:
            context_data = cls.all_types[context]
            for typename, type in context_data.items():
                if typename == in_typename:
                    ret = type
                    break
        return ret

    @classmethod
    def init_typedata(cls, pack_spec, pg_spec, generator_default_value):
        # INFO_MSG("initalizing", cls)
        cls.pack_spec = pack_spec
        cls.pg_spec = pg_spec
        cls.generator_default_value = generator_default_value

    def humanize(self):
        return self.serialize()

    @classmethod
    def serialize_entry(cls, key_value):
        raise SerializationError(f"Not supported for this type ({cls.__name__})")

    @classmethod
    def serialize_key(self, key):
        raise SerializationError(f"Not supported for this type ({cls.__name__})")

    def serialize(self):
        return self.serializer(self.py_type(self))

    @classmethod
    def dehumanize(cls, humanized_value):
        return cls.deserialize(humanized_value)

    @classmethod
    def deserialize(cls, serialized_value):
        return cls.deserializer(serialized_value)

    @classmethod
    def is_validated(cls):
        return True

    @classmethod
    def instantiate(cls, *value):
        return cls(*value)

    @classmethod
    def serializable_value(cls, *value):
        return cls.instantiate(*value)

    @classmethod
    def get_type_name(cls):
        return cls.__name__

    @classmethod
    def get_type_signature(cls):
        return cls.get_type_name()

    @classmethod
    def get_full_type_signature(cls):
        return cls.get_type_signature() if not cls.const_ref else "const %s&" % cls.get_type_signature()


    @classmethod
    def generator_default(cls):
        return cls.generator_default_value

    @classmethod
    def get_base(cls):
        return cls

    def generator_value(self):
        if not self.literals:
            return str(self)
        else:
            return self.literals % self


class StructBase(dict, TypeBase):
    pg_spec = "JSONB"
    fields = list()
    defaults = dict()

    @classmethod
    def init_typedata(cls, fields, defaults, specifiers, kwspecifiers):
        # for field in fields:
        #     print(field)
        cls.fields_names = [field[0] for field in fields]
        cls.fields = fields
        cls.defaults = defaults
        cls.specifiers = specifiers
        cls.kwspecifiers = kwspecifiers
        cls.is_struct_type = True

    @classmethod
    def init_additional_methods(cls, basis_struct_class):
        for item_name, item_value in basis_struct_class.__dict__.items():
            if item_name not in dir(cls) and callable(item_value):
                setattr(cls, item_name, item_value)

    def __getattr__(self, item):
        if item in self.fields_names:
            return self[item]
        return object.__getattr__(item)

    def __setattr__(self, key, value):
        if key in self.fields_names:
            self[key] = value
        else:
            super().__setattr__(key, value)

    def serialize(self):
        serialized = BinarySerialization()
        for field_name, field_type in self.fields:
            # if field_name.lower() in self:
            #     value = self.get(field_name.lower(), None)
            # else:
            #     value = self.get(field_name, None)

            if field_name in self:
                value = self[field_name]
                if not isinstance(value, field_type):
                    value = field_type.instantiate(value)
            else:
                value = field_type.instantiate() if field_name not in self.defaults else field_type.instantiate(self.defaults[field_name])

            serialized << value.serialize()
        return serialized.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        result = cls()
        serialized = BinarySerialization(serialized_value)
        proxy = serialized.proxy()
        for field_name, field_type in cls.fields:
            ds = proxy >> bytes
            value = field_type.deserialize(ds)
            result[field_name] = value
        return result

    @classmethod
    def generator_default(cls):
        return cls.__name__ + "()"

    @classmethod
    def ImplementStorage(cls, *specifiers, primary_key=None):
        def Decorator(in_class):
            from Core.Storage import Storage
            in_class.base = cls

            storage = Storage(in_class.__name__, in_class.base, primary_key)
            # assert in_class.base.is_validated() or error(f"{in_class.base} has invalidated type: {in_class.base.get_invalidated_type()}. Please make validate_container for this type in Types.py", do_exit=True, depth=2)
            storage.specifiers = specifiers
            storage.array_type = TArray[in_class.base]
            storage.name, storage.type = in_class.__name__, in_class.base
            storage_list.append(storage)
            return storage
        return Decorator

    def generator_value(self):
        return self.__class__.__name__ + "(%s)" % ", ".join(self.values())

    # @classmethod
    # def is_validated(cls):
    #     return all([field[1].is_validated() for field in cls.fields])
    #
    # @classmethod
    # def get_invalidated_type(cls):
    #     for field_name, field_type in cls.fields:
    #         if not field_type.is_validated():
    #             if issubclass(field_type, StructBase):
    #                 return field_type.get_invalidated_type()
    #             else:
    #                 return field_type
    #     return None

class EnumBase(TypeBase, IntEnum):
    pack_spec = "h"
    pg_spec = "VARCHAR(255)"

    @classmethod
    def init_typedata(cls, specs, kwspecs):
        cls.is_enum_type = True
        cls.specifiers = specs
        cls.kwspecifiers = kwspecs

    def serialize(self):
        sr = BinarySerialization()
        sr << self._names[int(self)]
        return sr.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        srp = BinarySerialization(serialized_value).proxy()
        ds = srp >> str
        if "::" in ds:
            ds = ds.split("::")[1]
        deserialized = cls(ds)
        return deserialized

    @classmethod
    def generator_default(cls):
        return "%s::%s" % (cls.__name__, str(list(cls.get_members().keys())[0]))

    def generator_value(self):
        return self.__class__.__name__ + "::" + str(self)


class ArrayBase(list, TypeBase):
    pg_spec = "JSONB"
    base = TypeBase
    const_ref = True

    @classmethod
    def init_typedata(cls, base):
        cls.base = base

    def serialize(self):
        serialized = BinarySerialization()
        count = len(self)
        serialized << count
        for index, item in enumerate(self):
            if not isinstance(item, self.base):
                item = self.base.instantiate(item)
            serialized << item.serialize()
        return serialized.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        sr = BinarySerialization(serialized_value).proxy()
        count = sr >> int
        ds = cls()
        for i in range(count):
            item = cls.base.deserialize(sr >> bytes)
            ds.append(item)
        return ds

    @classmethod
    def generator_default(self):
        return "{}"

    @classmethod
    def get_base(cls):
        return cls.base

    @classmethod
    def is_validated(cls):
        return cls.__name__ in validated_containers

    def generator_value(self):
        return "{%s}" % ", ".join(self)


class SetBase(set, TypeBase):
    pg_spec = "JSONB"
    base = TypeBase
    const_ref = True

    @classmethod
    def init_typedata(cls, base):
        cls.base = base

    def serialize(self):
        serialized = BinarySerialization()
        count = len(self)
        serialized << count
        for index, item in enumerate(self):
            if not isinstance(item, self.base):
                item = self.base.instantiate(item)
            serialized << item.serialize()
        return serialized.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        sr = BinarySerialization(serialized_value).proxy()
        count = sr >> int
        ds = cls()
        for i in range(count):
            item = cls.base.deserialize(sr >> bytes)
            ds.add(item)
        return ds

    @classmethod
    def generator_default(self):
        return "{}"

    @classmethod
    def get_base(cls):
        return cls.base

    @classmethod
    def is_validated(cls):
        return cls.__name__ in validated_containers

    def generator_value(self):
        raise NotImplementedError("Sets has no generator default values")


class MapBase(dict, TypeBase):
    pg_spec = "JSONB"
    base_key = TypeBase
    base_value = TypeBase
    const_ref = True


    @classmethod
    def init_typedata(cls, base_key, base_value):
        cls.base_key = base_key
        cls.base_value = base_value

    def serialize(self):
        serialized = BinarySerialization()
        count = len(self)
        serialized << count
        for key in self.keys():
            if not isinstance(key, self.base_key):
                key = self.base_key.instantiate(key)
            serialized << key.serialize()
        for value in self.values():
            if not isinstance(value, self.base_value):
                try:
                    value = self.base_value.instantiate(value)
                except TypeError:
                    print(self.base_value, value)
                    raise
            serialized << value.serialize()
        return serialized.get_archive()


    @classmethod
    def serialize_entry(cls, key_value):
        key, value = key_value
        return BinarySerialization() << cls.base_key.serializable_value(key).serialize() << cls.base_value.serializable_value(value).serialize()

    @classmethod
    def serialize_key(cls, key):
        return BinarySerialization() << cls.base_key.serializable_value(key).serialize()

    @classmethod
    def deserialize(cls, serialized_value):
        sr = BinarySerialization(serialized_value).proxy()
        count = sr >> int

        keys = list()
        values = list()
        for i in range(count):
            item = cls.base_key.deserialize(sr >> bytes)
            keys.append(item)
        for i in range(count):
            item = cls.base_value.deserialize(sr >> bytes)
            values.append(item)
        return cls({keys[i]: values[i] for i in range(count)})

    @classmethod
    def generator_default(self):
        return "{}"

    @classmethod
    def get_base(cls):
        return cls.base_key

    @classmethod
    def is_validated(cls):
        return cls.__name__ in validated_containers

    def generator_value(self):
        raise NotImplementedError("Maps has no generator default values")

    # dict section override


    def edit(self, key):
        class Helper:
            def __init__(self, outer, key):
                self.outer = outer
                self.key = key

            def __enter__(self):
                pass

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.outer.replication_buffer.append((SliceReplicationKind.EditEntry, (self.key, self.outer[self.key])))
        return Helper(self, key)

    def update(self, E=None, **F):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        self.replication_buffer.append((SliceReplicationKind.EditEntry, (key, value)))
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.replication_buffer.append((SliceReplicationKind.RemoveEntry, (key,)))
        dict.__delitem__(self, key)

    def clear(self):
        self.replication_buffer.clear()
        self.replication_buffer.append((SliceReplicationKind.Clear, ()))
        dict.clear(self)

    def pop(self, k, d=None):
        self.replication_buffer.append((SliceReplicationKind.RemoveEntry, (k,)))
        return dict.pop(self, k, d)

    def popitem(self):
        key, value = dict.popitem(self)
        self.replication_buffer.append((SliceReplicationKind.RemoveEntry, (key,)))
        return key, value



class __UJsonRawBase(dict, TypeBase):
    """ Тип JSON (для неконкретных данных) """

    pg_spec = "JSONB"

    def serialize(self):
        serialized = BinarySerialization()
        serialized << json.dumps(self)
        return serialized.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        srp = BinarySerialization(serialized_value).proxy()
        deserialized = srp >> str
        return json.loads(deserialized)

    @classmethod
    def generator_default(self):
        return "nullptr"

    @classmethod
    def instantiate(cls, value=None):
        return cls(value if value else {})

    def generator_value(self):
        raise NotImplementedError("JSON has no generator default values")


UJsonRaw: Type[__UJsonRawBase] = type("UJsonRaw*", (__UJsonRawBase,),
                                      {
                                          "is_local_datatype": True,
                                          "__doc__": __UJsonRawBase.__doc__
                                      })


class TextFormatValueType:
    Simple = 0
    Text = 1


class FText(str, TypeBase):
    """ Unreal FText """
    pack_spec = "s"
    pg_spec = "TEXT"
    generator_default_value = "FText()"
    const_ref = True
    is_local_datatype = True

    def __init__(self, *args, **kwargs):
        str.__init__(*args, **kwargs)
        self.namespace = "UnknownNamespace"
        self.key = "UnknownKey"
        self.format_values = list()

    def init_text(self, namespace, key):
        self.namespace = namespace if namespace else "UnknownNamespace"
        self.key = key if key else "UnknownKey"

    def serialize(self):
        sr = BinarySerialization()
        sr << self
        sr << self.key
        sr << self.namespace
        sr << len(self.format_values)
        for value in self.format_values:
            if isinstance(value, FText):
                sr << TextFormatValueType.Simple
                sr << str(value)
            else:
                sr << TextFormatValueType.Text
                sr << value.serialize()
        return sr.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        srp = BinarySerialization(serialized_value).proxy()
        text = srp >> str
        key = srp >> str
        namespace = srp >> str
        format_values_count = srp >> int
        format_values = list()

        for i in range(0, format_values_count):
            value_type = srp >> int
            if value_type == TextFormatValueType.Simple:
                serialized_value = srp >> str
                value = serialized_value
            elif value_type == TextFormatValueType.Text:
                serialized_value = srp >> bytes
                value = FText.deserialize(serialized_value)
            else:
                raise SerializationError("Cannot deserialize FText")
            format_values.append(value)

        result = FText(text)
        result.init_text(namespace=namespace, key=key)
        result.format_values = format_values
        return result

    def format(self, *args):
        self.format_values = args
        return self

    def to_string(self):
        formatted_values = list()
        for s in self.format_values:
            if isinstance(s, FText):
                formatted_values.append(s.to_string())
            else:
                formatted_values.append(s)
        return str.format(self, *formatted_values)

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return f'<FText namespace="{self.namespace}", key="{self.key}": "{str.__str__(self)}">'

    def __mod__(self, other):
        if not isinstance(other, (tuple, list)):
            other = other,
        return self.format(*other)

    def generator_value(self):
        return f'NSLOCTEXT("{self.namespace}", "{self.key}", "{str.__str__(self)}")'


class _timespan:
    TicksPerDay =    864_000_000_000
    TicksPerHour =    36_000_000_000
    TicksPerMicrosecond =         10
    TicksPerMillisecond =     10_000
    TicksPerMinute =     600_000_000
    TicksPerSecond =      10_000_000
    TicksPerWeek = 6_048_000_000_000

    DaysPerMonth = [0, 31, 28, 31,  30,  31,  30,  31,  31,  30,  31,  30,  31]
    DaysToMonth  = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]

class FTimespan(timedelta, TypeBase):
    pg_spec = "TIMESTAMP"
    generator_default_value = "FTimespan()"
    is_local_datatype = True

    @staticmethod
    def td_from_string(td_string):
        seconds = pytimeparse.parse(td_string)
        return timedelta(seconds=seconds)

    def serialize(self):
        int64_type = self.find_type('int64')
        assert int64_type is not None or error("int64 type missing", do_exit=True, depth=2)
        days, seconds, microseconds, milliseconds, minutes, hours, weeks = self.get_decayed(self)
        days += weeks * 7
        ticks = _timespan.TicksPerMicrosecond * (1000 * (1000 * (60 * 60 * 24 * days + 60 * 60 * hours + 60 * minutes + seconds) + milliseconds) + microseconds)
        return int64_type(ticks).serialize()

    @classmethod
    def deserialize(cls, serialized_value):
        int64_type = cls.find_type('int64')
        assert int64_type is not None or error("int64 type missing", do_exit=True, depth=2)
        ticks = int64_type.deserialize(serialized_value)

        days = ticks // _timespan.TicksPerDay
        hours = (ticks // _timespan.TicksPerHour) % 24
        microseconds = (ticks // _timespan.TicksPerMicrosecond) % 1000
        milliseconds = (ticks // _timespan.TicksPerMillisecond) % 1000
        minutes = (ticks // _timespan.TicksPerMinute) % 60
        seconds = (ticks // _timespan.TicksPerSecond) % 60

        result = cls(days, seconds, microseconds, milliseconds, minutes, hours)
        return result

    def generator_value(self):
        return self.__class__.__name__ + "()"

    @classmethod
    def instantiate(cls, *value):
        if len(value) == 1:
            td: timedelta = value[0]
            if isinstance(td, timedelta):
                days, seconds, microseconds, milliseconds, minutes, hours, weeks = cls.get_decayed(td)
                return cls(days, seconds, microseconds, milliseconds, minutes, hours, weeks)
            elif isinstance(td, str):
                td = cls.td_from_string(td)
                return cls.instantiate(td)

        return cls(*value)

    @staticmethod
    def get_decayed(d: timedelta):
        total_seconds = d.total_seconds()

        weeks = int(total_seconds // 604800)
        total_seconds -= weeks * 604800

        days = int(total_seconds // 86400)
        total_seconds -= days * 86400

        hours = int(total_seconds // 3600)
        total_seconds -= hours * 3600

        minutes = int(total_seconds // 60)
        total_seconds -= minutes * 60

        seconds = int(total_seconds)

        microseconds = d.microseconds % 1000
        milliseconds = d.microseconds // 1000

        return days, seconds, microseconds, milliseconds, minutes, hours, weeks



class FDateTime(_DateTime, TypeBase):
    pg_spec = "TIMESTAMP"
    generator_default_value = "FDateTime()"
    is_local_datatype = True

    @classmethod
    def invalid(cls):
        return cls(1900, 1, 1)

    @classmethod
    def pg_null(cls, value):
        if value is None:
            return cls.instantiate()
        return value

    def serialize(self):
        return _pack_int64( self.get_ticks() )

    @classmethod
    def deserialize(cls, serialized_value):
        ticks = _unpack_int64(serialized_value)
        year, month, day, hour, minute, second, millisecond = cls.get_by_ticks(ticks)
        result = cls(year, month, day, hour, minute, second, millisecond * 1000)
        return result

    @classmethod
    def instantiate(cls, *value):
        if len(value) == 1:
            dt = value[0]
            if isinstance(dt, datetime):
                return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)
            elif isinstance(dt, str):
                fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in dt else '%Y-%m-%d %H:%M:%S'
                return datetime.strptime(dt, fmt)
        return datetime(1, 1, 1)

    @classmethod
    def generator_default(cls):
        return cls.generator_default_value

    def to_string(self):
        return f'{self.year}.{self.month}.{self.day} {self.hour}:{self.minute}'

def NSLOCTEXT(namespace, key, text_value):
    text = FText(text_value)
    text.init_text(namespace, key)
    return text


class AssetPtrBase(str, TypeBase):
    pg_spec = "VARCHAR(255)"
    pack_spec = "s"
    class_name = None

    @classmethod
    def init_typedata(cls, class_name):
        cls.class_name = class_name
        cls.generator_default_value = 'nullptr'

# def local_datatype(datatype_name, py_type, pack_spec, pg_spec, generator_default, const_ref=False):
#     new_type = type(datatype_name, (py_type, TypeBase), {})
#     new_type.const_ref = const_ref
#     new_type.init_typedata(pack_spec, pg_spec, generator_default)
#     return new_type

class SubclassBase(str, TypeBase):
    pg_spec = "VARCHAR(255)"
    pack_spec = "s"
    class_name = None
    serializer = _pack_str
    deserializer = _unpack_str
    py_type = str

    @classmethod
    def init_typedata(cls, class_name):
        cls.class_name = class_name
        cls.generator_default_value = 'nullptr'

T = TypeVar('T')
def local_datatype(datatype_name, py_type: T, pack_spec, pg_spec, generator_default, const_ref=False, doc=None, literals=None, blueprint_atomic=False, serializer=None, deserializer=None) -> Union[T, Type[TypeBase]]:
    """ Declares an local data type
        @param datatype_name: type name
        @param py_type: python-ancestor
        @param pack_spec: packing specifier
        @param pg_spec: data specifier for Postgres
        @param generator_default: default value for codegen
        @param const_ref: is const reference in C++?
        @param doc: documentation
        @param literals: literals for codegen
        @param blueprint_atomic: available for generator (struct field for storage)
        @return: new type
    """
    new_type: Type[TypeBase] = type(datatype_name, (py_type, TypeBase), {})
    new_type.const_ref = const_ref
    new_type.init_typedata(pack_spec, pg_spec, generator_default)
    new_type.is_local_datatype = True
    new_type.__doc__ = doc
    new_type.blueprint_atomic = blueprint_atomic
    new_type.literals = literals
    new_type.serializer = serializer
    new_type.deserializer = deserializer
    new_type.py_type = py_type
    frame = sys._getframe(1)
    new_type.inspect_info = get_file_line(frame)
    return new_type


def init_typedata(*args, **kwargs):
    def decorator(cls):
        cls.init_typedata(*args, **kwargs)
        return cls
    return decorator



class MailboxProxyDatatype(TypeBase):
    mailbox_class = None
    meta_class_name = "Unknown"
    meta_context_name = "Unknown"
    simple_name = "Unknown"
    is_exposed_mailbox = False
    generator_default_value = ""

    # def __init__(self, context_name, class_name, endpoint, id):
    #     self.context_name = context_name
    #     self.class_name = class_name
    #     self.endpoint = endpoint
    #     self.remote_id = id


    def serialize(self):
        sr = BinarySerialization()
        sr << str(self.get_endpoint()[0])
        sr << self.get_endpoint()[1]
        sr << self.get_id()
        sr << self.get_context()
        sr << self.get_class_name()
        return sr.get_archive()

    @classmethod
    def deserialize(cls, serialized_value):
        srp = BinarySerialization(serialized_value).proxy()
        endpoint = [None, None]
        try:
            endpoint[0] = srp >> str
            endpoint[1] = srp >> int
            id          = srp >> int
            context     = srp >> str
            cls_name    = srp >> str
        except Exception as e:
            ERROR_MSG("Failed to deserialize mailbox: %s", srp)
            raise


        # symbol = SymbolsRegistry().get_by_context(context, cls_name)
        # return Mailbox(symbol, endpoint, id, context)
        return cls.get_mailbox_class()(context, cls_name, endpoint, id)


    def init(self, class_name, context_name, endpoint, remote_id):
        self.class_name = class_name
        self.context_name = context_name
        self.endpoint = endpoint
        self.remote_id = remote_id
        self.initialized = True
        self.is_exposed_mailbox = False

    def as_exposed(self):
        mb = self.instantiate(self)
        mb.endpoint = Globals.this_service.exposed_ip, mb.endpoint[1]
        mb.entity_info = ConfigurationGenerator().generated_entities_info.get_by_name(self.class_name)
        mb.is_exposed_mailbox = True

        return mb

    @classmethod
    def instantiate(cls, value=None):
        if value is None:
            retval = cls()
            retval.init(cls.meta_class_name, cls.meta_context_name, ("0.0.0.0", 0),  0)
            return retval

        retval = cls()
        # INFO_MSG("Init %s %s" % (cls, value))
        retval.init(value.get_class_name(), value.get_context(), value.get_endpoint(), value.get_id())
        return retval

    @classmethod
    def get_mailbox_class(cls):
        return cls.mailbox_class

    def get_endpoint(self):
        return self.endpoint

    def get_id(self):
        return self.remote_id

    def get_context(self):
        return self.context_name

    def get_class_name(self):
        return self.class_name

    @classmethod
    def get_type_name(cls):
        # return cls.meta_class_name + cls.meta_context_name.capitalize() + "Mailbox"
        return cls.simple_name

    @classmethod
    def get_type_signature(cls):
        return "U" + cls.get_type_name() + "*"


def declare_struct(basis_struct_class, datatype_name, fields, defaults, specifiers, kwspecifiers) -> type(dict):
    new_type = type(datatype_name, (StructBase,), {})
    new_type.init_typedata(fields, defaults, specifiers, kwspecifiers)
    new_type.init_additional_methods(basis_struct_class)
    return new_type


def declare_enum(datatype_name, base_class, specifiers, kwspecifiers):
    annotations = getattr(base_class, '__annotations__', dict())
    class_dict = {'__annotations__': annotations}
    for a in annotations.keys():
        if hasattr(base_class, a):
            class_dict[a] = getattr(base_class, a)
    new_type = type(datatype_name, (EnumBase,), class_dict)
    new_type.init_typedata(specifiers, kwspecifiers)
    return new_type



def UENUM(*specifiers, **kwspecifiers):
    def decorator(cls) -> EnumBase:
        assert cls.__name__.startswith("E") or error("UENUMS should starts with 'E'", depth=2, do_exit=True)
        values = None
        new_type = declare_enum(cls.__name__, cls, specifiers, kwspecifiers)
        frame_info = sys._getframe(1)
        new_type.inspect_info = get_file_line(frame_info)
        new_type.__doc__ = cls.__doc__
        return new_type
    return decorator


def complicate_type(T, outer):
    """ If passed python type, the Type ancestor will be returned. Else 'T' will be"""
    if T in pythonic_types_mapping:
        out_T = pythonic_types_mapping[T]
        WARN_MSG(f"Pythonic type has been used in {outer} ({T}), {out_T} will be substituted",
                 once="complication",
                 depth=2,
                 warning_id="TYPE_NEGLECT")
        return out_T
    assert issubclass(T, TypeBase) or error("Invalid type %s for %s" % (T, outer), depth=3, do_exit=True)
    return T


def USTRUCT(*specifiers, **kwspecifiers):
    def decorator(cls) -> StructBase:
        assert cls.__name__.startswith("F") or error("USTRUCTS should starts with 'F'", depth=2, do_exit=True)
        defaults = dict()
        items = list()
        for key, in_T in cls.__annotations__.items():
            default_value = getattr(cls, key, None)
            T = complicate_type(in_T, cls.__name__)
            if default_value is not None:
                defaults[key] = T
            items.append((key, T))
        # for name, T in cls.__annotations__.items():
        #     assert isinstance(T, type) and issubclass(T, TypeBase) or error("Invalid type %s for %s" % (T, name), depth=2, do_exit=True)
        new_type = declare_struct(cls, cls.__name__, items, defaults, specifiers, kwspecifiers)
        frame_info = sys._getframe(1)
        new_type.inspect_info = get_file_line(frame_info)
        new_type.__doc__ = cls.__doc__
        new_type.__gencode__ = getattr(cls, '__gencode__', None)
        return new_type
    return decorator


storage_list = list()


def STORAGE(cls):
    from Core.Storage import Storage
    assert hasattr(cls, 'base') or error("Storage has no 'base'", depth=2, do_exit=True)
    assert isinstance(cls.base, type) and issubclass(cls.base, StructBase) or error("Storage base must be USTRUCT", depth=2, do_exit=True)
    storage = Storage(cls.__name__, cls.base)
    storage.name, storage.type = cls.__name__, cls.base
    storage_list.append(storage)
    return storage

from Core.Utils import error, get_file_line

class CA(PropertyMcs, GenericMeta):
    __origin__ = None

class GenericMeta_TArray(CA):
    def __new__(cls, *args, **kwargs):
        return type.__new__(cls, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        error("Cannot instantiate TArray directly", depth=2)

    def __getitem__(self, base):
        base = complicate_type(base, "TArray")
        assert issubclass(base, TypeBase) or error("Invalid array type base '%s'" % base, depth=2, do_exit=True)
        new_type = type("TArray<%s>" % base.__name__, (ArrayBase,), {})
        new_type.init_typedata(base)
        return new_type


class GenericMeta_TSet(CA):
    def __new__(cls, *args, **kwargs):
        return type.__new__(cls, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        error("Cannot instantiate TSet directly", depth=2)

    def __getitem__(self, base):
        base = complicate_type(base, "TSet")
        assert issubclass(base, TypeBase) or error("Invalid set type base '%s'" % base, depth=2, do_exit=True)
        new_type = type("TSet<%s>" % base.__name__, (SetBase,), {})
        new_type.init_typedata(base)
        return new_type


class GenericMeta_TMap(CA):
    def __new__(cls, *args, **kwargs):
        return type.__new__(cls, *args) # , **kwargs)

    def __call__(self, *args, **kwargs):
        error("Cannot instantiate TMap directly", depth=2, do_exit=True)

    def __getitem__(self, item):
        item = complicate_type(item[0], "TMap"), complicate_type(item[1], "TMap")
        assert isinstance(item, tuple) and len(item) == 2
        base_key, base_value = item
        assert issubclass(base_key, TypeBase) or error("Invalid map type key base '%s'" % base_key, depth=2, do_exit=True)
        assert issubclass(base_value, TypeBase) or error("Invalid map type value base '%s'" % base_value, depth=2, do_exit=True)
        new_type = type("TMap<%s, %s>" % (base_key.__name__, base_value.__name__), (MapBase,), {})
        new_type.init_typedata(base_key, base_value)
        return new_type

class GenericMeta_TAssetSubclassOf(CA):
    def __new__(cls, *args, **kwargs):
        return type.__new__(cls, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        error("Cannot instantiate TAssetSubclassOf directly", depth=2, do_exit=True)

    def __getitem__(self, class_name):
        assert isinstance(class_name, str)
        new_type = type("TAssetSubclassOf<class %s>" % (class_name), (AssetPtrBase,), {})
        new_type.init_typedata(class_name)
        return new_type


class GenericMeta_TSubclassOf(CA):
    def __new__(cls, *args, **kwargs):
        return type.__new__(cls, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        error("Cannot instantiate TSubclassOf directly", depth=2, do_exit=True)

    def __getitem__(self, item):
        assert isinstance(item, str)
        new_type = type("TSubclassOf<class %s>" % (item), (SubclassBase,), {})
        new_type.init_typedata(item)
        return new_type

class TArray(ArrayBase, list, metaclass=GenericMeta_TArray):
    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate TArray directly")


class TSet(Set, SetBase, set, metaclass=GenericMeta_TSet):
    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate TSet directly")


class TMap(Dict, MapBase, dict, metaclass=GenericMeta_TMap):
    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate TMap directly")


class TSubclassOf(SubclassBase, str, metaclass=GenericMeta_TSubclassOf):
    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate TSubclassOf directly")


class TAssetSubclassOf(SubclassBase, str, metaclass=GenericMeta_TAssetSubclassOf):
    def __call__(self, *args, **kwargs):
        raise TypeError("Cannot instantiate TAssetSubclassOf directly")



def make_mailbox_proxy(context_name, class_name):
    name_suffix = context_name.capitalize()
    if class_name in AppConfig.by_name:
        name_suffix = ""
    datatype_name = class_name + name_suffix + "Mailbox"
    new_type = type(datatype_name, (MailboxProxyDatatype,), {})
    new_type.meta_class_name = class_name
    new_type.meta_context_name = context_name
    new_type.simple_name = datatype_name
    return new_type


def TMailbox(context_name, class_name):
    return make_mailbox_proxy(context_name, class_name)


def TBaseMailbox(class_name):
    return make_mailbox_proxy("base", class_name)


def TDBMailbox(class_name):
    return make_mailbox_proxy("db", class_name)


def TUE4Mailbox(class_name):
    return make_mailbox_proxy("ue4", class_name)


def CustomClientMailbox():
    return make_mailbox_proxy("", "")


def validate_container(container):
    if container.__name__ in validated_containers:
        WARN_MSG(f"Container {container} already validated", depth=1)
    validated_containers.add(container.__name__)

def validate_containers(*containers):
    for c in containers:
        validate_container(c)


def reconstruct(T, value):
    if (isinstance(value, list) and issubclass(T, dict)) or \
       (isinstance(value, dict) and issubclass(T, list)):
        return T()

    if isinstance(value, str) and issubclass(T, EnumBase):
        return T(value)

    if isinstance(value, str) and issubclass(T, str) or \
       isinstance(value, (int, float)) and issubclass(T, (int, float)):
        return T(value)

    if isinstance(value, str) and issubclass(T, (int, float)):
        if value.isdigit():
            return T(value)
        else:
            return T()

    if isinstance(value, str) and issubclass(T, (int, float)):
        if value.isdigit():
            return T(value)
        else:
            return T()

    if isinstance(value, (int, float)) and issubclass(T, str):
        return T(value)

    if isinstance(value, list) and issubclass(T, ArrayBase):
        result = T()
        for index, entry in enumerate(value):
            r = reconstruct(T.base, entry)
            result.append(r)
        return result

    elif isinstance(value, dict) and issubclass(T, StructBase):
        result = T()
        for field_name, field_type in T.fields:
            if field_name not in value:
                result[field_name] = field_type()
            else:
                result[field_name] = reconstruct(field_type, value[field_name])
        return result

    elif isinstance(value, dict) and issubclass(T, MapBase):
        result = T()
        for map_key, map_value in value.items():
            map_key = reconstruct(T.base_key, map_key)
            map_value = reconstruct(T.base_value, map_value)
            result[map_key] = map_value
        return result

    elif isinstance(value, list) and issubclass(T, SetBase):
        result = T()
        for index, entry in enumerate(value):
            r = reconstruct(T.base, entry)
            result.add(r)
        return result
