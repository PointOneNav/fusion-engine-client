from .. import message_type_to_class, PlatformStorageDataMessage
from .internal_defs import InternalMessageType
from .profiling import *

# Extend the message class with internal types.
message_type_to_class.update({
    ProfileSystemStatusMessage.MESSAGE_TYPE: ProfileSystemStatusMessage,
    ProfilePipelineMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    ProfilePipelineMessage.MESSAGE_TYPE: ProfilePipelineMessage,
    ProfileExecutionMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    ProfileExecutionMessage.MESSAGE_TYPE: ProfileExecutionMessage,
    ProfileFreeRtosSystemStatusMessage.MESSAGE_TYPE: ProfileFreeRtosSystemStatusMessage,
    ProfileFreeRtosSystemStatusMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    ProfileExecutionStatsMessage.MESSAGE_TYPE: ProfileExecutionStatsMessage,
    ProfileExecutionStatsMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    ProfileCounterMessage.MESSAGE_TYPE: ProfileCounterMessage,
    ProfileCounterMessage.DEFINITION_TYPE: ProfileDefinitionMessage,
    InternalMessageType.LEGACY_PLATFORM_STORAGE_DATA: PlatformStorageDataMessage,
})
