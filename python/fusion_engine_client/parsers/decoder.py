from collections import defaultdict
from typing import Iterable, List, Dict, Callable, Optional, Tuple, Union
from zlib import crc32

from ..messages import MessageHeader, MessageType, MessagePayload, message_type_to_class
from ..utils import trace as logging
from ..utils.bin_utils import bytes_to_hex
from ..utils.enum_utils import IntEnum, lookup_value

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

    @note
    For reading from a pre-recorded data file, see the more efficient @ref MixedLogReader class.
    """
    class WarnOnError(IntEnum):
        NONE = 0
        LIKELY = 1
        ALL = 2

    def __init__(self, max_payload_len_bytes: int = MessageHeader._MAX_EXPECTED_SIZE_BYTES,
                 warn_on_unrecognized: bool = False, warn_on_gap: bool = False,
                 warn_on_error: Union[bool, str, WarnOnError] = WarnOnError.LIKELY,
                 return_bytes: bool = False, return_offset: bool = False,
                 message_types: Optional[Iterable[Union[MessageType, type]]] = None, return_payload: bool = True):
        """!
        @brief Construct a new decoder instance.

        @param max_payload_len_bytes The maximum expected payload length (in bytes). Incoming headers with reported
               payload lengths larger than this value will be treated as corrupted/invalid and will trigger a
               resynchronization.
        @param warn_on_unrecognized If `True`, print a warning if a deserialized message header contains an unrecognized
               or unsupported message type.
        @param warn_on_gap If `True`, print a warning if a gap is detected in the incoming message sequence numbers.
        @param warn_on_error Print a warning if an error is detected:
               - `True`, `'all'`, @ref WarnOnError.ALL - Print for all errors (invalid CRC, invalid payload length,
                  etc.); not recommended for mixed-binary data streams
               - `'likely'`, @ref WarnOnError.LIKELY - Print only for errors where the message header appears to
                 be plausible (e.g., message type and payload length match, but CRC fails)
               - `False`, `'none'`, @ref WarnOnError.NONE - Disable all warning messages
        @param return_bytes If `True`, return a `bytes` object with the raw data (header + payload) in addition to the
               decoded message object.
        @param return_offset If `True`, the byte offset into the data stream at which the message was found.
        @param message_types If set, only return the listed message types (@ref MessageType values or @ref
               MessagePayload classes). Other messages are still validated, but are skipped without copying or
               deserializing their payloads, and do not trigger callbacks.
        @param return_payload If `False`, do not deserialize message payloads, and omit them from the returned
               results and from the callback arguments. This is much faster when only the header, bytes, or offset are
               needed.
        """
        self._warn_on_unrecognized = warn_on_unrecognized
        self._warn_on_seq_skip = warn_on_gap

        if isinstance(warn_on_error, self.WarnOnError):
            self._warn_on_error = warn_on_error
        else:
            if warn_on_error == True or warn_on_error == 'all':
                self._warn_on_error = self.WarnOnError.ALL
            elif warn_on_error == 'likely':
                self._warn_on_error = self.WarnOnError.LIKELY
            elif warn_on_error == False or warn_on_error == 'none':
                self._warn_on_error = self.WarnOnError.NONE
            else:
                raise ValueError('Unrecognized warn-on-error value.')

        self._return_bytes = return_bytes
        self._return_offset = return_offset
        self._return_payload = return_payload

        if message_types is None:
            self._message_types = None
        else:
            self._message_types = set(t.get_type() if MessagePayload.is_subclass(t) else t for t in message_types)

        self._max_payload_len_bytes = max_payload_len_bytes
        self._buffer = bytearray()
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
        # Callbacks are only called for message types allowed by the message type filter.
        if type is not None and self._message_types is not None and type not in self._message_types:
            _logger.warning('Callback registered for %s, which is excluded by the message type filter. It will not '
                            'be called.' % MessageType.get_type_string(type))

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

        # Checked up front because the messages below are not free to build: some payloads parse their own contents
        # to describe themselves, and the buffer dumps copy the data they print.
        trace_enabled = _logger.isEnabledFor(logging.TRACE)
        debug_enabled = _logger.isEnabledFor(logging.DEBUG)
        if self._warn_on_error == self.WarnOnError.ALL:
            warn_or_debug = _logger.warning
        elif debug_enabled:
            warn_or_debug = _logger.debug
        else:
            warn_or_debug = None

        if trace_enabled:
            _logger.trace('Received %d bytes. [total_received=%d B, stream_offset=%d B (0x%x)]' %
                          (len(data), self._bytes_processed + len(data), self._bytes_processed,
                           self._bytes_processed))
            self._trace_buffer(data, depth=2)

        # Append the new data to the buffer.
        self._buffer += data

        # Decode all messages found in the buffer.
        #
        # Bytes that have been consumed are tracked with a read cursor and discarded in a single pass once the buffer
        # is exhausted. Removing them as we go would copy everything after them, once per message decoded and once per
        # byte skipped while resynchronizing.
        #
        # This loop runs once per message, and on a high-rate data stream its per-message overhead dominates the
        # decoder's CPU usage. To reduce unnecessary CPU usage, it checks the header and CRC without copying the data,
        # and only builds a @ref MessageHeader for messages it returns.
        decoded_messages = []
        header_size = MessageHeader.calcsize()
        buffer = self._buffer
        buffer_len = len(buffer)
        view = memoryview(buffer)
        offset = 0
        try:
            while True:
                # Message must be at least long enough for header.
                if buffer_len - offset < header_size:
                    break

                # Check if the current and next byte match the sync pattern. If not, search for the next occurrence.
                sync0 = buffer[offset]
                sync1 = buffer[offset + 1]
                sync_detected = sync0 == MessageHeader.SYNC0 and sync1 == MessageHeader.SYNC1

                if not sync_detected:
                    sync_offset = buffer.find(MessageHeader.SYNC, offset + 1)

                    # Nothing found. Everything but the last byte can be dropped, since only that byte can be the
                    # start of a sequence split across two calls.
                    if sync_offset < 0:
                        sync_offset = buffer_len - 1

                    offset = sync_offset
                    continue

                # Possible header found. Decode it and wait for the payload.
                (_, _, reserved, crc, protocol_version, message_version, message_type_int, sequence_number,
                 payload_size_bytes, source_identifier) = MessageHeader._STRUCT.unpack_from(buffer, offset)
                msg_len = payload_size_bytes + header_size

                if trace_enabled:
                    _logger.trace('Found candidate header. [type=%s, sequence=%d, payload_size=%d B '
                                  '(total_size=%d B), stream_offset=%d B (0x%x)]' %
                                  (MessageType.get_type_string(message_type_int), sequence_number,
                                   payload_size_bytes, msg_len, self._bytes_processed + offset,
                                   self._bytes_processed + offset))
                    self._trace_buffer(buffer[offset:offset + header_size])

                # The reserved bytes in the header are currently always set to 0. If the incoming bytes are not zero,
                # assume this an invalid sync.
                #
                # This may change in the future, but for now it prevents us from needing to collect a ton of bytes
                # before performing a CRC check if a bogus header from an invalid sync has a very large payload size
                # that happens to still be smaller than the buffer size.
                if reserved != 0:
                    if warn_or_debug is not None:
                        warn_or_debug('Reserved bytes nonzero. Dropping suspected invalid sync. [type=%s, '
                                      'payload_size=%d B, max=%d B]' %
                                      (MessageType.get_type_string(message_type_int), payload_size_bytes,
                                       self._max_payload_len_bytes))
                    offset += 1
                    continue
                # If the message is too large to fit in the buffer, we cannot parse it.
                #
                # If this is an invalid sync, the parsed (invalid) payload length may  exceed the buffer size and the
                # invalid header will be dropped. If it does not exceed the buffer size, it'll get caught later during
                # the CRC check.
                elif payload_size_bytes > self._max_payload_len_bytes:
                    if warn_or_debug is not None:
                        warn_or_debug('Message payload too big. [type=%s, payload_size=%d B, max=%d B]' %
                                      (MessageType.get_type_string(message_type_int), payload_size_bytes,
                                       self._max_payload_len_bytes))
                    offset += 1
                    continue

                # If there's not enough data to complete the message, we're done looping. The next call will decode
                # the header again once more data arrives.
                end_offset = offset + msg_len
                if end_offset > buffer_len:
                    break

                # Message complete.
                if trace_enabled:
                    _logger.trace('Collected complete message. [message_size=%d B, payload_size=%d B]' %
                                  (msg_len, payload_size_bytes))
                    self._trace_buffer(buffer[offset:end_offset])

                # Validate the CRC. The memoryview avoids copying the message to compute it.
                computed_crc = crc32(view[offset + MessageHeader.CRC_START_OFFSET_BYTES:end_offset])
                if computed_crc != crc:
                    print_func = warn_or_debug

                    # Check if the expected payload size for this message type matches the received payload size. If
                    # so, it likely means the message got corrupted. For variable-length messages, this will not work
                    # since we don't know the expected size.
                    cls = message_type_to_class.get(message_type_int, None)
                    try:
                        if (cls is not None and payload_size_bytes == cls.calcsize() and
                                self._warn_on_error >= self.WarnOnError.LIKELY):
                            print_func = _logger.warning
                    except (AttributeError, TypeError):
                        pass

                    if print_func is not None:
                        print_func('CRC mismatch. [type=%s, payload_size=%d B, expected=0x%08x, computed=0x%08x]' %
                                   (MessageType.get_type_string(message_type_int), payload_size_bytes, crc,
                                    computed_crc))
                    offset += 1
                    continue

                # Check for sequence number gaps.
                if self._last_sequence_number is not None:
                    # The sequence number is a uint32 and wraps back to 0.
                    expected_sequence_number = (self._last_sequence_number + 1) & 0xFFFFFFFF
                    if sequence_number != expected_sequence_number:
                        # If we got this far, the message is valid and the CRC passed, so we expect the sequence
                        # number to go forward. If it goes backward, treat this as unexpected and warn if errors
                        # for "likely" messages are enabled.
                        if (sequence_number < self._last_sequence_number and
                                self._warn_on_error >= self.WarnOnError.LIKELY):
                            _logger.warning("Sequence number went backwards on %s message. [expected=%d, "
                                            "received=%d, payload_size=%d B, stream_offset=%d B (0x%x)].",
                                            MessageType.get_type_string(message_type_int),
                                            expected_sequence_number, sequence_number, payload_size_bytes,
                                            self._bytes_processed + offset, self._bytes_processed + offset)
                        # Otherwise, report the gap only if the user specifically requested gap reporting.
                        elif self._warn_on_seq_skip:
                            _logger.warning("Gap detected in FusionEngine message sequence numbers. "
                                            "[expected=%d, received=%d].",
                                            expected_sequence_number, sequence_number)

                self._last_sequence_number = sequence_number

                # Skip messages the user did not request.
                if self._message_types is not None and message_type_int not in self._message_types:
                    offset = end_offset
                    continue

                # Build the header for the caller.
                header = MessageHeader()
                header.reserved = reserved
                header.crc = crc
                header.protocol_version = protocol_version
                header.message_version = message_version
                header.message_type = lookup_value(MessageType, message_type_int)
                header.sequence_number = sequence_number
                header.payload_size_bytes = payload_size_bytes
                header.source_identifier = source_identifier

                # Get the class for the received message type and deserialize the message payload, if requested. If
                # cls is not None, it is a child of @ref MessagePayload that maps to the received @ref MessageType.
                #
                # The payload is copied out of the buffer rather than unpacked in place, since some payload classes
                # read to the end of the buffer they are given.
                contents = None
                if self._return_payload:
                    cls = message_type_to_class.get(message_type_int, None)
                    payload = bytes(view[offset + header_size:end_offset])
                    if cls is not None:
                        contents = cls()
                        try:
                            contents.unpack(buffer=payload, offset=0, message_version=message_version)
                            if debug_enabled:
                                _logger.debug('Decoded FusionEngine message %s.', repr(contents))
                        except NotImplementedError as e:
                            print_func = _logger.warning if self._warn_on_unrecognized else _logger.debug
                            print_func('Error deserializing message %s payload: %s', header.get_type_string(), e)
                        except Exception as e:
                            # unpack() may fail if the payload length in the header differs from the length expected
                            # by the class, the payload contains an illegal value, etc.
                            _logger.error('Error deserializing message %s payload: %s', header.get_type_string(), e)
                    # If cls is None, we don't have a class for the message type. Return a copy of the payload bytes.
                    else:
                        print_func = _logger.warning if self._warn_on_unrecognized else _logger.debug
                        print_func('Decoded unknown FusionEngine message. [type=%d, payload_size=%d B]',
                                   message_type_int, payload_size_bytes)

                    if contents is None:
                        contents = payload

                # Store the result.
                result = [header]
                if self._return_payload:
                    result.append(contents)
                if self._return_bytes:
                    result.append(buffer[offset:end_offset])
                if self._return_offset:
                    result.append(self._bytes_processed + offset)

                decoded_messages.append(result)

                # Call any callbacks registered for this message type.
                #
                # self._callbacks is a `defaultdict(list)` and returns an empty list ([]) if the key is not found.
                for callback in self._callbacks[header.message_type]:
                    # Unpack results so that the callback is called as:
                    #   callback(header, contents)
                    callback(*result)

                # Callbacks registered with type None should receive all message types.
                for callback in self._callbacks[None]:
                    # Unpack results so that the callback is called as:
                    #   callback(header, contents)
                    callback(*result)

                # Move decoder past the current message.
                offset = end_offset
        finally:
            # The buffer cannot be resized while the memoryview exists.
            view.release()

        # Discard everything consumed above, leaving any partial message for the next call.
        self._bytes_processed += offset
        if offset > 0:
            del buffer[:offset]

        # Return the list of decoded messages.
        return decoded_messages

    @classmethod
    def _trace_buffer(cls, buffer, depth=1, bytes_per_line=32):
        if _logger.isEnabledFor(logging.getTraceLevel(depth)):
            _logger.trace('\n' + bytes_to_hex(buffer, bytes_per_row=bytes_per_line), depth=depth)
