import struct
from typing import Type, Union

from libcpp.vector cimport vector
from libcpp.memory cimport shared_ptr

cdef extern from "BinaryArchive.h":
    cdef cppclass BinaryArchive:
        BinaryArchive()
        BinaryArchive(char* InOther, int InSize)
        void Add(char* InData, int InCount)
        int Size() const
        void GetArchive(shared_ptr[char]& OutArchive, int& OutArchiveSize)
        void GetData(vector[char*]& OutData, vector[int]& OutCounts) const
        bint IsValid() const


class SerializationError(ValueError):
    """ Error while serializing or deserializing """

cdef class BinarySerializationProxy:
    def __init__(self, data_list):
        self.data_list = data_list

    def __rshift__(self, other):
        if len(self.data_list) == 0:
            # INFO_MSG("Proxy is empty")
            return None

        data = self.data_list.pop(0)

        if issubclass(other, int):
            return BinarySerialization.bytes2int(data)
        elif issubclass(other, str):
            return BinarySerialization.bytes2str(data)
        elif issubclass(other, bytes):
            return data
        elif issubclass(other, BinarySerialization):
            return BinarySerialization(data)
        elif hasattr(other, "__deserialize__"):  # todo WIP small feature
            return other.__deserialize__(data)


cdef class BinarySerialization:
    cdef BinaryArchive archive

    def __cinit__(self, other=None):
        if isinstance(other, bytes):
            self.archive = BinaryArchive(<char*>other, len(other))
        else:
            self.archive = BinaryArchive()

    def __init__(self, other=None):
        """ @see BinarySerialization.__cinit__ """

    def get_count(self):
        return self.archive.Size()

    def get_offsets(self) -> list:
        pass

    def get_archive(self):
        cdef shared_ptr[char] archive
        cdef int size = 0
        self.archive.GetArchive(archive, size)
        cdef char* chars = archive.get()
        return chars[:size]

    def add_data(self, bytes new_data):
        cdef char* data = new_data
        self.archive.Add(data, len(new_data))


    def __lshift__(self, other):
        if isinstance(other, int):
            archived = self.int2bytes(other)
            self.add_data(archived)
            return self
        elif isinstance(other, str):
            archived = self.str2bytes(other)
            self.add_data(archived)
            return self
        elif isinstance(other, bytes):
            self.add_data(other)
            return self
        elif isinstance(other, BinarySerialization):
            archived = other.get_archive()
            self.add_data(archived)
            return self
        elif hasattr(other, "__serialize__"):  # todo WIP small feature
            return other.__serialize__(other)


    def get_data(self):
        cdef vector[char*] data
        cdef vector[int] counts
        self.archive.GetData(data, counts)
        result = []
        for i in range(data.size()):
            s = data[i]
            size = counts[i]
            result.append(s[:size])
        return result

    def proxy(self):
        return BinarySerializationProxy(self.get_data())

    @staticmethod
    def bytes2str(in_bytes: bytes):
        mc = struct.unpack('i', in_bytes[0:4])[0]
        mn = struct.unpack(str(mc)+'s', in_bytes[4:])
        return mn[0].decode()

    @staticmethod
    def bytes2int(in_bytes: bytes):
        return struct.unpack('i', in_bytes)[0]

    @staticmethod
    def str2bytes(in_string: str):
        result = bytes()
        str_len = len(in_string)
        result += struct.pack('i', str_len)
        result += struct.pack(str(str_len)+'s', bytes(in_string, 'utf-8'))
        return result

    @staticmethod
    def int2bytes(in_value: int):
        return struct.pack('i', in_value)
