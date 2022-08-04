from enum import IntEnum
from typing import NamedTuple

from construct import (Struct, Int32ul, Int16ul, Int8ul, Padding, this, Bytes)

from ...utils.construct_utils import AutoEnum, NamedTupleAdapter
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


class DataType(IntEnum):
    CALIBRATION_STATE = 0
    CRASH_LOG = 1
    FILTER_STATE = 2
    USER_CONFIG = 3

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


class DataValidity(IntEnum):
    UNKNOWN = 0
    NO_DATA_STORED = 1
    DATA_VALID = 2
    DATA_CORRUPTED = 3

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


class PlatformStorageDataMessage(MessagePayload):
    """!
    @brief Device user configuration response.
    """
    MESSAGE_TYPE = MessageType.PLATFORM_STORAGE_DATA
    MESSAGE_VERSION = 1

    PlatformStorageDataMessageConstruct = Struct(
        "data_type" / AutoEnum(Int8ul, DataType),
        "data_validity" / AutoEnum(Int8ul, DataValidity),
        Padding(2),
        "data_version" / VersionConstruct,
        "data_length_bytes" / Int32ul,
        "data" / Bytes(this.data_length_bytes),
    )

    def __init__(self, user_config=None):
        self.data_version = ConfigVersion(0, 0)
        self.data_type = DataType.CALIBRATION_STATE
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
        fields = ['data_validity', 'data_version']
        string = f'Platform Storage Data ({str(self.data_type)}, {len(self.data)} B)\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
