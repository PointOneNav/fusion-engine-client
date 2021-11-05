from enum import IntEnum
from typing import NamedTuple

from construct import (Struct, Enum, Int32ul, Int16ul,
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

    ## @}

    ##
    # @name Clear Short Lived Data
    # @{

    ## Reset the navigation engine's estimate of position, velocity, and orientation.
    RESET_POSITION_DATA = 0x00000010
    ## Delete all saved ephemeris.
    RESET_EPHEMERIS = 0x00000020
    ## Delete all corrections information.
    RESET_CORRECTIONS = 0x00000040

    ## @}

    ##
    # @name Clear Long Lived Data
    # @{

    ## Reset all stored navigation engine data.
    RESET_NAVIGATION_ENGINE_DATA = 0x00000100
    ## Delete calibration state.
    RESET_CALIBRATION_DATA = 0x00000200

    ## @}

    ##
    # @name Clear Configuration Data
    # @{

    ## Clears configuration back to default.
    RESET_CONFIG = 0x00001000

    ## @}

    ## Restart mask recommended for typical usage.
    RESET_SOFTWARE = 0x000000FF

    ## Restart mask to set all persistent data back to factry defaults.
    ## Note: Upper 8 bits reserved for future use (e.g., hardware reset).
    FACTORY_RESET = 0x00FFFFFF

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
    MESSAGE_VERSION = 0

    class Response(IntEnum):
        OK = 0,
        ERROR = 1

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


class QueueConfigParamMessage(MessagePayload):
    """!
    @brief Command to queue config change
    """
    MESSAGE_TYPE = MessageType.QUEUE_CONFIG_PARAM_CMD
    MESSAGE_VERSION = 0

    QueueConfigParamMessageConstruct = Struct(
        "config_version" / VersionConstruct,
        "config_change_offset_bytes" / Int32ul,
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Bytes(this.config_change_length_bytes),
    )

    def __init__(self):
        self.config_version = ConfigVersion(0, 0)
        self.config_change_offset_bytes = 0
        self.config_change_data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['config_change_length_bytes'] = len(self.config_change_data)

        packed_data = QueueConfigParamMessage.QueueConfigParamMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = QueueConfigParamMessage.QueueConfigParamMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def calcsize(self) -> int:
        return len(self.pack())


class ApplyConfigMessage(MessagePayload):
    """!
    @brief Command to apply config change
    """
    MESSAGE_TYPE = MessageType.APPLY_CONFIG_CMD
    MESSAGE_VERSION = 0

    class Action(IntEnum):
        APPLY = 0,
        APPLY_AND_SAVE = 1,
        CLEAR_QUEUED = 2,
        RELOAD_FROM_SAVED = 3,

    ApplyConfigMessageConstruct = Struct(
        "action" / Enum(Int8ul, Action),
        Padding(3)
    )

    def __init__(self):
        self.action = self.Action.APPLY

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.ApplyConfigMessageConstruct.build({"action": self.action})
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ApplyConfigMessageConstruct.parse(buffer[offset:])
        self.action = parsed.action
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.ApplyConfigMessageConstruct.sizeof()


class ConfigurationSource(IntEnum):
    ACTIVE = 0,
    QUEUED = 1,
    SAVED = 2,


class ConfigurationDataMessage(MessagePayload):
    """!
    @brief Device user configuration response.
    """
    MESSAGE_TYPE = MessageType.CONF_DATA
    MESSAGE_VERSION = 0

    ConfigurationDataMessageConstruct = Struct(
        "config_version" / VersionConstruct,
        "queued_changes" / Flag,
        "active_differs_from_saved" / Flag,
        "saved_data_corrupted" / Flag,
        "config_source" / Enum(Int8ul, ConfigurationSource),
        "config_length_bytes" / Int32ul,
        "config_data" / Bytes(this.config_length_bytes),
    )

    def __init__(self, user_config=None):
        self.config_version = ConfigVersion(0, 0)
        self.queued_changes = False
        self.active_differs_from_saved = False
        self.saved_data_corrupted = False
        self.config_source = ConfigurationSource.ACTIVE
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
        fields = ['config_version', 'queued_changes', 'active_differs_from_saved',
                  'saved_data_corrupted', 'config_source']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.ConfigurationDataMessageConstruct.sizeof()


class ConfigRequestMessage(MessagePayload):
    """!
    @brief Base class for requesting device config data.
    """
    MESSAGE_TYPE = MessageType.CONF_REQ
    MESSAGE_VERSION = 0

    ConfigRequestMessageConstruct = Struct(
        "request_source" / Enum(Int8ul, ConfigurationSource),
        Padding(3),
    )

    def __init__(self):
        self.request_source = ConfigurationSource.ACTIVE

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.ConfigRequestMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ConfigRequestMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['config_version', 'queued_changes', 'active_differs_from_saved', 'config_source', 'config_data']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.ConfigurationDataMessageConstruct.sizeof()
