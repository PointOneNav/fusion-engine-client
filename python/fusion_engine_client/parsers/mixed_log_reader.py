from datetime import datetime
import logging
import os
import sys
from typing import Union

from ..analysis import file_index
from ..messages import MessageType, MessageHeader, MessagePayload, Timestamp, message_type_to_class
from ..utils.time_range import TimeRange


class MixedLogReader(object):
    """!
    @brief Generator class for decoding FusionEngine messages contained in a mixed-content binary file.

    For real-time deserialization of an incoming binary data stream, see @ref FusionEngineDecoder.
    """
    logger = logging.getLogger('point_one.fusion_engine.parsers.mixed_log_reader')

    def __init__(self, input_file, warn_on_gaps: bool = False, show_progress: bool = False,
                 generate_index: bool = True, ignore_index: bool = False, max_bytes: int = None,
                 time_range: TimeRange = None, message_types: Union[set, MessageType] = None,
                 return_header: bool = True, return_payload: bool = True,
                 return_bytes: bool = False, return_offset: bool = False):
        """!
        @brief Construct a new generator instance.

        Each call to @ref next() will return a tuple containing any/all of the message header, payload, serialized
        `bytes`, and byte offset depending on the values of the `return_*` parameters.

        @param input_file The path to an input file (`.p1log` or mixed-content binary file), or an open file-like
               object.
        @param warn_on_gaps If `True`, print warnings if gaps are detected in the FusionEngine message sequence numbers.
        @param show_progress If `True`, print file read progress to the console periodically.
        @param generate_index If `True`, generate an index file if one does not exist for faster reading in the future.
               See @ref FileIndex for details. Ignored if `max_bytes` is specified.
        @param ignore_index If `True`, ignore the existing index file and read from the binary file directly. If
               `generate_index == True`, this will delete the existing file and create a new one.
        @param max_bytes If specified, read up to the maximum number of bytes.
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
        if message_types is None:
            self.message_types = None
        elif isinstance(message_types, MessageType):
            self.message_types = set((message_types,))
        elif MessagePayload.is_subclass(message_types):
            self.message_types = set((message_types.get_type(),))
        else:
            self.message_types = set([(t.get_type() if MessagePayload.is_subclass(t) else t) for t in message_types])
            if len(self.message_types) == 0:
                self.message_types = None

        self.valid_count = 0
        self.message_counts = {}
        self.prev_sequence_number = None
        self.total_bytes_read = 0

        self.show_progress = show_progress
        self.last_print_bytes = 0
        self.start_time = datetime.now()

        # Open the file to be read.
        if isinstance(input_file, str):
            self.input_file = open(input_file, 'rb')
        else:
            self.input_file = input_file

        input_path = self.input_file.name
        self.file_size_bytes = os.stat(input_path).st_size

        if max_bytes is None:
            self.max_bytes = sys.maxsize
        else:
            self.max_bytes = max_bytes
            if generate_index:
                self.logger.debug('Max bytes specified. Disabling index generation.')
                generate_index = False

        # Open the companion index file if one exists.
        self.index_path = file_index.FileIndex.get_path(input_path)
        self.next_index_elem = 0
        if ignore_index:
            if os.path.exists(self.index_path):
                self.logger.debug("Ignoring index file @ '%s'." % self.index_path)
            self.index = None
            self.index_builder = file_index.FileIndexBuilder() if generate_index else None
        else:
            if os.path.exists(self.index_path):
                try:
                    self.logger.debug("Loading index file '%s'." % self.index_path)
                    self.index = file_index.FileIndex(index_path=self.index_path, data_path=input_path,
                                                      delete_on_error=generate_index)
                    self.index = self.index[self.message_types][self.time_range]
                    self.index_builder = None
                except ValueError as e:
                    self.logger.error("Error loading index file: %s" % str(e))
                    self.index = None
                    self.index_builder = file_index.FileIndexBuilder() if generate_index else None
            else:
                self.logger.debug("No index file found @ '%s'." % self.index_path)
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
            self._print_progress()

            if offset_bytes + MessageHeader.calcsize() > self.max_bytes:
                self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                break

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

                # Check if the payload is too big. If so, we most likely found an invalid header -- message sync bytes
                # occurring randomly in non-FusionEngine binary data in the file.
                if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                    raise ValueError('Payload size (%d) too large.' % header.payload_size_bytes)

                # Read and validate the payload.
                #
                # Note here that we can read < payload_size_bytes under 2 circumstances:
                # 1. We reached EOF unexpectedly: we found a valid message header but the file doesn't contain the
                #    complete message.
                # 2. We found an invalid header but its (bogus) payload length, while not large enough to trigger the
                #    "too big" check above, extends past the end of the file.
                #
                # In either case, we will skip past this header and see if there any further candidate headers later in
                # the file.
                #
                # If the CRC fails, either because we found an invalid header or because a valid message got corrupted,
                # validate_crc() will raise a ValueError and we will skip forward in the same manner.
                payload_bytes = self.input_file.read(header.payload_size_bytes)
                read_len += len(payload_bytes)
                if len(payload_bytes) != header.payload_size_bytes:
                    raise ValueError('Not enough data - likely not a valid FusionEngine header.')

                data += payload_bytes
                header.validate_crc(data)

                message_length_bytes = MessageHeader.calcsize() + header.payload_size_bytes
                self.logger.trace('Read %s message @ %d (0x%x). [length=%d B, sequence=%d, # messages=%d]' %
                                  (header.get_type_string(), offset_bytes, offset_bytes, message_length_bytes,
                                   header.sequence_number, self.valid_count + 1),
                                  depth=1)

                if offset_bytes + message_length_bytes > self.max_bytes:
                    self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                    break

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
                    self.logger.trace("Message type not requested. Skipping.", depth=1)
                    continue
                elif self.time_range is not None and not self.time_range.is_in_range(payload):
                    if self.time_range.in_range_started() and self.index_builder is None:
                        self.logger.debug("End of time range reached. Finished processing.")
                        break
                    else:
                        self.logger.trace("Message not in time range. Skipping.", depth=1)
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
        self._print_progress(self.total_bytes_read)
        self.logger.debug("Read %d bytes total." % self.total_bytes_read)

        # If we are creating an index file, save it now.
        if self.index_builder is not None:
            self.logger.debug("Saving index file as '%s'." % self.index_path)
            self.index_builder.save(self.index_path, self.input_file.name)

        # Finished iterating.
        raise StopIteration()

    def _advance_to_next_sync(self):
        if self.index is None:
            try:
                while True:
                    if self.input_file.tell() + 1 >= self.max_bytes:
                        self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                        return False

                    byte0 = self.input_file.read(1)[0]
                    while True:
                        if byte0 == MessageHeader._SYNC0:
                            if self.input_file.tell() + 1 >= self.max_bytes:
                                self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                                return False

                            byte1 = self.input_file.read(1)[0]
                            if byte1 == MessageHeader._SYNC1:
                                self.input_file.seek(-2, os.SEEK_CUR)
                                offset_bytes = self.input_file.tell()
                                self.logger.trace('Sync bytes found @ %d (0x%x).' % (offset_bytes, offset_bytes),
                                                  depth=3)
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

    def _print_progress(self, file_size=None):
        if file_size is None:
            file_size = min(self.file_size_bytes, self.max_bytes)

        if self.total_bytes_read - self.last_print_bytes > 10e6 or self.total_bytes_read == file_size:
            elapsed_sec = (datetime.now() - self.start_time).total_seconds()
            self.logger.log(logging.INFO if self.show_progress else logging.DEBUG,
                            'Processed %d/%d bytes (%.1f%%). [elapsed=%.1f sec, rate=%.1f MB/s]' %
                            (self.total_bytes_read, file_size,
                             100.0 if file_size == 0 else 100.0 * float(self.total_bytes_read) / file_size,
                             elapsed_sec, self.total_bytes_read / elapsed_sec / 1e6))
            self.last_print_bytes = self.total_bytes_read

    def filter_inplace(self, key):
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
            elif MessagePayload.is_subclass(key):
                self.message_types = set((key.get_type(),))
            # Return entries for a list of message types.
            elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(next(iter(key)), MessageType):
                current_types = set(self.message_types) if self.message_types is not None else set()
                new_message_types = set(key)
                self.message_types = current_types & new_message_types
            elif isinstance(key, (set, list, tuple)) and len(key) > 0 and MessagePayload.is_subclass(next(iter(key))):
                current_types = set(self.message_types) if self.message_types is not None else set()
                new_message_types = set([t.get_type() for t in key])
                self.message_types = current_types & new_message_types
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

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()
