from collections import defaultdict
import logging
from typing import List, Dict, Callable, Optional, Tuple, Union

from ..messages import MessageHeader, MessageType, MessagePayload, message_type_to_class

_logger = logging.getLogger('point_one.fusion_engine.parsers.decoder')

Callback = Callable[[MessageHeader, Union[MessagePayload, bytes]], None]
CallbackWithBytes = Callable[[MessageHeader, Union[MessagePayload, bytes], bytes], None]

MessageTuple = Tuple[MessageHeader, Union[MessagePayload, bytes]]
MessageWithBytesTuple = Tuple[MessageHeader, Union[MessagePayload, bytes], bytes]


class FusionEngineDecoder:
    """!
    @brief Helper class for framing and deserializing FusionEngine messages.

    This class performs message framing and validation operations on an incoming stream of bytes to decode any
    FusionEngine messages found within the stream. If an error is detected (CRC failure, invalid message length, etc.),
    the stream will resynchronize automatically.
    """

    def __init__(self, max_payload_len_bytes: int = MessageHeader._MAX_EXPECTED_SIZE_BYTES,
                 warn_on_unrecognized: bool = False, warn_on_gap: bool = False, warn_on_error: bool = False,
                 return_bytes: bool = False, return_offset: bool = False):
        """!
        @brief Construct a new decoder instance.

        @param max_payload_len_bytes The maximum expected payload length (in bytes). Incoming headers with reported
               payload lengths larger than this value will be treated as corrupted/invalid and will trigger a
               resynchronization.
        @param warn_on_unrecognized If `True`, print a warning if a deserialized message header contains an unrecognized
               or unsupported message type.
        @param warn_on_gap If `True`, print a warning if a gap is detected in the incoming message sequence numbers.
        @param warn_on_error If `True`, print a warning if an error is detected (invalid CRC, invalid payload length,
               etc.).
        @param return_bytes If `True`, return a `bytes` object with the raw data (header + payload) in addition to the
               decoded message object.
        @param return_offset If `True`, the byte offset into the data stream at which the message was found.
        """
        self._warn_on_unrecognized = warn_on_unrecognized
        self._warn_on_seq_skip = warn_on_gap
        self._warn_on_error = warn_on_error

        self._return_bytes = return_bytes
        self._return_offset = return_offset

        self._max_payload_len_bytes = max_payload_len_bytes
        self._buffer = bytearray()
        self._header: Optional[MessageHeader] = None
        self._msg_len = 0
        self._last_sequence_number = None
        self._bytes_processed = 0

        self._callbacks: Dict[Optional[MessageType], List[Callable[[
            MessageHeader,
            Union[MessagePayload, bytes]], None]]] = defaultdict(list)

    def add_callback(self, type: Optional[MessageType], callback: Union[Callback, CallbackWithBytes]):
        """!
        @brief Register a function to be called when a specific message is decoded.

        @note
        Multiple callbacks may be registered for the same message type.

        @param type The type of message for this callback to receive. If type is `None`, this callback will be called
               for all messages.
        @param callback The function to call with the message header and decoded contents (@ref MessagePayload object).
               If the incoming message type is not recognized, the second argument will be a `bytes` object containing
               the uninterpreted payload contents. If `return_bytes == True`, the function will be called with a third
               argument containing the uninterpreted message contents (including the header).
        """
        # `self._callbacks` is a `defaultdict(list)` so no need to initialize list on first entry.
        self._callbacks[type].append(callback)

    def on_data(self, data: Union[bytes, int]) -> List[Union[MessageTuple, MessageWithBytesTuple]]:
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
                - If `return_bytes == True`, each list entry will include a third value containing the uninterpreted
                message contents (including the header).
                - If `return_offset == True`, each list entry will include a fourth value containing the message byte
                offset within the data stream..
        """
        # Cast singleton byte values to a byte array.
        if isinstance(data, int):
            data = data.to_bytes(1, 'big')

        if len(data) == 0:
            return []

        # Append the new data to the buffer.
        self._buffer += data

        # Decode all messages found in the buffer.
        decoded_messages = []
        while self._buffer:
            # Message must be at least long enough for header.
            if len(self._buffer) < MessageHeader.calcsize():
                break
            # Looking for a valid header.
            elif self._header is None:
                # Explicitly check for the first two sync bytes to be a bit more efficient then doing it inside the @ref
                # MessageHeader.unpack() with an exception.
                if self._buffer[0] != MessageHeader._SYNC0:
                    self._buffer.pop(0)
                    self._bytes_processed += 1
                    continue
                if self._buffer[1] != MessageHeader._SYNC1:
                    self._buffer.pop(0)
                    self._bytes_processed += 1
                    continue

                # Possible header found. Decode it and wait for the payload.
                self._header = MessageHeader()
                self._header.unpack(self._buffer, warn_on_unrecognized=False)
                self._msg_len = self._header.payload_size_bytes + MessageHeader.calcsize()
                if self._header.payload_size_bytes > self._max_payload_len_bytes:
                    print_func = _logger.warning if self._warn_on_error else _logger.debug
                    print_func('Message payload too big. [payload_size=%d B, max=%d B]',
                               self._header.payload_size_bytes, self._max_payload_len_bytes)
                    self._header = None
                    self._buffer.pop(0)
                    self._bytes_processed += 1
                    continue

            # If there's not enough data to complete the message, we're done looping.
            if len(self._buffer) < self._msg_len:
                break

            # Validate the CRC. This will raise an exception on CRC failure.
            try:
                self._header.validate_crc(self._buffer)
            # Invalid CRC detected.
            except Exception as e:
                print_func = _logger.warning if self._warn_on_error else _logger.debug
                print_func(e)
                self._header = None
                self._msg_len = 0
                self._buffer.pop(0)
                self._bytes_processed += 1
                continue

            # Check for sequence number gaps.
            if self._last_sequence_number is not None and self._warn_on_seq_skip:
                expected_sequence_number = (self._last_sequence_number + 1) % 2**32
                if self._header.sequence_number != expected_sequence_number:
                    _logger.warning("Gap detected in FusionEngine message sequence numbers. [expected=%d, "
                                    "received=%d].",
                                    expected_sequence_number, self._header.sequence_number)
            self._last_sequence_number = self._header.sequence_number

            # Get the class for the received message type and deserialize the message payload. If cls is not None, it is
            # a child of @ref MessagePayload that maps to the received @ref MessageType.
            cls = message_type_to_class.get(self._header.message_type, None)
            if cls is not None:
                contents = cls()
                try:
                    contents.unpack(buffer=self._buffer, offset=MessageHeader.calcsize())
                except Exception as e:
                    # unpack() may fail if the payload length in the header differs from the length expected by the
                    # class, the payload contains an illegal value, etc.
                    _logger.error('Error deserializing message %s payload: %s', self._header.get_type_string(), e)
                    self._header = None
                    self._msg_len = 0
                    self._buffer.pop(0)
                    self._bytes_processed += 1
                    continue
                _logger.debug('Decoded FusionEngine message %s.', repr(contents))
            # If cls is None, we don't have a class for the message type. Return a copy of the payload bytes.
            else:
                contents = bytes(self._buffer[MessageHeader.calcsize():self._msg_len])
                print_func = _logger.warning if self._warn_on_unrecognized else _logger.debug
                print_func('Decoded unknown FusionEngine message. [type=%d, payload_size=%d B]',
                           self._header.message_type, self._header.payload_size_bytes)

            # Store the result.
            result = [self._header, contents]
            if self._return_bytes:
                result.append(self._buffer[:self._msg_len])
            if self._return_offset:
                result.append(self._bytes_processed)

            decoded_messages.append(result)

            # Call any callbacks registered for this message type.
            #
            # self._callbacks is a `defaultdict(list)` and returns an empty list ([]) if the key is not found.
            for callback in self._callbacks[self._header.message_type]:
                # Unpack results so that the callback is called as:
                #   callback(header, contents)
                callback(*result)

            # Callbacks registered with type None should receive all message types.
            for callback in self._callbacks[None]:
                # Unpack results so that the callback is called as:
                #   callback(header, contents)
                callback(*result)

            # Move decoder past the current message.
            self._bytes_processed += self._msg_len
            self._buffer = self._buffer[self._msg_len:]
            self._header = None
            self._msg_len = 0

        # Return the list of decoded messages.
        return decoded_messages
