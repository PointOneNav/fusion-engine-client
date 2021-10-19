from collections import defaultdict
import logging
from typing import List, Dict, Callable, Optional, Tuple, Union

from ..messages import MessageHeader, MessageType, MessagePayload
# Note: This should be imported from `..messages` in the public repo.
from ..messages.internal import message_type_to_class

_logger = logging.getLogger('point_one.fusion_engine.parsers.decoder')


class FusionEngineDecoder:
    """!
    @brief Helper class for deserializing FusionEngine messages.

    @post
    This class keeps and internal buffer to track the state of the message
    currently being decoded. It will resync on errors to ensure all possible
    messages are decoded.
    """

    def __init__(self, max_payload_len_bytes=MessageHeader._MAX_EXPECTED_SIZE_BYTES):
        """!
        @param max_payload_len_bytes assume headers with payloads larger than this
            value are corrupted and resync.
        """
        self._max_payload_len_bytes = max_payload_len_bytes
        self._buffer = bytearray()
        self._header: Optional[MessageHeader] = None
        self._msg_len = 0
        self._bool_warn_seq_skip = False
        self._last_sequence_number = None
        self._callbacks: Dict[Optional[MessageType], List[Callable[[
            MessageHeader,
            Union[MessagePayload, bytes]], None]]] = defaultdict(list)

    def add_callback(self, type: MessageType,
                     callback: Callable[[Optional[MessageType],
                                         Union[MessagePayload, bytes]], None]):
        """!
        @brief Register a function to be called for certion MessageType.

        @post
        Registering multiple callbacks with the same type will result in
        multiple matching callbacks being called.

        @param type The type of message for this callback to receive. If type
               is None, this callback will be called for all messages.
        @param callback The function to call with decoded messages and their
               headers. For wild card callbacks or callbacks registered for a
               @ref MessageType without a corresponding MessagePayload, the
               payload contents will be returned as a byte array in the place
               of a @ref MessagePayload.
        """
        # `self._callbacks` is a `defaultdict(list)` so no need to initialize
        # list on first entry.
        self._callbacks[type].append(callback)

    def print_seq_skip_warnings(self, enable):
        """!
        @brief Enable a warning to print if the received message headers skip
               a sequence_number.

        @param enable If this is `True` print the warning when a sequence
               number is skipped.
        """
        self._bool_warn_seq_skip = enable

    def on_data(self, data: Union[bytes, int]) -> List[Tuple[MessageHeader, Union[MessagePayload, bytes]]]:
        """!
        @brief Decode FusionEngine messages from serialized data.

        @post
        This class maintains the state of decoding as it goes, so this function
        should be in a loop, called with data as it becomes available.

        As messages are decoded they will trigger any matching registered
        callbacks.

        @param data Either a single byte (which is of type `int` in python3) or
               a byte array for the message stream being decoded.

        @return A list of message results for any messages completed with the
                input `data`. Known message types will be a tuple of the @ref
                MessageHeader and a child of @ref MessagePayload corresponding
                to the @ref MessageType. Unknown messages will be a tuple of the @ref
                MessageHeader and a byte array with the payload contents.
        """
        # Cast singleton byte values to a byte array.
        if type(data) == int:
            data = data.to_bytes(1, 'big')
        self._buffer += data

        decoded_messages = []
        # While there may be a message in @ref self._buffer keep looping.
        while self._buffer:
            # Message must be at least long enough for header.
            if len(self._buffer) < MessageHeader.calcsize():
                break
            # Looking for a valid header.
            if self._header is None:
                # Explicitly check for the first two sync bytes to be a bit
                # more efficient then doing it inside the @ref
                # MessageHeader.unpack() with an exception.
                if self._buffer[0] != MessageHeader._SYNC0:
                    self._buffer.pop(0)
                    continue
                if self._buffer[1] != MessageHeader._SYNC1:
                    self._buffer.pop(0)
                    continue
                self._header = MessageHeader()
                self._header.unpack(self._buffer)
                self._msg_len = self._header.payload_size_bytes + MessageHeader.calcsize()
                if self._header.payload_size_bytes > self._max_payload_len_bytes:
                    self._header = None
                    self._buffer.pop(0)
                    continue
            # Looking for complete message.
            if len(self._buffer) < self._msg_len:
                break
            try:
                self._header.validate_crc(self._buffer)
                # If cls is not None, it is a child of @ref MessagePayload that
                # maps to the received @ref MessageType.
                cls = message_type_to_class.get(
                    self._header.message_type, None)
                if cls is not None:
                    contents = cls()
                    contents.unpack(buffer=self._buffer,
                                    offset=MessageHeader.calcsize())
                    result = (self._header, contents)
                    _logger.debug(
                        'Decoded FusionEngine message %s', repr(contents))
                else:
                    # Make a copy of payload to return instead of decoded
                    # message.
                    result = (self._header, bytes(
                        self._buffer[MessageHeader.calcsize():self._msg_len]))
                    _logger.debug('Decoded unknown FusionEngine message type=%d size=%d',
                                  self._header.message_type, self._header.payload_size_bytes)
                if self._last_sequence_number is not None and self._bool_warn_seq_skip and (self._last_sequence_number + 1) % 2**32 != self._header.sequence_number:
                    _logger.warning("FusionEngine messages' sequence_number skipped from %d to %d.",
                                    self._last_sequence_number, self._header.sequence_number)
                self._last_sequence_number = self._header.sequence_number
                # self._callbacks is a `defaultdict(list)` and returns []
                # if the key is not found.
                for callback in self._callbacks[self._header.message_type]:
                    # Map results to callback parameters.
                    callback(*result)
                # Match None callbacks to every message.
                for callback in self._callbacks[None]:
                    # Map results to callback parameters.
                    callback(*result)
                # Move decoder past the current message
                self._buffer = self._buffer[self._msg_len:]
                self._header = None
                self._msg_len = 0
                decoded_messages.append(result)
            # Thrown on bad CRC or if the `unpack` function for a known
            # @ ref MessagePayload fails (ie. the header payload length differs
            # from the length assumed by the `unpack` function).
            except Exception as e:
                _logger.debug(e)
                self._header = None
                self._msg_len = 0
                self._buffer.pop(0)
        return decoded_messages
