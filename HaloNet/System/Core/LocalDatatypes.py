from typing import Union, Type

from Core.Common.Enum import member
from Core.intrinsic.Serialization import BinarySerialization, SerializationError
from Core.Type import local_datatype, USTRUCT, Private, TypeBase, FText, NSLOCTEXT, UENUM
from Core.Declarators.Specs import Local, Blueprintable, BlueprintType
from Core.intrinsic._BasicTypes import _pack_int8, _pack_uint8,_pack_int16, _pack_uint16, _pack_int32, _pack_uint32, _pack_int64, \
    _pack_uint64, _pack_float, _pack_double, _unpack_int8, _unpack_uint8, _unpack_int16, _unpack_uint16, _unpack_int32, \
    _unpack_uint32, _unpack_int64, _unpack_uint64, _unpack_float, _unpack_double, _pack_str, _unpack_str, _pack_bytes, \
    _unpack_bytes

__all__ = 'uint8', 'int8', 'uint16', 'int16', 'uint32', 'int32', 'uint64', 'int64', 'Bool', 'Float', 'double', \
          'FString', 'FName', 'FText', 'UClass', 'FBytes', 'NSLOCTEXT', \
          'FVector', 'FVector2D', 'FRotator', 'FColor', 'FLinearColor', 'FTransform', 'ELoginResult', 'EJoinResult', \
          'NAME_None'

uint8   = local_datatype('uint8',     int,    'B', 'INT2',          '0',                        literals='%s',          blueprint_atomic=True,   serializer=_pack_uint8,   deserializer=_unpack_uint8,    doc="1 байт без знака")
int8    = local_datatype('int8',      int,    'b', 'INT2',          '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_int8,    deserializer=_unpack_int8,     doc="1 байт со знаком")
uint16  = local_datatype('uint16',    int,    'H', 'INT2',          '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_uint16,  deserializer=_unpack_uint16,   doc="2 байта/слово без знака")
int16   = local_datatype('int16',     int,    'h', 'INT4',          '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_int16,   deserializer=_unpack_int16,    doc="2 байта/слово со знаком")
uint32  = local_datatype('uint32',    int,    'I', 'INT4',          '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_uint32,  deserializer=_unpack_uint32,   doc="4 байта/двойное слово без знака")
int32   = local_datatype('int32',     int,    'i', 'INT8',          '0',                        literals='%s',          blueprint_atomic=True,   serializer=_pack_int32,   deserializer=_unpack_int32,    doc="4 байта/двойное слово со знаком")
uint64  = local_datatype('uint64',    int,    'Q', 'DECIMAL',       '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_uint64,  deserializer=_unpack_uint64,   doc="8 байт/четверное слово без знака")
int64   = local_datatype('int64',     int,    'q', 'INT8',          '0',                        literals='%s',          blueprint_atomic=False,  serializer=_pack_int64,   deserializer=_unpack_int64,    doc="8 байт/четверное слово со знаком")
Bool    = local_datatype('bool',      int,    'b', 'BOOLEAN',       'false',                    literals='%s',          blueprint_atomic=False,  serializer=_pack_uint8,   deserializer=_unpack_uint8,    doc="Булевый")  # used Uppercase due to conflict with pythonic type
Float   = local_datatype('float',     float,  'f', 'NUMERIC',       '0.f',                      literals='%s',          blueprint_atomic=True,   serializer=_pack_float,   deserializer=_unpack_float,    doc="С плавающей точкой")  # used Uppercase due to conflict with pythonic type
double  = local_datatype('double',    float,  'd', 'NUMERIC',       '0.0',                      literals='%s',          blueprint_atomic=False,  serializer=_pack_double,  deserializer=_unpack_double,   doc="С плавающей точкой двойной точности")
FString = local_datatype('FString',   str,    's', 'TEXT',          'TEXT("")', const_ref=True, literals='TEXT("%s")',  blueprint_atomic=True,   serializer=_pack_str,     deserializer=_unpack_str,      doc="Строка")
FName   = local_datatype('FName',     str,    's', 'VARCHAR(255)',  'TEXT("")',                 literals='TEXT("%s")',  blueprint_atomic=True,   serializer=_pack_str,     deserializer=_unpack_str,      doc="Строка-имя")
UClass  = local_datatype('UClass*',   str,    's', 'VARCHAR(255)',  'nullptr',                  literals='',            blueprint_atomic=True,   serializer=_pack_str,     deserializer=_unpack_str,      doc="Ассет (строка-ссылка на ассет)")
FBytes  = local_datatype('FBytes',    bytes,  's', 'BYTEA',         'FBytes()',                 literals='{%s}',        blueprint_atomic=False,  serializer=_pack_bytes,   deserializer=_unpack_bytes,    doc="Байты (как строка, но без кодировки)")

NAME_None = FName("")

from Core.Type import register_pythonic_type
register_pythonic_type(str, FString)
register_pythonic_type(int, int32)
register_pythonic_type(bool, Bool)
register_pythonic_type(float, Float)
register_pythonic_type(bytes, FBytes)
register_pythonic_type(bytearray, FBytes)


@USTRUCT(Private)
class FPropertyInfo:
    """
    Property information for database table
    """
    EntityDBID: int32
    EntityClass: FString
    PropertyTypeName: FString
    PropertyName: FString
    SerializedValue: FBytes


@USTRUCT(Local)
class FVector:
    """ Локальный FVector (только хранилище, без реализации).
        Хранит три координаты (X, Y, Z)
    """
    X: Float
    Y: Float
    Z: Float


@USTRUCT(Local)
class FVector2D:
    """ Локальный FVector2D (только хранилище, без реализации).
        Хранит две координаты (X, Y)
    """
    X: Float
    Y: Float


@USTRUCT(Local)
class FRotator:
    """ Локальный FRotator (только хранилище, без реализации).
        Хранит три угла поворота (Pitch, Yaw, Roll)
    """
    Pitch: Float
    Yaw: Float
    Roll: Float


@USTRUCT(Local)
class FQuat:
    """ Локальный FQuat (только хранилище, без реализации).
        Хранит значения кватерниона (X, Y, Z, W)
    """
    X: Float
    Y: Float
    Z: Float
    W: Float


@USTRUCT(Local)
class FTransform:
    """ Локальный FTransform (только хранилище, без реализации).
        Хранит координаты, положение и размеры
    """
    Rotation: FQuat
    Translation: FVector
    Scale3D: FVector


@USTRUCT(Local)
class FColor:
    """ Локальный FColor (только хранилище, без реализации).
        Хранит 4 канала типа uint8 (целые, 0..255)
    """
    B: uint8
    G: uint8
    R: uint8
    A: uint8


@USTRUCT(Local)
class FLinearColor:
    """ Локальный FLinearColor (только хранилище, без реализации).
        Хранит 4 канала типа float (плавающая точка, относительные - 0..1)
    """
    B: Float
    G: Float
    R: Float
    A: Float


@UENUM(Blueprintable, BlueprintType)
class ELoginResult:
    Success: member()
    NotExists: member()
    Unconfirmed: member()
    Rejected: member()
    InternalError: member()
    InvalidSessionToken: member()

@UENUM(Blueprintable, BlueprintType)
class EJoinResult:
    Admitted: member()
    Disallowed: member()