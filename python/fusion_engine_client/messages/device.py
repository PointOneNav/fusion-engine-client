import struct

from construct import (Struct, Int64ul, Int16ul, Int8ul, Int16sl, Padding, this, Bytes, PaddedString)

from ..utils.construct_utils import AutoEnum, construct_message_to_string
from ..utils.enum_utils import IntEnum
from .defs import *

class SystemStatusMessage(MessagePayload):
    """!
    @brief System status elements.
    """
    MESSAGE_TYPE = MessageType.SYSTEM_STATUS
    MESSAGE_VERSION = 0

    INVALID_TEMPERATURE = -32768

    SystemStatusMessageConstruct = Struct(
        "p1_time" / TimestampConstruct,
        "gnss_temperature" / Int16sl,
        Padding(131),
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.gnss_temperature = SystemStatusMessage.INVALID_TEMPERATURE

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.SystemStatusMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.SystemStatusMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gnss_temperature={self.gnss_temperature}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, title='System Status')

    def calcsize(self) -> int:
        return self.SystemStatusMessageConstruct.sizeof()
