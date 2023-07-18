import math

from construct import (Struct, Float32l, Int8ul, Int16ul, Int64sl, Padding, Bytes, this)

from ..utils.construct_utils import construct_message_to_string
from .defs import *


class LBandFrameMessage(MessagePayload):
    """!
    @brief L-band frame message.
    """
    MESSAGE_TYPE = MessageType.LBAND_FRAME
    MESSAGE_VERSION = 0

    LBandFrameMessageConstruct = Struct(
        "system_time_ns" / Int64sl,
        "user_data_size_bytes" / Int16ul,
        "bit_error_count" / Int16ul,
        "signal_power_db" / Int8ul,
        Padding(3),
        "doppler_hz" / Float32l,
        "data_payload" / Bytes(this.user_data_size_bytes),
    )

    def __init__(self):
        self.system_time_ns = 0
        self.bit_error_count = 0
        self.signal_power_db = 0
        self.doppler_hz = math.nan
        self.data_payload = bytes()

    def pack(self, buffer: Optional[bytes] = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        values['user_data_size_bytes'] = len(self.data_payload)
        packed_data = self.LBandFrameMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.LBandFrameMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        del self.__dict__['user_data_size_bytes']
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', errors={self.bit_error_count}, power={self.signal_power_db}, doppler={self.doppler_hz}]'
        return result

    def __str__(self):
        string = f'L-band Frame @ %s\n' % system_time_to_str(self.system_time_ns)
        string += f'  Bit Error Count: {self.bit_error_count}\n'
        string += f'  Signal Power: {self.signal_power_db} dB\n'
        string += f'  Doppler: {self.doppler_hz} Hz'
        return string

    def calcsize(self) -> int:
        return len(self.pack())
