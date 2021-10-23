from .profiling import *
from .config_and_control import *
from .. import message_type_to_class

# Extend the message class with internal types.
message_type_to_class.update({
    MessageRequest.MESSAGE_TYPE: MessageRequest,
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
    ResetMessage.MESSAGE_TYPE: ResetMessage,
    CommandResponseMessage.MESSAGE_TYPE: CommandResponseMessage,
    QueueConfigParamMessage.MESSAGE_TYPE: QueueConfigParamMessage,
    ApplyConfigMessage.MESSAGE_TYPE: ApplyConfigMessage,
    ActiveConfigRequestMessage.MESSAGE_TYPE: ActiveConfigRequestMessage,
    QueuedConfigRequestMessage.MESSAGE_TYPE: QueuedConfigRequestMessage,
    SavedConfigRequestMessage.MESSAGE_TYPE: SavedConfigRequestMessage,
    ConfigurationDataMessage.MESSAGE_TYPE: ConfigurationDataMessage,
})
