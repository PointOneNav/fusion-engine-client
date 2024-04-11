from construct import (BytesInteger, Struct, Int16ul, Int8ul, Padding, Array, GreedyBytes)

from typing import Union

from .internal_defs import *


class DataWrapperMessage(MessagePayload):
    """!
    @brief Wrapper for arbitrary data packets.
    """
    MESSAGE_TYPE = MessageType.DATA_WRAPPER
    MESSAGE_VERSION = 0

    Construct = Struct(
        # 5 byte, unsigned, little endian integer
        "timestamp_ms" / BytesInteger(5, swapped=True),
        Padding(1),
        "data_type" / Int16ul,
        # NOTE: Since this message does no capture the expected data size, the Construct relies on the size of the
        # Python buffer passed to `unpack`` to infer the size of the data. This is the behavior of @ref GreedyBytes.
        "data" / GreedyBytes
    )

    def __init__(self):
        self.timestamp_ms = 0
        self.data_type = 0
        self.data = bytes()

    # Use default MessagePayload.pack and MessagePayload.unpack

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', data_type={self.data_type}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.Construct,
                                           value_to_string={'data': lambda x: f'{len(x)} B payload'},
                                           title=f'Data Wrapper')

    def calcsize(self) -> int:
        return len(self.pack())
