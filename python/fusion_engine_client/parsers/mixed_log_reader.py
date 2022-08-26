import logging
import os

from ..analysis import file_index
from ..messages import MessageType, MessageHeader, Timestamp, message_type_to_class
from ..utils.time_range import TimeRange


class MixedLogReader(object):
    """!
    @brief Generator class for decoding FusionEngine messages contained in a mixed-content binary file.

    For real-time deserialization of an incoming binary data stream, see @ref FusionEngineDecoder.
    """
    logger = logging.getLogger('point_one.fusion_engine.parsers.mixed_log_reader')

    def __init__(self, input_file, warn_on_gaps: bool = False,
                 generate_index: bool = True, ignore_index: bool = False,
                 time_range: TimeRange = None, message_types: set = None,
                 return_header: bool = True, return_payload: bool = True,
                 return_bytes: bool = False, return_offset: bool = False):
        """!
        @brief Construct a new generator instance.

        Each call to @ref next() will return a tuple containing any/all of the message header, payload, serialized
        `bytes`, and byte offset depending on the values of the `return_*` parameters.

        @param input_file The path to an input file (`.p1log` or mixed-content binary file), or an open file-like
               object.
        @param warn_on_gaps If `True`, print warnings if gaps are detected in the FusionEngine message sequence numbers.
        @param generate_index If `True`, generate an index file if one does not exist for faster reading in the future.
               See @ref FileIndex for details.
        @param ignore_index If `True`, ignore the existing index file and read from the binary file directly. If
               `generate_index == True`, this will delete the existing file and create a new one.
        @param return_header If `True`, return the decoded @ref MessageHeader for each message.
        @param return_payload If `True`, parse and return the payload for each message as a subclass of @ref
               MessagePayload. Will return `None` if the payload cannot be parsed.
        @param return_bytes If `True`, return a `bytes` object containing the serialized message header and payload.
        @param return_offset If `True`, return the offset into the file (in bytes) at which the message began.
        """
        self.warn_on_gaps = warn_on_gaps

        self.return_header = return_header
        self.return_payload = return_payload
        self.return_bytes = return_bytes
        self.return_offset = return_offset

        self.time_range = time_range
        self.message_types = message_types

        self.valid_count = 0
        self.message_counts = {}
        self.prev_sequence_number = None
        self.total_bytes_read = 0

        # Open the file to be read.
        if isinstance(input_file, str):
            self.input_file = open(input_file, 'rb')
        else:
            self.input_file = input_file

        # Open the companion index file if one exists.
        input_path = self.input_file.name
        self.index_path = file_index.FileIndex.get_path(input_path)
        self.next_index_elem = 0
        if ignore_index:
            self.index = None
            self.index_builder = file_index.FileIndexBuilder() if generate_index else None
        else:
            if os.path.exists(self.index_path):
                try:
                    self.index = file_index.FileIndex(index_path=self.index_path, data_path=input_path,
                                                      delete_on_error=generate_index)
                    self.index = self.index[self.message_types][self.time_range]
                    self.index_builder = None
                except ValueError as e:
                    self.logger.error("Error loading index file: %s" % str(e))
                    self.index = None
                    self.index_builder = file_index.FileIndexBuilder() if generate_index else None

        if self.index_builder is not None:
            self.logger.debug("Generating index file '%s'." % self.index_path)

    def have_index(self):
        return self.index is not None

    def get_index(self):
        return self.index

    def generating_index(self):
        return self.index_builder is not None

    def get_bytes_read(self):
        return self.total_bytes_read

    def next(self):
        while True:
            if not self._advance_to_next_sync():
                # End of file.
                self.total_bytes_read = self.input_file.tell()
                self.logger.debug('EOF reached.')
                break

            offset_bytes = self.input_file.tell()
            self.total_bytes_read = offset_bytes
            self.logger.trace('Reading candidate message @ %d (0x%x).' % (offset_bytes, offset_bytes), depth=2)

            # Read the next message header.
            data = self.input_file.read(MessageHeader.calcsize())
            read_len = len(data)
            if read_len < MessageHeader.calcsize():
                # End of file.
                self.logger.debug('EOF reached.')
                break

            try:
                header = MessageHeader()
                header.unpack(data, warn_on_unrecognized=False)

                # Check if the payload is too big.
                if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                    raise ValueError('Payload size (%d) too large.' % header.payload_size_bytes)

                # Read and validate the payload.
                payload_bytes = self.input_file.read(header.payload_size_bytes)
                read_len += len(payload_bytes)
                if len(payload_bytes) != header.payload_size_bytes:
                    raise ValueError('Not enough data - likely not a valid FusionEngine header.')

                data += payload_bytes
                header.validate_crc(data)

                self.logger.trace('Read %s message @ %d (0x%x). [length=%d B, sequence=%d, # messages=%d]' %
                                  (header.get_type_string(), offset_bytes, offset_bytes,
                                   MessageHeader.calcsize() + header.payload_size_bytes, header.sequence_number,
                                   self.valid_count + 1),
                                  depth=1)

                self.valid_count += 1
                self.message_counts.setdefault(header.message_type, 0)
                self.message_counts[header.message_type] += 1

                # Check for sequence number gaps.
                if self.prev_sequence_number is not None and \
                   (header.sequence_number - self.prev_sequence_number) != 1 and \
                   not (header.sequence_number == 0 and self.prev_sequence_number == 0xFFFFFFFF):
                    func = self.logger.warning if self.warn_on_gaps else self.logger.debug
                    func('Data gap detected @ %d (0x%x). [sequence=%d, gap_size=%d, total_messages=%d]' %
                         (offset_bytes, offset_bytes, header.sequence_number,
                          header.sequence_number - self.prev_sequence_number, self.valid_count + 1))
                self.prev_sequence_number = header.sequence_number

                # Deserialize the payload if we need it.
                need_payload = self.return_payload or self.index_builder is not None or self.time_range is not None
                if need_payload:
                    cls = message_type_to_class.get(header.message_type, None)
                    if cls is not None:
                        try:
                            payload = cls()
                            payload.unpack(buffer=payload_bytes, offset=0)
                        except Exception as e:
                            self.logger.error("Error parsing %s message: %s" % (header.get_type_string(), str(e)))
                            payload = None
                    else:
                        payload = None

                # Add this message to the index file.
                if self.index_builder is not None:
                    p1_time = payload.get_p1_time() if payload is not None else None
                    self.index_builder.append(message_type=header.message_type, offset_bytes=offset_bytes,
                                              p1_time=p1_time)

                # Now, if this message is not in the user-specified filter criteria, skip it.
                if self.message_types is not None and header.message_type not in self.message_types:
                    self.logger.debug("Message type not requested. Skipping.")
                    continue
                elif self.time_range is not None and not self.time_range.is_in_range(payload):
                    if self.time_range.in_range_started() and self.index_builder is None:
                        self.logger.debug("End of time range reached. Finished processing.")
                        break
                    else:
                        self.logger.debug("Message not in time range. Skipping.")
                        continue

                # Construct the result. If we're returning the payload, deserialize the payload.
                result = []
                if self.return_header:
                    result.append(header)
                if self.return_payload:
                    result.append(payload)
                if self.return_bytes:
                    result.append(data)
                if self.return_offset:
                    result.append(offset_bytes)
                return result
            except ValueError as e:
                offset_bytes += 1
                self.logger.trace('%s Rewinding to offset %d (0x%x).' % (str(e), offset_bytes, offset_bytes),
                                  depth=2)
                self.input_file.seek(offset_bytes, os.SEEK_SET)

        # Out of the loop - EOF reached.
        self.logger.debug("Read %d bytes total." % self.total_bytes_read)

        # If we are creating an index file, save it now.
        if self.index_builder is not None:
            index = self.index_builder.to_index()
            index.save(self.index_path)

        # Finished iterating.
        raise StopIteration()

    def _advance_to_next_sync(self):
        if self.index is None:
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
        else:
            if self.next_index_elem == len(self.index):
                return False
            else:
                offset_bytes = self.index._data['offset'][self.next_index_elem]
                self.next_index_elem += 1
                self.input_file.seek(offset_bytes, os.SEEK_SET)
                return True

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def __getitem__(self, key):
        """!
        @brief Limit the returned messages by type or time.

        @warning
        This operator modifies this class in-place.

        @param key One of the following:
               - An individual @ref MessageType to be returned
               - An iterable listing one or more @ref MessageType%s to be returned
               - A `slice` specifying the start/end of the desired absolute (P1) or relative time range
               - A @ref TimeRange object
        """
        # No key specified (convenience case).
        if key is None:
            pass
        # If we have an index file available, reduce the index to the requested criteria.
        elif self.index is not None:
            self.index = self.index[key]
        # Otherwise, store the criteria and apply them while reading.
        else:
            # Return entries for a specific message type.
            if isinstance(key, MessageType):
                self.message_types = set((key,))
            # Return entries for a list of message types.
            elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(next(iter(key)), MessageType):
                current_types = set(self.message_types) if self.message_types is not None else set()
                self.message_types = current_types & set(key)
            # Key is a slice in time. Return a subset of the data.
            elif isinstance(key, slice) and (isinstance(key.start, (Timestamp, float)) or
                                             isinstance(key.stop, (Timestamp, float))):
                time_range = TimeRange(start=key.start, end=key.stop, absolute=isinstance(key.start, Timestamp))
                if self.time_range is None:
                    self.time_range = time_range
                else:
                    self.time_range.intersect(time_range, in_place=True)
            # Key is a TimeRange object. Return a subset of the data. All nan elements (messages without P1 time) will
            # be included in the results.
            elif isinstance(key, TimeRange):
                if self.time_range is None:
                    self.time_range = key
                else:
                    self.time_range.intersect(key, in_place=True)
        return self
