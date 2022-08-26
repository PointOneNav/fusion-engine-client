import logging
import os

from ..messages import MessageHeader, MessagePayload, message_type_to_class


class MixedLogReader(object):
    """!
    @brief Generator class for decoding FusionEngine messages contained in a mixed-content binary file.

    For real-time deserialization of an incoming binary data stream, see @ref FusionEngineDecoder.
    """
    logger = logging.getLogger('point_one.fusion_engine.parsers.mixed_log_reader')

    def __init__(self, input_file, warn_on_gaps: bool = False,
                 return_header: bool = True, return_payload: bool = True,
                 return_bytes: bool = False, return_offset: bool = False):
        """!
        @brief Construct a new generator instance.

        Each call to @ref next() will return a tuple containing any/all of the message header, payload, serialized
        `bytes`, and byte offset depending on the values of the `return_*` parameters.

        @param input_file The path to an input file (`.p1log` or mixed-content binary file), or an openp file-like
               object.
        @param warn_on_gaps If `True`, print warnings if gaps are detected in the FusionEngine message sequence numbers.
        @param return_header If `True`, return the decoded @ref MessageHeader for each message.
        @param return_payload If `True`, parse and return the payload for each for each message as a subclass of @ref
               MessagePayload. Will return `None` if the payload cannot be parsed.
        @param return_bytes If `True`, return a `bytes` object containing the serialized message header and payload.
        @param return_offset If `True`, return the offset into the file (in bytes) at which the message began.
        """
        self.warn_on_gaps = warn_on_gaps
        self.return_header = return_header
        self.return_payload = return_payload
        self.return_bytes = return_bytes
        self.return_offset = return_offset

        if isinstance(input_file, str):
            self.input_file = open(input_file, 'rb')
        else:
            self.input_file = input_file

        self.valid_count = 0
        self.message_counts = {}
        self.prev_sequence_number = None

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        while True:
            if not self._advance_to_next_sync():
                raise StopIteration()

            offset = self.input_file.tell()
            self.logger.trace('Reading candidate message @ %d (0x%x).' % (offset, offset))

            # Read the next message header.
            data = self.input_file.read(MessageHeader.calcsize())
            read_len = len(data)
            if read_len < MessageHeader.calcsize():
                # End of file.
                raise StopIteration()

            try:
                header = MessageHeader()
                header.unpack(data, warn_on_unrecognized=False)

                # Check if the payload is too big.
                if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                    raise ValueError('Payload size (%d) too large.' % header.payload_size_bytes)

                # Read and validate the payload.
                payload = self.input_file.read(header.payload_size_bytes)
                read_len += len(payload)
                if len(payload) != header.payload_size_bytes:
                    raise ValueError('Not enough data - likely not a valid FusionEngine header.')

                data += payload
                header.validate_crc(data)

                if self.prev_sequence_number is not None and \
                   (header.sequence_number - self.prev_sequence_number) != 1 and \
                   not (header.sequence_number == 0 and self.prev_sequence_number == 0xFFFFFFFF):
                    func = self.logger.warning if self.warn_on_gaps else self.logger.debug
                    func('Data gap detected @ %d (0x%x). [sequence=%d, gap_size=%d, total_messages=%d]' %
                         (offset, offset, header.sequence_number, header.sequence_number - self.prev_sequence_number,
                          self.valid_count + 1))
                self.prev_sequence_number = header.sequence_number

                self.logger.debug('Read %s message @ %d (0x%x). [length=%d B, sequence=%d, # messages=%d]' %
                                  (header.get_type_string(), offset, offset,
                                   MessageHeader.calcsize() + header.payload_size_bytes, header.sequence_number,
                                   self.valid_count + 1))

                self.valid_count += 1
                self.message_counts.setdefault(header.message_type, 0)
                self.message_counts[header.message_type] += 1

                # Construct the result. If we're returning the payload, deserialize the payload.
                result = []
                if self.return_header:
                    result.append(header)
                if self.return_payload:
                    cls = message_type_to_class.get(header.message_type, None)
                    if cls is not None:
                        try:
                            payload = cls()
                        except Exception as e:
                            payload = None
                    else:
                        payload = None
                    result.append(payload)
                if self.return_bytes:
                    result.append(data)
                if self.return_offset:
                    result.append(offset)
                return result
            except ValueError as e:
                offset += 1
                self.logger.trace('%s Rewinding to offset %d (0x%x).' % (str(e), offset, offset))
                self.input_file.seek(offset, os.SEEK_SET)

    def _advance_to_next_sync(self):
        try:
            while True:
                byte0 = self.input_file.read(1)[0]
                while True:
                    if byte0 == MessageHeader._SYNC0:
                        byte1 = self.input_file.read(1)[0]
                        if byte1 == MessageHeader._SYNC1:
                            self.input_file.seek(-2, os.SEEK_CUR)
                            return True
                        byte0 = byte1
                    else:
                        break
        except IndexError:
            return False
