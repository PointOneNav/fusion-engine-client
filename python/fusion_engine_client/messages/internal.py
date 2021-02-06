from datetime import datetime, timezone
from enum import IntEnum
from typing import List

from aenum import extend_enum

from . import message_type_to_class
from .defs import *


class InternalMessageType(IntEnum):
    # Internal message types.
    SHUTTER_CMD = 20000
    SHUTTER = 20001
    VISION_POSE = 20002
    IMAGE_FEATURES = 20003
    CONFIG_DATA_REQ = 20004
    CONFIG_DATA = 20005
    MANIFEST_DATA_REQ = 20006
    MANIFEST_DATA = 20007

    MESSAGE_REQ = 20016

    # System profiling data
    PROFILE_SYSTEM_STATUS = 20032
    PROFILE_PIPELINE_DEFINITION = 20036
    PROFILE_PIPELINE = 20040


# Extend the message type enum with internal types.
for entry in InternalMessageType:
    extend_enum(MessageType, entry.name, entry.value)


class MessageRequest:
    """!
    @brief Transmission request for a specified message type.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_REQ

    _FORMAT = '<H2x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.message_type: MessageType = message_type

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

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


class ProfileSystemStatusMessage:
    """!
    @brief System-level profiling data.
    """
    MESSAGE_TYPE = MessageType.PROFILE_SYSTEM_STATUS

    _FORMAT = '<qQ'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.posix_time_ns = 0
        self.used_memory_bytes = 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(ProfileSystemStatusMessage._FORMAT, buffer, offset,
                         self.posix_time_ns, self.used_memory_bytes)
        offset += ProfileSystemStatusMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        (self.posix_time_ns, self.used_memory_bytes) = \
            struct.unpack_from(ProfileSystemStatusMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileSystemStatusMessage._SIZE

        return offset - initial_offset

    def __repr__(self):
        return '%s @ POSIX time %s (%.6f sec)' % \
               (self.MESSAGE_TYPE.name, datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                self.posix_time_ns * 1e-9)

    def __str__(self):
        string = 'System status @ POSIX time %s (%.6f sec)\n' % \
                  (datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                   self.posix_time_ns * 1e-9)
        string += '  P1 time: %s\n' % str(self.p1_time)
        string += '  Used memory: %d B' % self.used_memory_bytes
        return string

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + ProfileSystemStatusMessage._SIZE


class ProfilePipelineDefinitionEntry:
    """!
    @brief Pipeline profiling point definition.
    """
    _FORMAT = '<I3xB'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.hash = 0
        self.name = ''

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        format = ProfilePipelineDefinitionEntry._FORMAT + '%ds' % len(self.name)

        args = (self.hash, len(self.name), self.name)
        if buffer is None:
            buffer = struct.pack(format, *args)
        else:
            struct.pack_into(format, buffer=buffer, offset=offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.hash, string_length) = \
            struct.unpack_from(ProfilePipelineDefinitionEntry._FORMAT, buffer=buffer, offset=offset)
        offset += ProfilePipelineDefinitionEntry._SIZE

        (self.name,) = \
            struct.unpack_from('%ds' % string_length, buffer=buffer, offset=offset)
        self.name = self.name.decode('utf-8')
        offset += string_length

        return offset - initial_offset

    def calcsize(self) -> int:
        return ProfilePipelineDefinitionEntry._SIZE + len(self.name)


class ProfilePipelineDefinitionMessage:
    """!
    @brief Measurement pipeline profiling point definitions
    """
    MESSAGE_TYPE = MessageType.PROFILE_PIPELINE_DEFINITION

    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.posix_time_ns = 0
        self.entries: List[ProfilePipelineDefinitionEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfilePipelineDefinitionMessage._FORMAT, buffer, offset,
                         self.posix_time_ns, len(self.entries))
        offset += ProfilePipelineDefinitionMessage._SIZE

        for entry in self.entries:
            offset += entry.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.posix_time_ns, num_entries) = \
            struct.unpack_from(ProfilePipelineDefinitionMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfilePipelineDefinitionMessage._SIZE

        self.entries = []
        for i in range(num_entries):
            entry = ProfilePipelineDefinitionEntry()
            offset += entry.unpack(buffer, offset)
            self.entries.append(entry)

        return offset - initial_offset

    def to_dict(self):
        return {e.hash: e.name for e in self.entries}

    def __repr__(self):
        return '%s @ POSIX time %s (%.6f sec)' % \
               (self.MESSAGE_TYPE.name, datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                self.posix_time_ns * 1e-9)

    def __str__(self):
        string = 'Pipeline definition @ POSIX time %s (%.6f sec)\n' % \
                  (datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                   self.posix_time_ns * 1e-9)
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %s' % (entry.hash, entry.name)
        return string

    def calcsize(self) -> int:
        return ProfilePipelineDefinitionMessage._SIZE + len(self.entries) * ProfilePipelineDefinitionEntry.calcsize()


class ProfilePipelineEntry:
    """!
    @brief Pipeline profiling point.
    """
    _FORMAT = '<If'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.hash = 0
        self.delay_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        args = (self.hash, self.delay_sec)
        if buffer is None:
            buffer = struct.pack(ProfilePipelineEntry._FORMAT, *args)
        else:
            struct.pack_into(ProfilePipelineEntry._FORMAT, buffer=buffer, offset=offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.hash, self.delay_sec) = \
            struct.unpack_from(ProfilePipelineEntry._FORMAT, buffer=buffer, offset=offset)
        offset += ProfilePipelineEntry._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return ProfilePipelineEntry._SIZE


class ProfilePipelineMessage:
    """!
    @brief Measurement pipeline profiling update.
    """
    MESSAGE_TYPE = MessageType.PROFILE_PIPELINE

    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.posix_time_ns = 0
        self.p1_time = Timestamp()
        self.entries: List[ProfilePipelineEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfilePipelineMessage._FORMAT, buffer, offset,
                         self.posix_time_ns, len(self.entries))
        offset += ProfilePipelineMessage._SIZE

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        for entry in self.entries:
            offset += entry.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.posix_time_ns, num_entries) = \
            struct.unpack_from(ProfilePipelineMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfilePipelineMessage._SIZE

        offset += self.p1_time.unpack(buffer, offset)

        self.entries = []
        for i in range(num_entries):
            entry = ProfilePipelineEntry()
            offset += entry.unpack(buffer, offset)
            self.entries.append(entry)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ POSIX time %s (%.6f sec)' % \
               (self.MESSAGE_TYPE.name, datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                self.posix_time_ns * 1e-9)

    def __str__(self):
        string = 'Pipeline profiling update @ POSIX time %s (%.6f sec)\n' % \
                  (datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                   self.posix_time_ns * 1e-9)
        string += '  P1 time: %s\n' % self.p1_time
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %f sec' % (entry.hash, entry.delay_sec)
        return string

    def calcsize(self) -> int:
        return ProfilePipelineMessage._SIZE + len(self.entries) * ProfilePipelineEntry.calcsize()


# Extend the message class with internal types.
message_type_to_class.update({
    MessageRequest.MESSAGE_TYPE: MessageRequest,
    ProfileSystemStatusMessage.MESSAGE_TYPE: ProfileSystemStatusMessage,
    ProfilePipelineDefinitionMessage.MESSAGE_TYPE: ProfilePipelineDefinitionMessage,
    ProfilePipelineMessage.MESSAGE_TYPE: ProfilePipelineMessage
})
