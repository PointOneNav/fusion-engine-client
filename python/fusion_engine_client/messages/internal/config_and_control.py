from enum import IntEnum

from .internal_defs import *

from construct import (Struct, Enum, Int32ul, Int16ul,
                       Int8ul, Padding, this, Array, Flag)


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
    MESSAGE_VERSION = 0

    RESET_NAVIGATION = 0x00000001
    RESET_EPHEMERIS = 0x00000002
    RESET_CORRECTIONS = 0x00000004
    RESET_SOFTWARE = 0x00FFFFFF

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


VersionConstruct = Struct(
    Padding(1),
    "major" / Int8ul,
    "minor" / Int16ul,
)


UserConfigConstruct = Struct(
    "thing1" / Int8ul,
    Padding(3),
    "thing2" / Int32ul,
    "thing3" / Int32ul,
)


USER_CONFIG_VERSION = {"major": 1, "minor": 0}


class QueueConfigParamMessage(MessagePayload):
    """!
    @brief Command to queue config change
    """
    MESSAGE_TYPE = MessageType.QUEUE_CONFIG_PARAM_CMD
    MESSAGE_VERSION = 0

    QueueConfigParamMessageConstruct = Struct(
        "config_version" / VersionConstruct,
        "config_change_offset" / Int32ul,
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Array(this.config_change_length_bytes, Int8ul),
    )

    def __init__(self, user_config=None):
        self.config_version = USER_CONFIG_VERSION
        self.config_change_offset = 0
        if user_config:
            self.config_change_data = UserConfigConstruct.build(user_config)
        else:
            self.config_change_data = []

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


class ConfigRequestMessage(MessagePayload):
    """!
    @brief Base class for requesting device config data.
    """

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        return PackedDataToBuffer(bytes(0), buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        return 0

    @classmethod
    def calcsize(cls) -> int:
        return 0


class ActiveConfigRequestMessage(ConfigRequestMessage):
    """!
    @brief Request active config.
    """
    MESSAGE_TYPE = MessageType.ACTIVE_CONF_REQ
    MESSAGE_VERSION = 0


class QueuedConfigRequestMessage(ConfigRequestMessage):
    """!
    @brief Request queued config.
    """
    MESSAGE_TYPE = MessageType.QUEUED_CONF_REQ
    MESSAGE_VERSION = 0


class SavedConfigRequestMessage(ConfigRequestMessage):
    """!
    @brief Request saved config.
    """
    MESSAGE_TYPE = MessageType.SAVED_CONF_REQ
    MESSAGE_VERSION = 0


class ConfigurationDataMessage(MessagePayload):
    """!
    @brief Device user configuration response.
    """
    MESSAGE_TYPE = MessageType.CONF_DATA
    MESSAGE_VERSION = 0

    class Source(IntEnum):
        ACTIVE = 0,
        QUEUED = 1,
        SAVED = 2,

    ConfigurationDataMessageConstruct = Struct(
        "config_version" / VersionConstruct,
        "queued_changes" / Flag,
        "active_differs_from_saved" / Flag,
        "config_source" / Enum(Int8ul, Source),
        Padding(1),
        "config_data" / UserConfigConstruct,
    )

    def __init__(self, user_config=None):
        self.config_version = USER_CONFIG_VERSION
        self.queued_changes = False
        self.active_differs_from_saved = False
        self.config_source = self.Source.ACTIVE
        self.config_data = {"thing1": 0, "thing2": 0, "thing3": 0}

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.ConfigurationDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ConfigurationDataMessageConstruct.parse(buffer[offset:])
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
