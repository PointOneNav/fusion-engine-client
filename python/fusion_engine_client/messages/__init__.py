from .core import *
from .fault_control import *
from . import ros

message_type_to_class = MessagePayload.message_type_to_class
message_type_by_name = MessagePayload.message_type_by_name

messages_with_p1_time = set([t for t, c in message_type_to_class.items() if hasattr(c(), 'p1_time')])
messages_with_gps_time = set([t for t, c in message_type_to_class.items() if hasattr(c(), 'gps_time')])
messages_with_system_time = set([t for t, c in message_type_to_class.items() if hasattr(c(), 'system_time_ns')])
