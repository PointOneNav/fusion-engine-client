from collections import defaultdict
import logging
from typing import List, Dict, Callable, Optional, Tuple, Union

from ..messages import MessageHeader, MessageType, MessagePayload, message_type_to_class

_logger = logging.getLogger('point_one.fusion_engine.parsers.decoder')


class FusionEngineDecoder:
    """!
    @brief Helper class for framing and deserializing FusionEngine messages.

    This class performs message framing and validation operations on an incoming stream of bytes to decode any
    FusionEngine messages found within the stream. If an error is detected (CRC failure, invalid message length, etc.),
    the stream will resynchronize automatically.
    """

    def __init__(self, max_payload_len_bytes: int = MessageHeader._MAX_EXPECTED_SIZE_BYTES,
                 warn_on_unrecognized: bool = True):
        """!
        @brief Construct a new decoder instance.

        @param max_payload_len_bytes The maximum expected payload length (in bytes). Incoming headers with reported
               payload lengths larger than this value will be treated as corrupted/invalid and will trigger a
               resynchronization.
        @param warn_on_unrecognized If `True`, print a warning if a deserialized message header contains an unrecognized
               or unsupported message type.
        """
        self._warn_on_unrecognized = warn_on_unrecognized
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
                     callback: Callable[[MessageHeader,
                                         Union[MessagePayload, bytes]], None]):
        """!
        @brief Register a function to be called when a specific message is decoded.

        @note
        Multiple callbacks may be registered for the same message type.

        @param type The type of message for this callback to receive. If type is `None`, this callback will be called
               for all messages.
        @param callback The function to call with the message header and decoded contents (@ref MessagePayload object).
               If the incoming message type is not recognized, the second argument will be a `bytes` object containing
               the uninterpreted payload contents.
        """
        # `self._callbacks` is a `defaultdict(list)` so no need to initialize list on first entry.
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

        This function should be called when any incoming bytes are received. Data will be buffered internally until
        complete messages are received.

        When complete messages are decoded and validated, this function will provide them to any registered callback
        functions (see @ref add_callback()). When finished, this function will return a list of completed messages.

        @param data Either a single byte (which is of type `int` in Python 3) or a byte array (`bytes`) containing
               incoming data to be decoded.

        @return A list of message results for any messages completed with the input `data`. Each list entry will contain
                the message header and the decoded contents (@ref MessagePayload object). If the incoming message type
                is not recognized, the second argument will be a `bytes` containing the uninterpreted payload contents.
        """
        # Cast singleton byte values to a byte array.
        if type(data) == int:
            data = data.to_bytes(1, 'big')

        # Append the new data to the buffer.
        self._buffer += data

        # Decode all messages found in the buffer.
        decoded_messages = []
        while self._buffer:
            # Message must be at least long enough for header.
            if len(self._buffer) < MessageHeader.calcsize():
                break
            # Looking for a valid header.
            if self._header is None:
                # Explicitly check for the first two sync bytes to be a bit more efficient then doing it inside the @ref
                # MessageHeader.unpack() with an exception.
                if self._buffer[0] != MessageHeader._SYNC0:
                    self._buffer.pop(0)
                    continue
                if self._buffer[1] != MessageHeader._SYNC1:
                    self._buffer.pop(0)
                    continue

                # Possible header found. Decode it and wait for the payload.
                self._header = MessageHeader()
                self._header.unpack(self._buffer, warn_on_unrecognized=self._warn_on_unrecognized)
                self._msg_len = self._header.payload_size_bytes + MessageHeader.calcsize()
                if self._header.payload_size_bytes > self._max_payload_len_bytes:
                    self._header = None
                    self._buffer.pop(0)
                    continue

            # If there's not enough data to complete the message, we're done looping.
            if len(self._buffer) < self._msg_len:
                break

            # Validate the CRC. This will raise an exception on CRC failure.
            try:
                self._header.validate_crc(self._buffer)
                # If cls is not None, it is a child of @ref MessagePayload that
                # maps to the received @ref MessageType.
                cls = message_type_to_class.get(
                    self._header.message_type, None)
                if cls is not None:
                    contents = cls()
                    try:
                        contents.unpack(buffer=self._buffer,
                                        offset=MessageHeader.calcsize())
                    except Exception as e:
                        _logger.error('Failed unpacking %s: %s',
                                      self._header.message_type, e)
                        self._header = None
                        self._buffer.pop(0)
                        continue
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
