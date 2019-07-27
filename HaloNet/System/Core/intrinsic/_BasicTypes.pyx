# from cpython cimport PyObject, PyTypeObject, Py_TYPE
from time import time

import struct
from libc.string cimport memcpy, memset
from cython.operator cimport dereference as deref
from libcpp.memory cimport shared_ptr


from libcpp cimport cast



ctypedef signed char int8
ctypedef unsigned char uint8
ctypedef signed short short int16
ctypedef unsigned short short uint16
ctypedef signed int int32
ctypedef unsigned int uint32
ctypedef signed long long int64
ctypedef unsigned long long uint64


cdef extern from "Utils.h":
    cdef void print_mem_as_chars(void* ptr, int32 size)
    cdef void print_mem_as_ints(void* ptr, int32 size)

cdef extern from "BinaryConverters.h":
    void pack_bytes(const char* Bytes, int BytesNum, shared_ptr[char]& OutPackedBytes, int& OutSize)
    void unpack_bytes(const char* InPackedBytes, int InSize, shared_ptr[char]& OutBytes, int& OutBytesNum)


ctypedef signed char* int8_ptr
ctypedef unsigned char* uint8_ptr
ctypedef signed short short* int16_ptr
ctypedef unsigned short short* uint16_ptr
ctypedef signed int* int32_ptr
ctypedef unsigned int* uint32_ptr
ctypedef signed long long* int64_ptr
ctypedef unsigned long long* uint64_ptr
ctypedef float* float_ptr
ctypedef double* double_ptr

ctypedef char* pchar


def _pack_int8(int8 value):
    return cast.reinterpret_cast[pchar](&value)[:1]

def _pack_uint8(uint8 value):
    return cast.reinterpret_cast[pchar](&value)[:1]

def _pack_int16(int16 value):
    return cast.reinterpret_cast[pchar](&value)[:2]

cdef inline pchar __pack_int16(int16 value):
    return cast.reinterpret_cast[pchar](&value)[:2]

def _pack_uint16(uint16 value):
    return cast.reinterpret_cast[pchar](&value)[:2]

def _pack_int32(int32 value):
    return cast.reinterpret_cast[pchar](&value)[:4]

def _pack_uint32(uint32 value):
    return cast.reinterpret_cast[pchar](&value)[:4]

def _pack_int64(int64 value):
    return cast.reinterpret_cast[pchar](&value)[:8]

def _pack_uint64(uint64 value):
    return cast.reinterpret_cast[pchar](&value)[:8]

def _pack_float(float value):
    return cast.reinterpret_cast[pchar](&value)[:4]

def _pack_double(double value):
    return cast.reinterpret_cast[pchar](&value)[:8]



def _unpack_int8(char* value):
    return deref(cast.reinterpret_cast[int8_ptr](value))

def _unpack_uint8(char* value):
    return deref(cast.reinterpret_cast[uint8_ptr](value))

def _unpack_int16(char* value):
    return deref(cast.reinterpret_cast[int16_ptr](value))

def _unpack_uint16(char* value):
    return deref(cast.reinterpret_cast[uint16_ptr](value))

def _unpack_int32(char* value):
    return deref(cast.reinterpret_cast[int32_ptr](value))

def _unpack_uint32(char* value):
    return deref(cast.reinterpret_cast[uint32_ptr](value))

def _unpack_int64(char* value):
    return deref(cast.reinterpret_cast[int64_ptr](value))

def _unpack_uint64(char* value):
    return deref(cast.reinterpret_cast[uint64_ptr](value))


def _unpack_float(char* value):
    return deref(cast.reinterpret_cast[float_ptr](value))

def _unpack_double(char* value):
    return deref(cast.reinterpret_cast[double_ptr](value))



def _pack_str(str string):
    encoded = string.encode('utf-8')
    cdef shared_ptr[char] packed
    cdef int out_size = 0
    pack_bytes(encoded, len(encoded), packed, out_size)
    return packed.get()[:out_size]



def _unpack_str(bytes packed):
    cdef shared_ptr[char] encoded
    cdef int out_size = 0
    unpack_bytes(packed, len(packed), encoded, out_size)
    return (encoded.get()[:out_size]).decode('utf-8')


def _pack_bytes(bytes in_bytes):
    cdef shared_ptr[char] packed
    cdef int out_size = 0
    pack_bytes(in_bytes, len(in_bytes), packed, out_size)
    return packed.get()[:out_size]



def _unpack_bytes(bytes packed):
    cdef shared_ptr[char] out_bytes
    cdef int out_size = 0
    unpack_bytes(packed, len(packed), out_bytes, out_size)
    return out_bytes.get()[:out_size]



def test_call():

    t = time()
    for i in range(100000):
        a = __pack_int16(32345)
    print(time() - t)

    t = time()
    for i in range(100000):
        a = _pack_int16(32345)
    print(time() - t)

    t = time()
    for i in range(100000):
        b = struct.pack('i', 32345)
    print(time() - t)
