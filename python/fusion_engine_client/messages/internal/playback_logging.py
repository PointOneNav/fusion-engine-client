from construct import (Struct, Int16ul, Int8ul, Padding, Array, GreedyBytes)

from typing import Union

from .internal_defs import *


class DataWrapperMessage(MessagePayload):
    """!
    @brief Wrapper for arbitrary data packets.
    """
    MESSAGE_TYPE = MessageType.DATA_WRAPPER
    MESSAGE_VERSION = 0

    DataWrapperMessageConstruct = Struct(
        "time_stamp_data" / Array(5, Int8ul),
        Padding(1),
        "data_type" / Int16ul,
        "data" / GreedyBytes
    )

    def __init__(self):
        self.timestamp_ms = 0
        self.data_type = 0
        self.data = bytes()

    def pack_timestamp(self) -> bytes:
        return bytes([(self.timestamp_ms >> (i*8)) & 0xFF for i in range(5)])

    def unpack_timestamp(self, time_stamp_data: bytes) -> None:
        self.timestamp_ms = 0
        for i in range(5):
            self.timestamp_ms += time_stamp_data[i] << (i*8)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> Union[bytes, int]:
        packed_data = self.DataWrapperMessageConstruct.build(
            {"time_stamp_data": self.pack_timestamp(), "data_type": self.data_type, "data": self.data})
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.DataWrapperMessageConstruct.parse(buffer[offset:])
        self.unpack_timestamp(parsed.time_stamp_data)
        self.data_type = parsed.data_type
        self.data = parsed.data
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', data_type={self.data_type}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.DataWrapperMessageConstruct,
                                           value_to_string={'data': lambda x: f'{len(x)} B payload'},
                                           title=f'Data Wrapper')

    def calcsize(self) -> int:
        return len(self.pack())
