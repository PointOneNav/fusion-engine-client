from enum import IntEnum

from construct import (Struct, Int64ul, Int16ul, Int8ul, Padding, this, Bytes, PaddedString)

from ..utils.construct_utils import AutoEnum
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

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
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

    def __str__(self):
        string = f'Command Response\n'
        string += f'  Sequence number: {self.source_sequence_num}\n'
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

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (message_type,) = self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT._SIZE

        self.message_type = MessageType(message_type)

        return offset - initial_offset

    def __repr__(self):
        return '%s' % self.MESSAGE_TYPE.name

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
    # Reset all stored navigation engine data, including position, velocity, and orientation state, as well as all IMU
    # corrections (fast and slow) and other training data.
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
    # @name Device Reset Bitmasks
    # @{

    ##
    # Perform a device hot start.
    #
    # A hot start is typically used to restart the navigation engine in a
    # deterministic state, particularly for logging purposes.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    #
    # Not reset:
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    HOT_START = 0x000000FF

    ##
    # Perform a device warm start.
    #
    # A warm start is typically used to reset the device's estimate of position
    # and kinematic state in case of error.
    #
    # To be reset:
    # - The navigation engine (@ref RESTART_NAVIGATION_ENGINE)
    # - All runtime data (GNSS corrections (@ref RESET_GNSS_CORRECTIONS), etc.)
    # - Position, velocity, orientation (@ref RESET_POSITION_DATA)
    #
    # Not reset:
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    WARM_START = 0x000001FF

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
    # - Fast IMU corrections (@ref RESET_FAST_IMU_CORRECTIONS)
    #
    # Not reset:
    # - Training parameters (slowly estimated IMU corrections, temperature
    #   compensation, etc.; @ref RESET_NAVIGATION_ENGINE_DATA)
    # - Calibration data (@ref RESET_CALIBRATION_DATA)
    # - User configuration settings (@ref RESET_CONFIG)
    #
    # @note
    # To reset training or calibration data as well, set the @ref
    # RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
    COLD_START = 0x00000FFF

    ##
    # Restart mask to set all persistent data, including calibration and user configuration, back to factory defaults.
    #
    # Note: Upper 8 bits reserved for future use (e.g., hardware reset).
    FACTORY_RESET = 0x00FFFFFF

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

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += ResetRequest._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size

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
        "hw_version_length" / Int8ul,
        "rx_version_length" / Int8ul,
        Padding(4),
        "fw_version_str" / PaddedString(this.fw_version_length, 'utf8'),
        "engine_version_str" / PaddedString(this.engine_version_length, 'utf8'),
        "hw_version_str" / PaddedString(this.hw_version_length, 'utf8'),
        "rx_version_str" / PaddedString(this.rx_version_length, 'utf8'),
    )

    def __init__(self):
        self.system_time_ns = 0
        self.fw_version_str = ""
        self.engine_version_str = ""
        self.hw_version_str = ""
        self.rx_version_str = ""

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['fw_version_length'] = len(self.fw_version_str)
        values['engine_version_length'] = len(self.engine_version_str)
        values['hw_version_length'] = len(self.hw_version_str)
        values['rx_version_length'] = len(self.rx_version_str)
        packed_data = self.VersionInfoMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.VersionInfoMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        string = f'Version Info @ %s\n' % system_time_to_str(self.system_time_ns)
        string += f'  Firmware: {self.fw_version_str}\n'
        string += f'  FusionEngine: {self.engine_version_str}\n'
        string += f'  Hardware: {self.hw_version_str}\n'
        string += f'  GNSS receiver: {self.rx_version_str}'
        return string

    def calcsize(self) -> int:
        return len(self.pack())


class EventNotificationMessage(MessagePayload):
    """!
    @brief Notification of a system event for logging purposes.
    """
    MESSAGE_TYPE = MessageType.EVENT_NOTIFICATION
    MESSAGE_VERSION = 0

    class Action(IntEnum):
        LOG = 0
        RESET = 1
        CONFIG_CHANGE = 2

        def __str__(self):
            return super().__str__().replace(self.__class__.__name__ + '.', '')

    EventNotificationConstruct = Struct(
        "action" / AutoEnum(Int8ul, Action),
        Padding(3),
        "system_time_ns" / Int64ul,
        "event_flags" / Int64ul,
        "event_description_len_bytes" / Int16ul,
        Padding(2),
        "event_description" / Bytes(this.event_description_len_bytes),
    )

    def __init__(self):
        self.action = self.Action.LOG
        self.system_time_ns = 0
        self.event_flags = 0
        self.event_description = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['event_description_len_bytes'] = len(self.event_description)
        packed_data = self.EventNotificationConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.EventNotificationConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['action', 'event_flags', 'event_description']
        string = f'Event Notification @ %s\n' % system_time_to_str(self.system_time_ns)
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
