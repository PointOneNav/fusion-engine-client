from enum import IntEnum

from .internal_defs import *


class MessageRequest(MessagePayload):
    """!
    @brief Transmission request for a specified message type.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_REQ
    MESSAGE_VERSION = 0

    _FORMAT = '<H2x'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self, message_type: MessageType = MessageType.INVALID):
        self.message_type: MessageType = message_type

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

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


class ResetMessage(MessagePayload):
    """!
    @brief Reset command
    """
    MESSAGE_TYPE = MessageType.RESET_CMD
    MESSAGE_VERSION = 0

    RESET_NAVIGATION = 0x00000001
    RESET_EPHEMERIS = 0x00000002
    RESET_CORRECTIONS = 0x00000004
    RESET_SOFTWARE = 0x00FFFFFF

    _FORMAT = '<I'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.reset_mask = 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        struct.pack_into(ResetMessage._FORMAT, buffer, offset,
                         self.reset_mask)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.reset_mask,) = \
            struct.unpack_from(ResetMessage._FORMAT, buffer=buffer, offset=offset)
        offset += ResetMessage._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return ResetMessage._SIZE


class CommandResponseMessage(MessagePayload):
    """!
    @brief Reset command
    """
    MESSAGE_TYPE = MessageType.CMD_RESPONSE
    MESSAGE_VERSION = 0

    class Response(IntEnum):
        OK = 0,
        ERROR = 1

    _FORMAT = '<I3xB'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self):
        self.source_sequence_num = 0
        self.response = CommandResponseMessage.Response.OK

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        struct.pack_into(CommandResponseMessage._FORMAT, buffer, offset,
                         self.source_sequence_num, self.response)
        offset = CommandResponseMessage._SIZE

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        (self.source_sequence_num, self.response) = \
            struct.unpack_from(CommandResponseMessage._FORMAT, buffer=buffer, offset=offset)
        offset = CommandResponseMessage._SIZE

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return CommandResponseMessage._SIZE
