from collections import defaultdict
from typing import List, Dict, Callable, Optional, Tuple, Union

from ..messages import MessageHeader, MessageType, MessagePayload
from ..messages.internal import message_type_to_class


class FusionEngineDecoder:
    def __init__(self):
        self._buffer = bytearray()
        self._header: Optional[MessageHeader] = None
        # None in the callback key will match any MessageType.
        self._callbacks: Dict[Optional[MessageType], List[Callable[[
            MessageHeader, Union[MessagePayload, bytes]], None]]] = defaultdict(list)

    def add_callback(self, MessageType, callback: Callable[[Optional[MessageType], Union[MessagePayload, bytes]], None]):
        self._callbacks[MessageType].append(callback)

    def on_data(self, data: Union[bytes, int]) -> List[Tuple[MessageHeader, Union[MessagePayload, bytes]]]:
        if type(data) == int:
            data = data.to_bytes(1, 'big')
        self._buffer += data

        decoded_messages = []
        while self._buffer:
            if self._header is None:
                if self._buffer[0] != MessageHeader._SYNC0:
                    self._buffer.pop(0)
                    continue
                if len(self._buffer) < 2:
                    break
                if self._buffer[1] != MessageHeader._SYNC1:
                    self._buffer.pop(0)
                    continue
                if len(self._buffer) < MessageHeader.calcsize():
                    break
                self._header = MessageHeader()
                self._header.unpack(self._buffer)
                if self._header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                    self._header = None
                    self._buffer.pop(0)
                    continue
            msg_len = self._header.payload_size_bytes + MessageHeader.calcsize()
            if len(self._buffer) < msg_len:
                break
            try:
                self._header.validate_crc(self._buffer)
                cls = message_type_to_class.get(
                    self._header.message_type, None)
                if cls is not None:
                    contents = cls()
                    contents.unpack(buffer=self._buffer,
                                    offset=MessageHeader.calcsize())
                    for callback in self._callbacks[self._header.message_type]:
                        callback(self._header, contents)
                    for callback in self._callbacks[None]:
                        callback(self._header, contents)
                    result = (self._header, contents)
                else:
                    result = (self._header, bytes(
                        self._buffer[MessageHeader.calcsize():msg_len]))
                self._header = None
                self._buffer = self._buffer[msg_len:]
                decoded_messages.append(result)
            except Exception as e:
                self._header = None
                self._buffer.pop(0)
        return decoded_messages
