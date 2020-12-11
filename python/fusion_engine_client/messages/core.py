from .defs import *
from .measurements import *
from .solution import *

message_type_to_class = {
    PoseMessage.MESSAGE_TYPE: PoseMessage,
    PoseAuxMessage.MESSAGE_TYPE: PoseAuxMessage,
    GNSSInfoMessage.MESSAGE_TYPE: GNSSInfoMessage,
    GNSSSatelliteMessage.MESSAGE_TYPE: GNSSSatelliteMessage,
    IMUMeasurement.MESSAGE_TYPE: IMUMeasurement,
}
