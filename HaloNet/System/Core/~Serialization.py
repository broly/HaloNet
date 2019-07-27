import struct

# from Core import INFO_MSG
# from Core.Type import TypeBase

class SerializationError(ValueError):
    """ Error while serializing or deserializing """


class BinarySerializationProxy:
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


class BinarySerialization:
    def __init__(self, other=None):
        if other == None:
            self.binary_data = bytes((0, 0, 0, 0))
        else:
            self.binary_data = other

    def get_count(self) -> int:
        count = struct.unpack('i', self.binary_data[0:4])[0]
        return count

    def get_offsets(self) -> list:
        result = list()
        for i in range(self.get_count()):
            data = self.binary_data[4 + (i * 4):4 + (i * 4) + 4]
            if len(data) == 4:
                offset = struct.unpack('i', data)[0]
            else:
                raise SerializationError("Unable to deserialize section")
            result.append(offset)
        return result

    def get_data(self):
        result = list()
        working_data = self.binary_data[4 + 4 * self.get_count():]
        data_offsets = self.get_offsets() + [len(working_data)]
        for i in range(0, len(data_offsets) - 1):
            left = data_offsets[i]
            right = data_offsets[i+1]
            result.append(working_data[left:right])
        return result

    def add_data(self, new_data: bytes):
        result = bytes()
        datas = list(self.get_data())
        datas.append(new_data)

        count = len(datas)
        result += struct.pack('i', count)

        last_offset = 0
        for data in datas:
            result += struct.pack('i', last_offset)
            last_offset += len(data)

        for data in datas:
            result += data

        self.binary_data = result

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

    def proxy(self):
        try:
            return BinarySerializationProxy(self.get_data())
        except struct.error:
            raise SerializationError

    def get_archive(self):
        return self.binary_data

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