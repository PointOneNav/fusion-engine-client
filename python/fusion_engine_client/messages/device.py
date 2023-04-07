import math

from construct import (Struct, Int16sl, Padding)

from ..utils.construct_utils import FixedPointAdapter, construct_message_to_string
from .defs import *


class SystemStatusMessage(MessagePayload):
    """!
    @brief System status message.
    """
    MESSAGE_TYPE = MessageType.SYSTEM_STATUS
    MESSAGE_VERSION = 0

    SystemStatusMessageConstruct = Struct(
        "p1_time" / TimestampConstruct,
        "gnss_temperature_degc" / FixedPointAdapter(2 ** -7, Int16sl, invalid=0x7FFF),
        Padding(118),
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.gnss_temperature_degc = math.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.SystemStatusMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.SystemStatusMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gnss_temperature={self.gnss_temperature_degc:.1f} deg C]'
        return result

    def __str__(self):
        string = 'System Status Message @ %s\n' % str(self.p1_time)
        string += f'  GNSS Temperature: %.1f deg C' % self.gnss_temperature_degc
        return string

    def calcsize(self) -> int:
        return self.SystemStatusMessageConstruct.sizeof()
