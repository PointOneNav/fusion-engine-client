from construct import (BytesInteger, Struct, Int16ul, Int8ul, Padding, Array, GreedyBytes)

from typing import Union

from .internal_defs import *


class InputDataWrapperMessage(MessagePayload):
    """!
    @brief Wrapper for arbitrary data packets.
    """
    MESSAGE_TYPE = MessageType.INPUT_DATA_WRAPPER
    MESSAGE_VERSION = 0

    CENTI_NANO_SCALE_FACTOR = 10_000_000

    Construct = Struct(
        # 5 byte, unsigned, little endian integer
        "system_time_cs" / BytesInteger(5, swapped=True),
        Padding(1),
        "data_type" / Int16ul,
        # NOTE: Since this message does no capture the expected data size, the Construct relies on the size of the
        # Python buffer passed to `unpack`` to infer the size of the data. This is the behavior of @ref GreedyBytes.
        "data" / GreedyBytes
    )

    def __init__(self):
        self.system_time_ns = 0
        self.data_type = 0
        self.data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        self.system_time_cs = int(self.system_time_ns / self.CENTI_NANO_SCALE_FACTOR)
        ret = MessagePayload.pack(self, buffer, offset, return_buffer)
        del self.__dict__['system_time_cs']
        return ret

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        ret = MessagePayload.unpack(self, buffer, offset, message_version)
        self.system_time_ns = self.system_time_cs * self.CENTI_NANO_SCALE_FACTOR
        del self.__dict__['system_time_cs']
        return ret

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', data_type={self.data_type}, data_len={len(self.data)}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.Construct,
                                           value_to_string={'data': lambda x: f'{len(x)} B payload'},
                                           title=f'Data Wrapper')

    def calcsize(self) -> int:
        return len(self.pack())
