from enum import IntEnum
from typing import NamedTuple

from construct import (Struct, Enum, Int32ul, Int16ul,
                       Int8ul, Padding, this, Flag, Bytes)

from ...utils.construct_utils import NamedTupleAdapter
from .internal_defs import *


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
