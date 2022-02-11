from enum import IntEnum
from typing import NamedTuple

from construct import (Struct, Int32ul, Int16ul, Int8ul, Padding, this, Bytes)

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
        string = f'Platform Storage Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
