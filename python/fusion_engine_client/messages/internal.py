from datetime import datetime, timezone
from enum import IntEnum
from typing import List

from aenum import extend_enum
import numpy as np

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

PROFILING_TYPES = [
    MessageType.PROFILE_SYSTEM_STATUS,
    MessageType.PROFILE_PIPELINE_DEFINITION,
    MessageType.PROFILE_PIPELINE,
]


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

    _FORMAT = '<qfB3xQQQHHH2xf'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.posix_time_ns = 0

        self.cpu_usage = np.nan
        self.num_cpu_cores = 0

        self.total_memory_bytes = 0
        self.total_used_memory_bytes = 0
        self.used_memory_bytes = 0

        self.log_queue_depth = 0
        self.propagator_depth = 0
        self.dq_depth = 0
        self.dq_depth_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        struct.pack_into(ProfileSystemStatusMessage._FORMAT, buffer, offset,
                         self.posix_time_ns,
                         self.cpu_usage, self.num_cpu_cores,
                         self.total_memory_bytes, self.total_used_memory_bytes, self.used_memory_bytes,
                         self.log_queue_depth, self.propagator_depth, self.dq_depth, self.dq_depth_sec)
        offset += ProfileSystemStatusMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        (self.posix_time_ns,
         self.cpu_usage, self.num_cpu_cores,
         self.total_memory_bytes, self.total_used_memory_bytes, self.used_memory_bytes,
         self.log_queue_depth, self.propagator_depth, self.dq_depth, self.dq_depth_sec) = \
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
        string += '  CPU: %.1f%%\n' % self.cpu_usage
        string += '  Total memory: %d B/%d B' % (self.total_used_memory_bytes, self.total_memory_bytes)
        string += '  Used memory: %d B/%d B' % (self.used_memory_bytes, self.total_memory_bytes)
        string += '  Log queue depth: %d\n' % self.log_queue_depth
        string += '  Propagator depth: %d\n' % self.propagator_depth
        string += '  Delay queue depth: %d (%.2f sec)' % (self.dq_depth, self.dq_depth_sec)
        return string

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + ProfileSystemStatusMessage._SIZE

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'posix_time': np.array([m.posix_time_ns * 1e-9 for m in messages]),
            'cpu_usage': np.array([m.cpu_usage for m in messages]),
            'num_cpu_cores': np.array([m.num_cpu_cores for m in messages]),
            'total_memory_bytes': np.array([m.total_memory_bytes for m in messages]),
            'total_used_memory_bytes': np.array([m.total_used_memory_bytes for m in messages]),
            'used_memory_bytes': np.array([m.used_memory_bytes for m in messages]),
            'log_queue_depth': np.array([m.log_queue_depth for m in messages]),
            'propagator_depth': np.array([m.propagator_depth for m in messages]),
            'dq_depth': np.array([m.dq_depth for m in messages]),
            'dq_depth_sec': np.array([m.dq_depth_sec for m in messages]),
        }
        return result


class ProfileDefinitionEntry:
    """!
    @brief Individual profiling point definition.
    """
    _FORMAT = '<I3xB'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.id = 0
        self.name = ''

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        format = ProfileDefinitionEntry._FORMAT + '%ds' % len(self.name)

        args = (self.id, len(self.name), self.name)
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

        (self.id, string_length) = \
            struct.unpack_from(ProfileDefinitionEntry._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileDefinitionEntry._SIZE

        (self.name,) = \
            struct.unpack_from('%ds' % string_length, buffer=buffer, offset=offset)
        self.name = self.name.decode('utf-8')
        offset += string_length

        return offset - initial_offset

    def calcsize(self) -> int:
        return ProfileDefinitionEntry._SIZE + len(self.name)


class ProfileDefinitionMessage:
    """!
    @brief Profiling point definitions.
    """
    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.posix_time_ns = 0
        self.entries: List[ProfileDefinitionEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytes(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfileDefinitionMessage._FORMAT, buffer, offset,
                         self.posix_time_ns, len(self.entries))
        offset += ProfileDefinitionMessage._SIZE

        for entry in self.entries:
            offset += entry.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.posix_time_ns, num_entries) = \
            struct.unpack_from(ProfileDefinitionMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileDefinitionMessage._SIZE

        self.entries = []
        for i in range(num_entries):
            entry = ProfileDefinitionEntry()
            offset += entry.unpack(buffer, offset)
            self.entries.append(entry)

        return offset - initial_offset

    def to_dict(self):
        return {e.id: e.name for e in self.entries}

    def __repr__(self):
        return 'Profile definition @ POSIX time %s (%.6f sec)' % \
               (datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                self.posix_time_ns * 1e-9)

    def __str__(self):
        string = 'Profile definition @ POSIX time %s (%.6f sec)\n' % \
                  (datetime.utcfromtimestamp(self.posix_time_ns).replace(tzinfo=timezone.utc),
                   self.posix_time_ns * 1e-9)
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %s' % (entry.id, entry.name)
        return string

    def calcsize(self) -> int:
        return ProfileDefinitionMessage._SIZE + len(self.entries) * ProfileDefinitionEntry.calcsize()


class ProfilePipelineEntry:
    """!
    @brief Pipeline profiling point.
    """
    _FORMAT = '<If'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.id = 0
        self.delay_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        args = (self.id, self.delay_sec)
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

        (self.id, self.delay_sec) = \
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
    DEFINITION_TYPE = MessageType.PROFILE_PIPELINE_DEFINITION

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
            string += '    %d: %f sec' % (entry.id, entry.delay_sec)
        return string

    def calcsize(self) -> int:
        return ProfilePipelineMessage._SIZE + len(self.entries) * ProfilePipelineEntry.calcsize()

    @classmethod
    def to_numpy(cls, messages):
        points = {}
        for m in messages:
            for p in m.entries:
                if p.id not in points:
                    points[p.id] = [(m.posix_time_ns * 1e-9, p.delay_sec)]
                else:
                    points[p.id].append((m.posix_time_ns * 1e-9, p.delay_sec))
        points = {h: np.array(d).T for h, d in points.items()}

        result = {
            'posix_time': np.array([m.posix_time_ns * 1e-9 for m in messages]),
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'points': points
        }
        return result

    @classmethod
    def remap_by_name(cls, numpy_data, definition_message: ProfileDefinitionMessage):
        id_to_name = definition_message.to_dict()
        numpy_data.points = {id_to_name[id]: data for id, data in numpy_data.points.items()}


# Extend the message class with internal types.
message_type_to_class.update({
    MessageRequest.MESSAGE_TYPE: MessageRequest,
    ProfileSystemStatusMessage.MESSAGE_TYPE: ProfileSystemStatusMessage,
    ProfilePipelineMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    ProfilePipelineMessage.MESSAGE_TYPE: ProfilePipelineMessage
})
