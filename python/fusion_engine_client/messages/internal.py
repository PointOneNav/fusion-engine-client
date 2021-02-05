from enum import IntEnum

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


# Extend the message class with internal types.
message_type_to_class.update({
    MessageRequest.MESSAGE_TYPE: MessageRequest
})
