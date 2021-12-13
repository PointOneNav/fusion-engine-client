from .core import *
from . import ros

message_type_to_class = {
    # Navigation solution messages.
    PoseMessage.MESSAGE_TYPE: PoseMessage,
    PoseAuxMessage.MESSAGE_TYPE: PoseAuxMessage,
    GNSSInfoMessage.MESSAGE_TYPE: GNSSInfoMessage,
    GNSSSatelliteMessage.MESSAGE_TYPE: GNSSSatelliteMessage,

    # Sensor measurement messages.
    IMUMeasurement.MESSAGE_TYPE: IMUMeasurement,

    # ROS messages.
    ros.PoseMessage.MESSAGE_TYPE: ros.PoseMessage,
    ros.GPSFixMessage.MESSAGE_TYPE: ros.GPSFixMessage,
    ros.IMUMessage.MESSAGE_TYPE: ros.IMUMessage,
}
