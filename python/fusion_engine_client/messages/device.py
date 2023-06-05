import math

from construct import (Struct, Int16sl, Padding)
import numpy as np

from ..utils.construct_utils import FixedPointAdapter, construct_message_to_string
from .defs import *


class SystemStatusMessage(MessagePayload):
    """!
    @brief System status message.
    """
    MESSAGE_TYPE = MessageType.SYSTEM_STATUS
    MESSAGE_VERSION = 0

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "gnss_temperature_degc" / FixedPointAdapter(2 ** -7, Int16sl, invalid=0x7FFF),
        Padding(118),
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.gnss_temperature_degc = math.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gnss_temperature={self.gnss_temperature_degc:.1f} deg C]'
        return result

    def __str__(self):
        return f"""\
System Status Message @ %{self.p1_time}
  GNSS Temperature: {self.gnss_temperature_degc:.1f} deg C"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gnss_temperature_degc': np.array([m.gnss_temperature_degc for m in messages]),
        }
        return result
