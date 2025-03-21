from construct import (GreedyBytes, Padding, Struct, Int8ul, Int32ul, Int64sl, Bytes)

from ..utils.construct_utils import construct_message_to_string
from .defs import *


class STA5635Command(MessagePayload):
    """!
    @brief A command to be sent to an attached STA5635 RF front-end.
    """
    MESSAGE_TYPE = MessageType.STA5635_COMMAND
    MESSAGE_VERSION = 0

    Construct = Struct(
        "command" / Int8ul,
        "address" / Int8ul,
        "data" / Bytes(2),
    )

    def __init__(self):
        self.command = 0
        self.address = 0
        self.data = bytes()

    def pack(self, buffer: Optional[bytes] = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    def calcsize(self) -> int:
        return self.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', command=0x{self.command:02X}, address=0x{self.address:02X}, data={self.data}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, value_to_string={
            'command': lambda x: f'0x{x:02X}',
            'address': lambda x: f'0x{x:02X}',
        })


class STA5635CommandResponse(MessagePayload):
    """!
    @brief Result from an STA5635 sent in response to an @ref STA5635Command.
    """
    MESSAGE_TYPE = MessageType.STA5635_COMMAND_RESPONSE
    MESSAGE_VERSION = 0

    Construct = Struct(
        "system_time_ns" / Int64sl,
        "command_sequence_number" / Int32ul,
        "data" / Bytes(4),
    )

    def __init__(self):
        self.system_time_ns = 0
        self.command_sequence_number = 0
        self.data = bytes()

    def pack(self, buffer: Optional[bytes] = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    def calcsize(self) -> int:
        return self.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', seq={self.command_sequence_number}, data={self.data}]'
        return result


class STA5635IQData(MessagePayload):
    """!
    @brief Wrapper for IQ Samples from a STA5635.
    """
    MESSAGE_TYPE = MessageType.STA5635_IQ_DATA
    MESSAGE_VERSION = 0

    Construct = Struct(
        Padding(4),
        # NOTE: Since this message does no capture the expected data size, the Construct relies on the size of the
        # Python buffer passed to `unpack`` to infer the size of the data. This is the behavior of @ref GreedyBytes.
        "data" / GreedyBytes
    )

    def __init__(self):
        self.data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        ret = MessagePayload.pack(self, buffer, offset, return_buffer)
        return ret

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        ret = MessagePayload.unpack(self, buffer, offset, message_version)
        return ret

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', data_len={len(self.data)}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.Construct,
                                           value_to_string={
                                               'data': lambda x: f'{len(x)} B payload',
                                           },
                                           title=f'IQ Samples')

    def calcsize(self) -> int:
        return len(self.pack())
