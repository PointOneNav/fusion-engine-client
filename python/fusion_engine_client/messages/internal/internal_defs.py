from aenum import extend_enum

from ..defs import *


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

    # System profiling data
    PROFILE_SYSTEM_STATUS = 20032
    PROFILE_PIPELINE_DEFINITION = 20036
    PROFILE_PIPELINE = 20040
    PROFILE_EXECUTION_DEFINITION = 20044
    PROFILE_EXECUTION = 20048
    PROFILE_FREERTOS_SYSTEM_STATUS = 20052
    PROFILE_FREERTOS_TASK_DEFINITION = 20056
    PROFILE_EXECUTION_STATS = 20060
    PROFILE_EXECUTION_STATS_DEFINITION = 20061
    PROFILE_COUNTER = 20062
    PROFILE_COUNTER_DEFINITION = 20063

    # Legacy Internal Alias
    LEGACY_PLATFORM_STORAGE_DATA = 20105


# Extend the message type enum with internal types.
for entry in InternalMessageType:
    extend_enum(MessageType, entry.name, entry.value)
