from enum import IntEnum
from typing import NamedTuple

from construct import (Struct, Enum, Int64ul, Int32ul, Int16ul,
                       Int8ul, Padding, this, Flag, Bytes)

from ...utils.construct_utils import NamedTupleAdapter
from .internal_defs import *


class MessageRequest(MessagePayload):
    """!
    @brief Transmission request for a specified message type.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_REQ
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


class ResetMessage(MessagePayload):
    """!
    @brief Reset part/all of the device software.
    """
    MESSAGE_TYPE = MessageType.RESET_CMD
    MESSAGE_VERSION = 1

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
    ## Reset the navigation engine's estimate of position, velocity, and
    ## orientation.
    RESET_POSITION_DATA = 0x00000100
    ## Delete all saved satellite ephemeris.
    RESET_EPHEMERIS = 0x00000200
    ## @}

    ##
    # @name Clear Long Lived Data
    # @{
    ## Reset all stored navigation engine data, including position, velocity, and
    ## orientation state, as well as training data.
    RESET_NAVIGATION_ENGINE_DATA = 0x00001000

    ## Reset the device calibration data.
    ##
    ## @note
    ## This does _not_ reset any existing navigation engine state. It is
    ## recommended that you set @ref RESET_NAVIGATION_ENGINE_DATA as well under
    ## normal circumstances.
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

    ## Perform a device hot start: reload the navigation engine and clear all
    ## runtime data (GNSS corrections, etc.), but do not reset any saved state
    ## data (position, orientation, training parameters, calibration, etc.).
    ##
    ## A hot start is typically used to restart the navigation engine in a
    ## deterministic state, particularly for logging purposes.
    HOT_START = 0x000000FF

    ## Perform a device warm start: reload the navigation engine, resetting the
    ## saved position, velocity, and orientation, but do not reset training
    ## parameters or calibration data.
    ##
    ## A warm start is typically used to reset the device's position estimate in
    ## case of error.
    WARM_START = 0x000001FF

    ## Perform a device cold start: reset the navigation engine including saved
    ## position, velocity, and orientation state, but do not reset training data,
    ## calibration data, or user configuration parameters.
    ##
    ## @note
    ## To reset training or calibration data as well, set the @ref
    ## RESET_NAVIGATION_ENGINE_DATA and @ref RESET_CALIBRATION_DATA bits.
    COLD_START = 0x00000FFF

    ## Restart mask to set all persistent data, including calibration and user
    ## configuration, back to factory defaults.
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

        struct.pack_into(ResetMessage._FORMAT, buffer, offset,
                         self.reset_mask)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            struct.unpack_from(ResetMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ResetMessage._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return ResetMessage._SIZE


class CommandResponseMessage(MessagePayload):
    """!
    @brief Acknowledges a command and indicates if it succeeded.
    """
    MESSAGE_TYPE = MessageType.CMD_RESPONSE
    MESSAGE_VERSION = 1

    class Response(IntEnum):
        OK = 0,
        ## A version specified in the command or subcommand could not be handled. This could mean that the version was
        ## too new and not supported by the device, or it was older than the version used by the device and there was no
        ## translation for it.
        UNSUPPORTED_CMD_VERSION = 1,
        ## The command interacts with a feature that is not present on the target device (e.g., setting the baud rate on
        ## a device without a serial port).
        UNSUPPORTED_FEATURE = 2,
        ## One or more values in the command were not in acceptable ranges (e.g., an undefined enum value, or an invalid
        ## baud rate).
        VALUE_ERROR = 3,
        ## The command would require adding too many elements to internal storage.
        INSUFFICIENT_SPACE = 4,
        ## There was a runtime failure executing the command.
        EXECUTION_FAILURE = 5,

    _FORMAT = '<IB3x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.source_sequence_num = 0
        self.response = CommandResponseMessage.Response.OK

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

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return CommandResponseMessage._SIZE

    def __str__(self):
        string = f'Command Response\n'
        string += f'\tsource_sequence_num: {self.source_sequence_num}\n'
        string += f'\tresponse: {self.response}'
        return string


VersionConstructRaw = Struct(
    Padding(1),
    "major" / Int8ul,
    "minor" / Int16ul,
)


class ConfigVersion(NamedTuple):
    major: int
    minor: int


VersionConstruct = NamedTupleAdapter(ConfigVersion, VersionConstructRaw)


class ConfigurationSource(IntEnum):
    ACTIVE = 0,
    SAVED = 1


class ConfigType(IntEnum):
    INVALID = 0,
    OUTPUT_STREAM_MSGS = 1
    DEVICE_LEVER_ARM = 16
    DEVICE_COARSE_ORIENTATION = 17
    GNSS_LEVER_ARM = 18
    OUTPUT_LEVER_ARM = 19
    UART0_BAUD = 256
    UART1_BAUD = 257


class SetConfigMessage(MessagePayload):
    """!
    @brief Command to apply a config change
    """
    MESSAGE_TYPE = MessageType.SET_CONFIG_CMD
    MESSAGE_VERSION = 0

    SetConfigMessageConstruct = Struct(
        "config_type" / Enum(Int16ul, ConfigType),
        "config_version" / Int8ul,
        Padding(1),
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Bytes(this.config_change_length_bytes),
    )

    def __init__(self):
        self.config_type = ConfigType.INVALID
        self.config_version = 0
        self.config_change_length_bytes = 0
        self.config_change_data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['config_change_length_bytes'] = len(self.config_change_data)

        packed_data = self.SetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SetConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['config_type', 'config_version', "config_change_length_bytes"]
        string = f'Set Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class GetConfigMessage(MessagePayload):
    """!
    @brief Message for requesting device config data.
    """
    MESSAGE_TYPE = MessageType.GET_CONFIG_CMD
    MESSAGE_VERSION = 0

    GetConfigMessageConstruct = Struct(
        "config_type" / Enum(Int16ul, ConfigType),
        "request_source" / Enum(Int8ul, ConfigurationSource),
        Padding(1),
    )

    def __init__(self):
        self.request_source = ConfigurationSource.ACTIVE
        self.config_type = ConfigType.INVALID

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.GetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.GetConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['request_source', 'config_type']
        string = f'Get Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.GetConfigMessageConstruct.sizeof()


class ConfigurationDataMessage(MessagePayload):
    """!
    @brief Device user configuration response.
    """
    MESSAGE_TYPE = MessageType.CONF_DATA
    MESSAGE_VERSION = 0

    ConfigurationDataMessageConstruct = Struct(
        "config_source" / Enum(Int8ul, ConfigurationSource),
        "active_differs_from_saved" / Flag,
        "config_type" / Enum(Int16ul, ConfigType),
        "config_version" / Int8ul,
        Padding(3),
        "config_length_bytes" / Int32ul,
        "config_data" / Bytes(this.config_length_bytes),
    )

    def __init__(self, user_config=None):
        self.config_source = ConfigurationSource.ACTIVE
        self.active_differs_from_saved = False
        self.config_version = 0
        self.config_data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['config_length_bytes'] = len(self.config_data)
        packed_data = self.ConfigurationDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ConfigurationDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['config_type', 'config_version', 'active_differs_from_saved',
                  'config_source', 'config_length_bytes']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class SaveConfigMessage(MessagePayload):
    """!
    @brief Command to apply config change
    """
    MESSAGE_TYPE = MessageType.SAVE_CONFIG_CMD
    MESSAGE_VERSION = 0

    class Action(IntEnum):
        SAVE = 0
        REVERT_TO_SAVED = 1
        REVERT_TO_DEFAULTS = 2

    SaveConfigMessageConstruct = Struct(
        "action" / Enum(Int8ul, Action),
        Padding(3)
    )

    def __init__(self):
        self.action = self.Action.SAVE

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.SaveConfigMessageConstruct.build({"action": self.action})
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SaveConfigMessageConstruct.parse(buffer[offset:])
        self.action = parsed.action
        return parsed._io.tell()

    def __str__(self):
        fields = ['action']
        string = f'Save Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())

    @classmethod
    def calcsize(cls) -> int:
        return cls.SaveConfigMessageConstruct.sizeof()


class PlatformStorageDataMessage(MessagePayload):
    """!
    @brief Device user configuration response.
    """
    MESSAGE_TYPE = MessageType.PLATFORM_STORAGE_DATA
    MESSAGE_VERSION = 1

    PlatformStorageDataMessageConstruct = Struct(
        "data_type" / Int8ul,
        "data_validity" / Int8ul,
        Padding(2),
        "data_version" / VersionConstruct,
        "data_length_bytes" / Int32ul,
        "data" / Bytes(this.data_length_bytes),
    )

    def __init__(self, user_config=None):
        self.data_version = ConfigVersion(0, 0)
        self.data_type = 255
        self.data_validity = 0
        self.data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['data_length_bytes'] = len(self.data)
        packed_data = self.PlatformStorageDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.PlatformStorageDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['data_type', 'data_validity', 'data_version']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class EventNotificationMessage(MessagePayload):
    """!
    @brief An event notification.
    """
    MESSAGE_TYPE = MessageType.EVENT_NOTIFICATION
    MESSAGE_VERSION = 0

    class Action(IntEnum):
        LOG = 0
        RESET = 1
        CONFIG_CHANGE = 2

    EventNotificationConstruct = Struct(
        "action" / Enum(Int8ul, Action),
        Padding(3),
        "system_time_ns" / Int64ul,
        "event_flags" / Int64ul,
        "event_description_len_bytes" / Int32ul,
        "event_description" / Bytes(this.event_description_len_bytes),
    )

    def __init__(self, user_config=None):
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
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class VersionDataMessage(MessagePayload):
    """!
    @brief An event notification.
    """
    MESSAGE_TYPE = MessageType.VERSION_DATA
    MESSAGE_VERSION = 0

    VersionDataMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        "fw_version_length" / Int8ul,
        "engine_version_length" / Int8ul,
        "hw_version_length" / Int8ul,
        "rx_version_length" / Int8ul,
        Padding(4),
        "fw_version_str" /  Bytes(this.fw_version_length),
        "engine_version_str" /  Bytes(this.engine_version_length),
        "hw_version_str" /  Bytes(this.hw_version_length),
        "rx_version_str" /  Bytes(this.rx_version_length),
    )

    def __init__(self, user_config=None):
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
        packed_data = self.VersionDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.VersionDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['system_time_ns', 'fw_version_str', 'engine_version_str', 'hw_version_str', 'rx_version_str']
        string = f'Version Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
