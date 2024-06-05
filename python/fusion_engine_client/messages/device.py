import math
import string

from construct import Struct, this, Padding, PaddedString, Bytes, Int64ul, Int16ul, Int16sl
import numpy as np

from ..utils.construct_utils import AutoEnum, FixedPointAdapter, construct_message_to_string
from ..utils.enum_utils import IntEnum
from .defs import *


class VersionInfoMessage(MessagePayload):
    """!
    @brief Software and hardware version information.
    """
    MESSAGE_TYPE = MessageType.VERSION_INFO
    MESSAGE_VERSION = 0

    VersionInfoMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        "fw_version_length" / Int8ul,
        "engine_version_length" / Int8ul,
        "os_version_length" / Int8ul,
        "rx_version_length" / Int8ul,
        Padding(4),
        "fw_version_str" / PaddedString(this.fw_version_length, 'utf8'),
        "engine_version_str" / PaddedString(this.engine_version_length, 'utf8'),
        "os_version_str" / PaddedString(this.os_version_length, 'utf8'),
        "rx_version_str" / PaddedString(this.rx_version_length, 'utf8'),
    )

    def __init__(self):
        self.system_time_ns = 0
        self.fw_version_str = ""
        self.engine_version_str = ""
        self.os_version_str = ""
        self.rx_version_str = ""

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['fw_version_length'] = len(self.fw_version_str)
        values['engine_version_length'] = len(self.engine_version_str)
        values['os_version_length'] = len(self.os_version_str)
        values['rx_version_length'] = len(self.rx_version_str)
        packed_data = self.VersionInfoMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.VersionInfoMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', fw={self.fw_version_str}, engine={self.engine_version_str}, os={self.os_version_str} ' \
                  f'rx={self.rx_version_str}]'
        return result

    def __str__(self):
        string = f'Version Info @ %s\n' % system_time_to_str(self.system_time_ns)
        string += f'  Firmware: {self.fw_version_str}\n'
        string += f'  FusionEngine: {self.engine_version_str}\n'
        string += f'  OS: {self.os_version_str}\n'
        string += f'  GNSS receiver: {self.rx_version_str}'
        return string

    def calcsize(self) -> int:
        return len(self.pack())


class DeviceType(IntEnum):
    UNKNOWN = 0
    ATLAS = 1
    LG69T_AM = 2
    LG69T_AP = 3
    LG69T_AH = 4
    NEXAR_BEAM2K = 5,
    SSR_LG69T = 6,
    SSR_DESKTOP = 7,


class DeviceIDMessage(MessagePayload):
    """!
    @brief Device identifiers.
    """
    MESSAGE_TYPE = MessageType.DEVICE_ID
    MESSAGE_VERSION = 0
    _PRINTABLE_CHARS = bytes(string.printable, 'ascii')

    DeviceIDMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        "device_type" / AutoEnum(Int8ul, DeviceType),
        "hw_id_length" / Int8ul,
        "user_id_length" / Int8ul,
        "receiver_id_length" / Int8ul,
        Padding(4),
        "hw_id_data" / Bytes(this.hw_id_length),
        "user_id_data" / Bytes(this.user_id_length),
        "receiver_id_data" / Bytes(this.receiver_id_length),
    )

    def __init__(self):
        self.system_time_ns = 0
        self.device_type = DeviceType.UNKNOWN
        self.hw_id_data = b""
        self.user_id_data = b""
        self.receiver_id_data = b""

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['hw_id_length'] = len(self.hw_id_length)
        values['user_id_length'] = len(self.user_id_length)
        values['receiver_id_length'] = len(self.receiver_id_length)
        packed_data = self.DeviceIDMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.DeviceIDMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    @staticmethod
    def _get_str(msg: bytes) -> str:
        is_printable = all(b in DeviceIDMessage._PRINTABLE_CHARS for b in msg)
        if is_printable:
            return msg.decode('ascii')
        else:
            return '[' + ' '.join(f'{b:02X}' for b in msg) + ']'

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f'type={self.device_type}, hw={self._get_str(self.hw_id_data)}, user={self._get_str(self.user_id_data)},\
            rx={self._get_str(self.receiver_id_data)}'
        return result

    def __str__(self):
        string = f'Device ID Info @ %s\n' % system_time_to_str(self.system_time_ns)
        string += f'  Device Type: {self.device_type}\n'
        string += f'  HW ID: {self._get_str(self.hw_id_data)}\n'
        string += f'  User ID: {self._get_str(self.user_id_data)}\n'
        string += f'  Receiver ID: {self._get_str(self.receiver_id_data)}'
        return string

    def calcsize(self) -> int:
        return len(self.pack())


class EventType(IntEnum):
    LOG = 0
    RESET = 1
    CONFIG_CHANGE = 2
    COMMAND = 3
    COMMAND_RESPONSE = 4


class EventNotificationMessage(MessagePayload):
    """!
    @brief Notification of a system event for logging purposes.
    """
    MESSAGE_TYPE = MessageType.EVENT_NOTIFICATION
    MESSAGE_VERSION = 0

    EventNotificationConstruct = Struct(
        "event_type" / AutoEnum(Int8ul, EventType),
        Padding(3),
        "system_time_ns" / Int64ul,
        "event_flags" / Int64ul,
        "event_description_len_bytes" / Int16ul,
        Padding(2),
        "event_description" / Bytes(this.event_description_len_bytes),
    )

    def __init__(self):
        self.event_type = EventType.LOG
        self.system_time_ns = 0
        self.event_flags = 0
        self.event_description = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['event_description_len_bytes'] = len(self.event_description)
        if isinstance(self.event_description, str):
            values['event_description'] = self.event_description.encode('utf-8')
        packed_data = self.EventNotificationConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.EventNotificationConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)

        # For logged FusionEngine commands/responses, the device intentionally offsets the preamble by 0x0101 from
        # 0x2E31 ('.1') to 0x2F32 ('/2'). That way, the encapsulated messages within the event messages don't get
        # parsed, but we can still identify them. We'll undo that offset here so the content in self.event_description
        # reflects the original command/response.
        if (self.event_type == EventType.COMMAND or self.event_type == EventType.COMMAND_RESPONSE) and \
           len(self.event_description) >= 2 and (self.event_description[:2] == b'/2'):
            self.event_description = bytearray(self.event_description)
            self.event_description[0] -= 1
            self.event_description[1] -= 1

        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', type={self.event_type}, flags=0x{self.event_flags:X}'
        if self.event_type == EventType.COMMAND or self.event_type == EventType.COMMAND_RESPONSE:
            result += f', data={len(self.event_description)} B'
        else:
            result += f', description={self.event_description}'
        result += ']'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.EventNotificationConstruct,
            title=f'Event Notification @ %s' % system_time_to_str(self.system_time_ns),
            fields=['event_type', 'event_flags', 'event_description'],
            value_to_string={
                'event_flags': lambda x: '0x%016X' % x,
                'event_description': lambda x: self.event_description_to_string(),
            })

    def calcsize(self) -> int:
        return len(self.pack())

    def event_description_to_string(self, max_bytes=None):
        # For commands and responses, the payload should contain the binary FusionEngine message. Try to decode the
        # message type.
        if self.event_type == EventType.COMMAND or self.event_type == EventType.COMMAND_RESPONSE:
            if len(self.event_description) >= MessageHeader.calcsize():
                header = MessageHeader()
                header.unpack(self.event_description, validate_crc=False, warn_on_unrecognized=False)
                message_repr = f'[{header.message_type.to_string(include_value=True)}]'

                message_cls = MessagePayload.get_message_class(header.message_type)
                if message_cls is not None:
                    try:
                        message = message_cls()
                        message.unpack(buffer=self.event_description, offset=header.calcsize())
                        message_repr = repr(message)
                    except ValueError as e:
                        pass
            else:
                message_repr = '<Malformed>'

            return "%s\n%s" % (message_repr,
                               self._populate_data_byte_string(self.event_description, max_bytes=max_bytes))
        elif isinstance(self.event_description, str):
            return self.event_description
        else:
            try:
                return self.event_description.decode('utf-8')
            except UnicodeDecodeError:
                return repr(self.event_description)

    @classmethod
    def to_numpy(cls, messages: Sequence['EventNotificationMessage']):
        result = {
            'system_time': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'event_type': np.array([int(m.event_type) for m in messages], dtype=int),
            'event_flags': np.array([int(m.event_flags) for m in messages], dtype=np.uint64),
        }
        return result

    @classmethod
    def _populate_data_byte_string(cls, data: bytes, max_bytes: int = None):
        data_truncated = data if max_bytes is None else data[:max_bytes]
        suffix = '' if len(data_truncated) == len(data) else '...'
        return f'Data ({len(data)} B): {" ".join("%02X" % b for b in data_truncated)}{suffix}'


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
System Status Message @ {self.p1_time}
  GNSS Temperature: {self.gnss_temperature_degc:.1f} deg C"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'gnss_temperature_degc': np.array([m.gnss_temperature_degc for m in messages]),
        }
        return result
