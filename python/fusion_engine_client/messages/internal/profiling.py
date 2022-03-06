from datetime import datetime, timezone
from enum import IntEnum
from typing import List

from construct import (Struct, Int64ul, Int32ul, Int16ul,
                       Int8ul, Padding, this, Array)
import numpy as np

from .internal_defs import *


PROFILING_TYPES = [
    MessageType.PROFILE_SYSTEM_STATUS,
    MessageType.PROFILE_PIPELINE_DEFINITION,
    MessageType.PROFILE_PIPELINE,
    MessageType.PROFILE_EXECUTION_DEFINITION,
    MessageType.PROFILE_EXECUTION,
    MessageType.PROFILE_FREERTOS_SYSTEM_STATUS,
    MessageType.PROFILE_FREERTOS_TASK_DEFINITION,
    MessageType.PROFILE_EXECUTION_STATS,
    MessageType.PROFILE_EXECUTION_STATS_DEFINITION,
    MessageType.PROFILE_COUNTER,
    MessageType.PROFILE_COUNTER_DEFINITION,
]


class ProfileSystemStatusMessage(MessagePayload):
    """!
    @brief System-level profiling data.
    """
    MESSAGE_TYPE = MessageType.PROFILE_SYSTEM_STATUS
    MESSAGE_VERSION = 0

    _MAX_CPU_CORES = 16
    _INVALID_CPU_USAGE = 0xFF
    _CPU_USAGE_SCALE = 2.0

    _FORMAT = '<qB2xB%dBQQQHHH2xf' % _MAX_CPU_CORES
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.p1_time = Timestamp()
        self.system_time_ns = 0

        self.num_cpu_cores = 0
        self.total_cpu_usage = np.nan
        self.cpu_usage_per_core = []

        self.total_memory_bytes = 0
        self.total_used_memory_bytes = 0
        self.used_memory_bytes = 0

        self.log_queue_depth = 0
        self.propagator_depth = 0
        self.dq_depth = 0
        self.dq_depth_sec = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        args = [self.system_time_ns, self.num_cpu_cores]

        def percent_to_int(value):
            if np.isnan(value):
                return ProfileSystemStatusMessage._INVALID_CPU_USAGE
            else:
                return int(value * ProfileSystemStatusMessage._CPU_USAGE_SCALE)

        args.append(percent_to_int(self.total_cpu_usage))
        args.extend([percent_to_int(v) for v in self.cpu_usage_per_core[:ProfileSystemStatusMessage._MAX_CPU_CORES]])
        args.extend([ProfileSystemStatusMessage._INVALID_CPU_USAGE] *
                    (len(self.cpu_usage_per_core) - ProfileSystemStatusMessage._MAX_CPU_CORES))

        args.extend([self.total_memory_bytes, self.total_used_memory_bytes, self.used_memory_bytes,
                     self.log_queue_depth, self.propagator_depth, self.dq_depth, self.dq_depth_sec])
        struct.pack_into(ProfileSystemStatusMessage._FORMAT, buffer, offset, *args)
        offset += ProfileSystemStatusMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        values = struct.unpack_from(ProfileSystemStatusMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileSystemStatusMessage._SIZE

        (self.system_time_ns, self.num_cpu_cores) = values[:2]

        def int_to_percent(value):
            if value == ProfileSystemStatusMessage._INVALID_CPU_USAGE:
                return np.nan
            else:
                return value / ProfileSystemStatusMessage._CPU_USAGE_SCALE

        self.total_cpu_usage = int_to_percent(values[2])
        self.cpu_usage_per_core = [int_to_percent(v) for v in values[3:3 + ProfileSystemStatusMessage._MAX_CPU_CORES]]
        self.cpu_usage_per_core = self.cpu_usage_per_core[:self.num_cpu_cores]

        (self.total_memory_bytes, self.total_used_memory_bytes, self.used_memory_bytes,
         self.log_queue_depth, self.propagator_depth, self.dq_depth, self.dq_depth_sec) = \
            values[3 + ProfileSystemStatusMessage._MAX_CPU_CORES:]

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = 'System Status @ %s\n' % system_time_to_str(self.system_time_ns)
        string += '  P1 time: %s\n' % str(self.p1_time)
        string += '  CPU: %.1f%%\n' % self.total_cpu_usage
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
            'system_time': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'num_cpu_cores': np.array([m.num_cpu_cores for m in messages]),
            'total_cpu_usage': np.array([m.total_cpu_usage for m in messages]),
            'cpu_usage_per_core': np.array([m.cpu_usage_per_core for m in messages]).T,
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


class ProfileDefinitionMessage(MessagePayload):
    """!
    @brief Profiling point definitions.

    @note
    This class is used for multiple profiling data types.
    """
    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.system_time_ns = 0
        self.entries: List[ProfileDefinitionEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfileDefinitionMessage._FORMAT, buffer, offset,
                         self.system_time_ns, len(self.entries))
        offset += ProfileDefinitionMessage._SIZE

        for entry in self.entries:
            offset += entry.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.system_time_ns, num_entries) = \
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
        return '%s @ %s' % (self.__class__.__name__, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = 'Profile Definition @ %s\n' % system_time_to_str(self.system_time_ns)
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %s' % (entry.id, entry.name)
        return string.rstrip()

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


class ProfilePipelineMessage(MessagePayload):
    """!
    @brief Measurement pipeline profiling update.
    """
    MESSAGE_TYPE = MessageType.PROFILE_PIPELINE
    MESSAGE_VERSION = 0
    DEFINITION_TYPE = MessageType.PROFILE_PIPELINE_DEFINITION

    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.system_time_ns = 0
        self.p1_time = Timestamp()
        self.entries: List[ProfilePipelineEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfilePipelineMessage._FORMAT, buffer, offset,
                         self.system_time_ns, len(self.entries))
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

        (self.system_time_ns, num_entries) = \
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
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = 'Pipeline Profiling Update @ %s\n' % system_time_to_str(self.system_time_ns)
        string += '  P1 time: %s\n' % self.p1_time
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %f sec' % (entry.id, entry.delay_sec)
        return string.rstrip()

    def calcsize(self) -> int:
        return ProfilePipelineMessage._SIZE + Timestamp.calcsize() + len(self.entries) * ProfilePipelineEntry.calcsize()

    @classmethod
    def to_numpy(cls, messages):
        points = {}
        for m in messages:
            for p in m.entries:
                if p.id not in points:
                    points[p.id] = [(m.system_time_ns * 1e-9, p.delay_sec)]
                else:
                    points[p.id].append((m.system_time_ns * 1e-9, p.delay_sec))
        points = {h: np.array(d).T for h, d in points.items()}

        result = {
            'system_time': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'points': points
        }
        return result

    @classmethod
    def remap_by_name(cls, numpy_data, definition_message: ProfileDefinitionMessage):
        id_to_name = definition_message.to_dict()
        numpy_data.points = {id_to_name[id]: data for id, data in numpy_data.points.items()}
        return id_to_name


class ProfileExecutionEntry:
    """!
    @brief Execution profiling point.
    """
    _FORMAT = '<Iq'
    _SIZE: int = struct.calcsize(_FORMAT)

    START = 0
    STOP = 1

    def __init__(self):
        self.id = 0
        self.action = None
        self.system_time_ns = 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        system_time_ns = -self.system_time_ns if self.action == ProfileExecutionEntry.STOP else self.system_time_ns

        args = (self.id, system_time_ns)
        if buffer is None:
            buffer = struct.pack(ProfileExecutionEntry._FORMAT, *args)
        else:
            struct.pack_into(ProfileExecutionEntry._FORMAT, buffer=buffer, offset=offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.id, system_time_ns) = \
            struct.unpack_from(ProfileExecutionEntry._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileExecutionEntry._SIZE

        if system_time_ns < 0:
            self.action = ProfileExecutionEntry.STOP
            self.system_time_ns = -system_time_ns
        else:
            self.action = ProfileExecutionEntry.START
            self.system_time_ns = system_time_ns

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return ProfileExecutionEntry._SIZE


class ProfileExecutionMessage(MessagePayload):
    """!
    @brief Code execution profiling update.
    """
    MESSAGE_TYPE = MessageType.PROFILE_EXECUTION
    MESSAGE_VERSION = 0
    DEFINITION_TYPE = MessageType.PROFILE_EXECUTION_DEFINITION

    _FORMAT = '<q2xH'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.system_time_ns = 0
        self.entries: List[ProfileExecutionEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(ProfileExecutionMessage._FORMAT, buffer, offset,
                         self.system_time_ns, len(self.entries))
        offset += ProfileExecutionMessage._SIZE

        for entry in self.entries:
            offset += entry.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.system_time_ns, num_entries) = \
            struct.unpack_from(ProfileExecutionMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ProfileExecutionMessage._SIZE

        self.entries = []
        for i in range(num_entries):
            entry = ProfileExecutionEntry()
            offset += entry.unpack(buffer, offset)
            self.entries.append(entry)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = 'Execution Profiling Update @ %s\n' % system_time_to_str(self.system_time_ns)
        string += '  %d entries:' % len(self.entries)
        for entry in self.entries:
            string += '\n'
            string += '    %d: %s @ %f sec' % (entry.id,
                                               'start' if entry.action == ProfileExecutionEntry.START else 'stop',
                                               entry.system_time_ns * 1e-9)
        return string.rstrip()

    def calcsize(self) -> int:
        return ProfileExecutionMessage._SIZE + len(self.entries) * ProfileExecutionEntry.calcsize()

    @classmethod
    def to_numpy(cls, messages):
        points = {}
        for m in messages:
            for p in m.entries:
                if p.id not in points:
                    points[p.id] = [(p.system_time_ns, p.action)]
                else:
                    points[p.id].append((p.system_time_ns, p.action))
        points = {h: np.array(d, dtype=int).T for h, d in points.items()}

        result = {
            'points': points
        }
        return result

    @classmethod
    def remap_by_name(cls, numpy_data, definition_message: ProfileDefinitionMessage):
        id_to_name = definition_message.to_dict()
        numpy_data.points = {id_to_name[id]: data for id, data in numpy_data.points.items()}
        return id_to_name


class ProfileFreeRtosSystemStatusMessage(MessagePayload):
    """!
    @brief FreeRTOS System-level profiling data.
    """
    MESSAGE_TYPE = MessageType.PROFILE_FREERTOS_SYSTEM_STATUS
    MESSAGE_VERSION = 0
    DEFINITION_TYPE = MessageType.PROFILE_FREERTOS_TASK_DEFINITION

    _INVALID_CPU_USAGE = 0xFF
    _CPU_USAGE_SCALE = 2.0

    ProfileFreeRtosTaskStatusEntryConstruct = Struct(
        Padding(3),
        "cpu_usage" / Int8ul,
        "stack_high_water_mark_bytes" / Int32ul,
    )

    ProfileFreeRtosSystemStatusMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        "heap_free_bytes" / Int32ul,
        "sbrk_free_bytes" / Int32ul,
        Padding(3),
        "num_tasks" / Int8ul,
        "task_entries" / Array(this.num_tasks, ProfileFreeRtosTaskStatusEntryConstruct),
    )

    def __init__(self):
        self.system_time_ns = 0,
        self.heap_free_bytes = 0,
        self.sbrk_free_bytes = 0,
        self.task_entries = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)

        def percent_to_int(value):
            if np.isnan(value):
                return ProfileFreeRtosSystemStatusMessage._INVALID_CPU_USAGE
            else:
                return int(value * ProfileFreeRtosSystemStatusMessage._CPU_USAGE_SCALE)
        for status in values['task_entries']:
            status['cpu_usage'] = percent_to_int(status['cpu_usage'])
        values['num_tasks'] = len(values['task_entries'])

        packed_data = ProfileFreeRtosSystemStatusMessage.ProfileFreeRtosSystemStatusMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = ProfileFreeRtosSystemStatusMessage.ProfileFreeRtosSystemStatusMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)

        def int_to_percent(value):
            if value == ProfileFreeRtosSystemStatusMessage._INVALID_CPU_USAGE:
                return np.isnan(value)
            else:
                return value / ProfileFreeRtosSystemStatusMessage._CPU_USAGE_SCALE
        for status in self.task_entries:
            status['cpu_usage'] = int_to_percent(status['cpu_usage'])
        return parsed._io.tell()

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = f'FreeRTOS System Profiling @ %s\n' % system_time_to_str(self.system_time_ns)
        string += f'\theap_free_bytes: {self.heap_free_bytes}\n'
        string += f'\tsbrk_free_bytes: {self.sbrk_free_bytes}\n'
        for i, task in enumerate(self.task_entries):
            string += f'\tTask[{i}]:\n'
            string += f'\t\tcpu_usage: {task.cpu_usage}%\n'
            string += f'\t\tstack_high_water_mark_bytes: {task.stack_high_water_mark_bytes}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'system_time_sec': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'heap_free_bytes': np.array([m.heap_free_bytes for m in messages]),
            'sbrk_free_bytes': np.array([m.sbrk_free_bytes for m in messages]),
            'task_cpu_usage_percent': [],
            'task_min_stack_free_bytes': [],
        }
        if len(messages) > 0:
            num_tasks = len(messages[0].task_entries)
            for i in range(num_tasks):
                task_cpu_usage_percent = np.array([m.task_entries[i].cpu_usage for m in messages])
                result['task_cpu_usage_percent'].append(task_cpu_usage_percent)
                task_min_stack_free_bytes = np.array([m.task_entries[i].stack_high_water_mark_bytes for m in messages])
                result['task_min_stack_free_bytes'].append(task_min_stack_free_bytes)
        return result


class ProfileExecutionStatsMessage(MessagePayload):
    """!
    @brief Execution stats profiling data.
    """
    MESSAGE_TYPE = MessageType.PROFILE_EXECUTION_STATS
    MESSAGE_VERSION = 0
    DEFINITION_TYPE = MessageType.PROFILE_EXECUTION_STATS_DEFINITION

    ProfileExecutionStatsEntryConstruct = Struct(
        "running_time_ns" / Int32ul,
        "max_run_time_ns" / Int32ul,
        "run_count" / Int32ul,
    )

    ProfileExecutionStatsMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        Padding(2),
        "num_entries" / Int16ul,
        "entries" / Array(this.num_entries, ProfileExecutionStatsEntryConstruct),
    )

    def __init__(self):
        self.system_time_ns = 0,
        self.entries = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = ProfileExecutionStatsMessage.ProfileExecutionStatsMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = ProfileExecutionStatsMessage.ProfileExecutionStatsMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = f'Execution Stats Profiling @ %s\n' % system_time_to_str(self.system_time_ns)
        for i, trace in enumerate(self.entries):
            string += f'\tTrace[{i}]:\n'
            string += f'\t\trunning_time_ns: {trace.running_time_ns}\n'
            string += f'\t\tmax_run_time_ns: {trace.max_run_time_ns}\n'
            string += f'\t\trun_count: {trace.run_count}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'system_time_sec': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'running_time_ns': [],
            'max_run_time_ns': [],
            'run_count': [],
        }
        if len(messages) > 0:
            num_tasks = len(messages[0].entries)
            for i in range(num_tasks):
                running_time_ns = np.array([m.entries[i].running_time_ns for m in messages])
                result['running_time_ns'].append(running_time_ns)
                max_run_time_ns = np.array([m.entries[i].max_run_time_ns for m in messages])
                result['max_run_time_ns'].append(max_run_time_ns)
                run_count = np.array([m.entries[i].run_count for m in messages])
                result['run_count'].append(run_count)
        return result


class ProfileCounterMessage(MessagePayload):
    """!
    @brief Execution stats profiling data.
    """
    MESSAGE_TYPE = MessageType.PROFILE_COUNTER
    MESSAGE_VERSION = 0
    DEFINITION_TYPE = MessageType.PROFILE_COUNTER_DEFINITION

    ProfileCounterEntryConstruct = Struct(
        "count" / Int32ul,
    )

    ProfileCounterMessageConstruct = Struct(
        "system_time_ns" / Int64ul,
        Padding(2),
        "num_entries" / Int16ul,
        "entries" / Array(this.num_entries, ProfileCounterEntryConstruct),
    )

    def __init__(self):
        self.system_time_ns = 0,
        self.entries = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = ProfileCounterMessage.ProfileCounterMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = ProfileCounterMessage.ProfileCounterMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, system_time_to_str(self.system_time_ns))

    def __str__(self):
        string = f'Profiling Counters @ %s\n' % system_time_to_str(self.system_time_ns)
        for i, counter in enumerate(self.entries):
            string += f'\tCount[{i}]: {counter.count}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'system_time_sec': np.array([m.system_time_ns * 1e-9 for m in messages]),
            'counters': [],
        }
        if len(messages) > 0:
            num_tasks = len(messages[0].entries)
            for i in range(num_tasks):
                counters = np.array([m.entries[i].count for m in messages])
                result['counters'].append(counters)
        return result
