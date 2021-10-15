from collections import defaultdict
from typing import List, Dict, Callable, Optional
from ..messages.internal import MessageHeader, MessageType, MessagePayload, message_type_to_class


class FusionEngineDecoder:

    def __init__(self):
        self._buffer: List[int] = []
        self._header: Optional[MessageHeader] = None
        # TODO: Add wild card
        self._callbacks: Dict[MessageType, List[Callable[[
            MessageHeader, MessagePayload], None]]] = defaultdict(list)

    def add_callback(self, MessageType, callback: Callable[[MessageHeader, MessagePayload], None]):
        self._callbacks[MessageType].append(callback)

    def on_data(self, data: List):
        self._buffer += data
        self._check_buffer()

    def on_byte(self, data: int):
        self._buffer.append(data)
        self._check_buffer()

    def _check_buffer(self):
        if self._header is None:
            while self._buffer:
                if self._buffer[0] == MessageHeader._SYNC0:
                    break
                self._buffer.pop(0)
            if len(self._buffer) < 2:
                return
            if self._buffer[1] != MessageHeader._SYNC1:
                self._buffer.pop(0)
                self._check_buffer()
            if len(self._buffer) < MessageHeader.calcsize():
                return
            self._header = MessageHeader()
            self._header.unpack(self._buffer)
            if self._header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                self._header = None
                self._buffer.pop(0)
                self._check_buffer()
        msg_len = self._header.payload_size_bytes + MessageHeader.calcsize()
        if len(self._buffer) < msg_len:
            return
        try:
            self._header.validate_crc(self._buffer)
            cls = message_type_to_class.get(self._header, None)
            if cls is not None:
                contents = cls()
                contents.unpack(buffer=self._buffer,
                                offset=MessageHeader.calcsize())
                for callback in self._callbacks[self._header.message_type]:
                    callback(self._header, contents)
            self._header = None
            self._buffer.pop(msg_len)
            self._check_buffer()
        except Exception as e:
            self._header = None
            self._buffer.pop(0)
            self._check_buffer()
