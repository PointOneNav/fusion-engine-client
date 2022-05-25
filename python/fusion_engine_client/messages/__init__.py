from .core import *
from . import ros

message_type_to_class = {
    # Navigation solution messages.
    PoseMessage.MESSAGE_TYPE: PoseMessage,
    PoseAuxMessage.MESSAGE_TYPE: PoseAuxMessage,
    GNSSInfoMessage.MESSAGE_TYPE: GNSSInfoMessage,
    GNSSSatelliteMessage.MESSAGE_TYPE: GNSSSatelliteMessage,
    CalibrationStatus.MESSAGE_TYPE: CalibrationStatus,
    RelativeENUPositionMessage.MESSAGE_TYPE: RelativeENUPositionMessage,

    # Sensor measurement messages.
    IMUMeasurement.MESSAGE_TYPE: IMUMeasurement,

    # ROS messages.
    ros.ROSPoseMessage.MESSAGE_TYPE: ros.ROSPoseMessage,
    ros.ROSGPSFixMessage.MESSAGE_TYPE: ros.ROSGPSFixMessage,
    ros.ROSIMUMessage.MESSAGE_TYPE: ros.ROSIMUMessage,

    # Command and control messages.
    CommandResponseMessage.MESSAGE_TYPE: CommandResponseMessage,
    MessageRequest.MESSAGE_TYPE: MessageRequest,
    ResetRequest.MESSAGE_TYPE: ResetRequest,
    VersionInfoMessage.MESSAGE_TYPE: VersionInfoMessage,
    EventNotificationMessage.MESSAGE_TYPE: EventNotificationMessage,

    SetConfigMessage.MESSAGE_TYPE: SetConfigMessage,
    GetConfigMessage.MESSAGE_TYPE: GetConfigMessage,
    SaveConfigMessage.MESSAGE_TYPE: SaveConfigMessage,
    ConfigResponseMessage.MESSAGE_TYPE: ConfigResponseMessage,

    SetOutputInterfaceConfigMessage.MESSAGE_TYPE: SetOutputInterfaceConfigMessage,
    GetOutputInterfaceConfigMessage.MESSAGE_TYPE: GetOutputInterfaceConfigMessage,
    OutputInterfaceConfigResponseMessage.MESSAGE_TYPE: OutputInterfaceConfigResponseMessage,
}

messages_with_system_time = [t for t, c in message_type_to_class.items() if hasattr(c(), 'system_time_ns')]

message_type_by_name = {c.__name__: t for t, c in message_type_to_class.items()}
