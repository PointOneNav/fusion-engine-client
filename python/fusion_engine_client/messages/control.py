from enum import IntEnum

from construct import (Struct, Int64ul, Int16ul, Int8ul, Padding, this, Bytes)

from ..utils.construct_utils import AutoEnum
from .defs import *


class CommandResponseMessage(MessagePayload):
    """!
    @brief Response to indicate if command was processed successfully.
    """
    MESSAGE_TYPE = MessageType.COMMAND_RESPONSE
    MESSAGE_VERSION = 0

    _FORMAT = '<IB3x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.source_sequence_num = 0
        self.response = Response.OK

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(CommandResponseMessage._FORMAT, buffer, offset,
                         self.source_sequence_num, self.response)
        offset = CommandResponseMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.source_sequence_num, self.response) = \
            struct.unpack_from(CommandResponseMessage._FORMAT, buffer=buffer, offset=offset)
        offset = CommandResponseMessage._SIZE

        try:
            self.response = Response(self.response)
        except ValueError:
            pass

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return CommandResponseMessage._SIZE

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

    _FORMAT = '<H2x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.message_type: MessageType = message_type

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(MessageRequest._FORMAT, buffer, offset, self.message_type.value)
        offset += MessageRequest._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        message_type = struct.unpack_from(MessageRequest._FORMAT, buffer=buffer, offset=offset)[0]
        offset += MessageRequest._SIZE

        self.message_type = MessageType(message_type)

        return offset - initial_offset

    def __repr__(self):
        return '%s' % self.MESSAGE_TYPE.name

    def __str__(self):
        return 'Transmission request for message %s.' % MessageType.get_type_string(self.message_type)

    @classmethod
    def calcsize(cls) -> int:
        return MessageRequest._SIZE


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
    RESET_CORRECTIONS = 0x00000002
    ## @}

    ##
    # @name Clear Short Lived Data
    # @{
    ## Reset the navigation engine's estimate of position, velocity, and orientation.
    RESET_POSITION_DATA = 0x00000100
    ## Delete all saved satellite ephemeris.
    RESET_EPHEMERIS = 0x00000200
    ## @}

    ##
    # @name Clear Long Lived Data
    # @{
    ## Reset all stored navigation engine data, including position, velocity, and orientation state, as well as training
    ## data.
    RESET_NAVIGATION_ENGINE_DATA = 0x00001000

    ## Reset the device calibration data.
    ##
    ## @note
    ## This does _not_ reset any existing navigation engine state. It is recommended that you set @ref
    ## RESET_NAVIGATION_ENGINE_DATA as well under normal circumstances.
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

    ## Perform a device hot start: reload the navigation engine and clear all runtime data (GNSS corrections, etc.), but
    ## do not reset any saved state data (position, orientation, training parameters, calibration, etc.).
    ##
    ## A hot start is typically used to restart the navigation engine in a deterministic state, particularly for logging
    ## purposes.
    HOT_START = 0x000000FF

    ## Perform a device warm start: reload the navigation engine, resetting the saved position, velocity, and
    ## orientation, but do not reset training parameters or calibration data.
    ##
    ## A warm start is typically used to reset the device's position estimate in case of error.
    WARM_START = 0x000001FF

    ## Perform a device cold start: reset the navigation engine including saved position, velocity, and orientation
    ## state, but do not reset training data, calibration data, or user configuration parameters.
    ##
    ## @note
    ## To reset training or calibration data as well, set the @ref RESET_NAVIGATION_ENGINE_DATA and @ref
    ## RESET_CALIBRATION_DATA bits.
    COLD_START = 0x00000FFF

    ## Restart mask to set all persistent data, including calibration and user configuration, back to factory defaults.
    ##
    ## Note: Upper 8 bits reserved for future use (e.g., hardware reset).
    FACTORY_RESET = 0x00FFFFFF

    ## @}

    _FORMAT = '<I'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.reset_mask = 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        struct.pack_into(ResetRequest._FORMAT, buffer, offset, self.reset_mask)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            struct.unpack_from(ResetRequest._FORMAT, buffer=buffer, offset=offset)
        offset += ResetRequest._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return ResetRequest._SIZE

    def __str__(self):
        return 'Reset request. [mask=0x%08x]' % self.reset_mask


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
        "fw_version_str" / Bytes(this.fw_version_length),
        "engine_version_str" / Bytes(this.engine_version_length),
        "hw_version_str" / Bytes(this.hw_version_length),
        "rx_version_str" / Bytes(this.rx_version_length),
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
        fields = ['system_time_ns', 'fw_version_str', 'engine_version_str', 'hw_version_str', 'rx_version_str']
        string = f'Version Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

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
        fields = ['action', 'system_time_ns', 'event_flags', 'event_description']
        string = f'Event Notification\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
