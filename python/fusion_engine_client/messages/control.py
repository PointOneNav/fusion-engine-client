import string
import struct

from construct import (Struct, Int64ul, Int16ul, Int8ul, Padding, this, Bytes, PaddedString)

from ..utils.construct_utils import AutoEnum, construct_message_to_string
from ..utils.enum_utils import IntEnum
from .defs import *


class CommandResponseMessage(MessagePayload):
    """!
    @brief Response to indicate if command was processed successfully.
    """
    MESSAGE_TYPE = MessageType.COMMAND_RESPONSE
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<IB3x')

    def __init__(self):
        self.source_sequence_num = 0
        self.response = Response.OK

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        self._STRUCT.pack_into(buffer, offset, self.source_sequence_num, self.response)
        offset = self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (self.source_sequence_num, self.response) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset = self._STRUCT.size

        try:
            self.response = Response(self.response)
        except ValueError:
            pass

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', response={self.response}, seq_num={self.source_sequence_num}]'
        return result

    def __str__(self):
        string = f'Command Response\n'
        string += f'  Sequence #: {self.source_sequence_num}\n'
        if isinstance(self.response, Response):
            string += f'  Response: {str(self.response)} ({int(self.response)})'
        else:
            string += f'  Response: UNKNOWN ({int(self.response)})'
        return string


class MessageRequest(MessagePayload):
    """!
    @brief Request transmission of a specified message type.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_REQUEST
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<H2x')

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.message_type: MessageType = message_type

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        self._STRUCT.pack_into(buffer, offset, self.message_type.value)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (message_type,) = self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.message_type = MessageType(message_type)

        return offset - initial_offset

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', message_type={self.message_type}]'
        return result

    def __str__(self):
        return 'Transmission request for message %s.' % MessageType.get_type_string(self.message_type)

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size


class ResetRequest(MessagePayload):
    """!
    @brief Perform a software or hardware reset.
    """
    MESSAGE_TYPE = MessageType.RESET_REQUEST
    MESSAGE_VERSION = 0

    ##
    # @name Runtime State Reset
    # @{
    ## Restart the navigation engine, but do not clear its position estimate.
    RESTART_NAVIGATION_ENGINE = 0x00000001
    ## Delete all GNSS corrections information.
    RESET_GNSS_CORRECTIONS = 0x00000002
    ## @}

    ##
    # @name Clear Short Lived Data
    # @{
    ## Reset the navigation engine's estimate of position, velocity, and orientation.
    RESET_POSITION_DATA = 0x00000100
    ## Delete all saved satellite ephemeris.
    RESET_EPHEMERIS = 0x00000200
    ## Reset bias estimates, and other IMU corrections that are typically estimated quickly.
    RESET_FAST_IMU_CORRECTIONS = 0x00000400
    ## @}

    ##
    # @name Clear Long Lived Data
    # @{
    ##
    # Reset all stored navigation engine data, including position, velocity, and orientation state (same as @ref
    # RESET_POSITION_DATA), plus all IMU corrections and other training data.
    RESET_NAVIGATION_ENGINE_DATA = 0x00001000

    ##
    # Reset the device calibration data.
    #
    # @note
    # This does _not_ reset any existing navigation engine state. It is recommended that you set @ref
    # RESET_NAVIGATION_ENGINE_DATA as well under normal circumstances.
    RESET_CALIBRATION_DATA = 0x00002000
    ## @}

    ##
    # @name Clear Configuration Data
    # @{
    ## Clear all configuration data.
    RESET_CONFIG = 0x00100000
    ## @}

    ##
    # @name Software Reboot And Special Reset Modes
    # @{
    ##
    # Reboot the GNSS measurement engine (GNSS receiver), in addition to
    # performing any other requested resets (e.g., @ref RESET_EPHEMERIS). If no
    # other resets are specified, the GNSS receiver will reboot and should
    # perform a hot start.
    REBOOT_GNSS_MEASUREMENT_ENGINE = 0x01000000
    ## Reboot the navigation processor.
    REBOOT_NAVIGATION_PROCESSOR = 0x02000000
    ##
    # Perform a diagnostic log reset to guarantee deterministic performance for
    # data post-processing and diagnostic support.
    #
    # Diagnostic log resets are useful when capturing data to be sent to Point
    # One for analysis and support. Performing a diagnostic reset guarantees that
    # the performance of the device seen in real time can be reproduced during
    # post-processing.
    #
    # This reset performs the following:
    # - Restart the navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - Clear any stored data in RAM that was received since startup such as
    #   ephemeris or GNSS corrections
    #   - This is _not_ the same as @ref RESET_EPHEMERIS; this action does not
    #     reset ephemeris data stored in persistent storage
    # - Flush internal data buffers on the device
    #
    # Note that this does _not_ reset the navigation engine's position data,
    # training parameters, or calibration. If the navigation engine has existing
    # position information, it will be used.
    #
    # This reset may be combined with other resets as needed to clear additional
    # information.
    DIAGNOSTIC_LOG_RESET = 0x04000000
    ## @}

    ##
    # @name Device Reset Bitmasks
    # @{

    ##
    # Perform a device hot start.
    #
    # This will reset the navigation engine into a known state, using previously
    # stored position and time information. The device will begin navigating
    # immediately if possible.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    #
    # Not reset/performed:
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    HOT_START = 0x00000001

    ##
    # Perform a device warm start.
    #
    # During a warm start, the device retains its knowledge of approximate
    # position and time, plus almanac data if available, but resets all ephemeris
    # data. As a result, the device will need to download ephemeris data before
    # continuing to navigate with GNSS.
    #
    # To be reset:
    # - The navigation engine (i.e., perform a hot start, @ref
    #   RESTART_NAVIGATION_ENGINE)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    #
    # Not reset/performed:
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    WARM_START = 0x00000201

    ##
    # Perform a PVT reset: reset all position, velocity, orientation, and time
    # information (i.e., the navigation engine's kinematic state).
    #
    # A PVT reset is typically used to reset the kinematic portion of the
    # navigation engine's state if you are experiencing errors on startup or
    # after a @ref HOT_START.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    #
    # Not reset/performed:
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    PVT_RESET = 0x000001FF

    ##
    # Perform a device cold start.
    #
    # A cold start is typically used to reset the device's state estimate in the
    # case of error that cannot be resolved by a @ref WARM_START.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - GNSS ephemeris data (@ref RESET_EPHEMERIS)
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    #
    # Not reset/performed:
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    # - Reboot GNSS measurement engine (@ref REBOOT_GNSS_MEASUREMENT_ENGINE)
    # - Reboot navigation processor (@ref REBOOT_NAVIGATION_PROCESSOR)
    #
    # @note
    # To reset training or calibration data as well, set the @ref
    # RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
    COLD_START = 0x00000FFF

    ##
    # Restart mask to set all persistent data, including calibration and user configuration, back to factory defaults.
    FACTORY_RESET = 0xFFFFFFFF

    ## @}

    _STRUCT = struct.Struct('<I')

    def __init__(self, reset_mask: int = 0):
        self.reset_mask = reset_mask

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        self._STRUCT.pack_into(buffer, offset, self.reset_mask)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', mask=0x{self.reset_mask:08X}]'
        return result

    def __str__(self):
        return 'Reset Request [mask=0x%08x]' % self.reset_mask


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
    def _populate_data_byte_string(cls, data: bytes, max_bytes: int = None):
        data_truncated = data if max_bytes is None else data[:max_bytes]
        suffix = '' if len(data_truncated) == len(data) else '...'
        return f'Data ({len(data)} B): {" ".join("%02X" % b for b in data_truncated)}{suffix}'


class ShutdownRequest(MessagePayload):
    """!
    @brief Perform a device shutdown.
    """
    MESSAGE_TYPE = MessageType.SHUTDOWN_REQUEST
    MESSAGE_VERSION = 0

    ShutdownRequestConstruct = Struct(
        "shutdown_flags" / Int64ul,
        Padding(8),
    )

    def __init__(self, shutdown_flags = 0):
        self.shutdown_flags = shutdown_flags

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.ShutdownRequestConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.ShutdownRequestConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', flags=0x{self.shutdown_flags:016X}]'
        return result

    def __str__(self):
        return 'Shutdown Request [flags=0x%016x]' % self.shutdown_flags

    def calcsize(self) -> int:
        return self.ShutdownRequestConstruct.sizeof()


class StartupRequest(MessagePayload):
    """!
    @brief Perform a device startup.
    """
    MESSAGE_TYPE = MessageType.STARTUP_REQUEST
    MESSAGE_VERSION = 0

    StartupRequestConstruct = Struct(
        "startup_flags" / Int64ul,
        Padding(8),
    )

    def __init__(self, startup_flags = 0):
        self.startup_flags = startup_flags

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = vars(self)
        packed_data = self.StartupRequestConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.StartupRequestConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', flags=0x{self.startup_flags:016X}]'
        return result

    def __str__(self):
        return 'Startup Request [flags=0x%016x]' % self.startup_flags

    def calcsize(self) -> int:
        return self.StartupRequestConstruct.sizeof()
