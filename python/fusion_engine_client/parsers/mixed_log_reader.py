from typing import Iterable, Union

import copy
from datetime import datetime
import os
import sys

import numpy as np

from . import file_index
from ..messages import MessageType, MessageHeader, MessagePayload, Timestamp, message_type_to_class
from ..utils import trace as logging
from ..utils.time_range import TimeRange


class MixedLogReader(object):
    """!
    @brief Generator class for decoding FusionEngine messages contained in a mixed-content binary file.

    For real-time deserialization of an incoming binary data stream, see @ref FusionEngineDecoder.
    """
    logger = logging.getLogger('point_one.fusion_engine.parsers.mixed_log_reader')

    def __init__(self, input_file, warn_on_gaps: bool = False, show_progress: bool = False,
                 generate_index: bool = True, ignore_index: bool = False, max_bytes: int = None,
                 time_range: TimeRange = None, message_types: Union[Iterable[MessageType], MessageType] = None,
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
        @param time_range An optional @ref TimeRange object specifying desired start and end time bounds of the data to
               be read. See @ref TimeRange for more details.
        @param message_types A list of one or more @ref fusion_engine_client.messages.defs.MessageType "MessageTypes" to
               be returned. If `None` or an empty list, read all available messages.
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

        self._original_time_range = copy.deepcopy(time_range)
        self.time_range = copy.deepcopy(self._original_time_range)

        self.remove_invalid_p1_time = False

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

        self._original_message_types = copy.deepcopy(self.message_types)
        self.filtered_message_types = self.message_types is not None

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
        self._original_index = None
        self.index = None
        self.next_index_elem = 0
        if ignore_index:
            if os.path.exists(self.index_path):
                if generate_index:
                    self.logger.debug("Deleting/regenerating index file @ '%s'." % self.index_path)
                    os.remove(self.index_path)
                else:
                    self.logger.debug("Ignoring index file @ '%s'." % self.index_path)
        else:
            if os.path.exists(self.index_path):
                try:
                    self.logger.debug("Loading index file '%s'." % self.index_path)
                    self._original_index = file_index.FileIndex(index_path=self.index_path, data_path=input_path,
                                                                delete_on_error=generate_index)
                    self.index = self._original_index[self.message_types][self.time_range]
                    self.filtered_message_types = len(np.unique(self._original_index.type)) != \
                                                  len(np.unique(self.index.type))
                except ValueError as e:
                    self.logger.error("Error loading index file: %s" % str(e))
            else:
                self.logger.debug("No index file found @ '%s'." % self.index_path)

        self.index_builder = None
        self.set_generate_index(generate_index)

    def rewind(self):
        self.logger.debug('Rewinding to the start of the file.')

        if self.time_range is not None:
            self.time_range.restart()

        if self._original_time_range is not None:
            self._original_time_range.restart()

        self.valid_count = 0
        self.message_counts = {}
        self.prev_sequence_number = None
        self.total_bytes_read = 0

        self.last_print_bytes = 0
        self.start_time = datetime.now()

        self.next_index_elem = 0
        self.input_file.seek(0, os.SEEK_SET)

        if self.index_builder is not None:
            self.index_builder = file_index.FileIndexBuilder()

    def seek_to_eof(self):
        self._read_next(force_eof=True)

    def reached_eof(self):
        if self.index is None:
            return self.total_bytes_read == self.file_size_bytes
        else:
            return self.next_index_elem == len(self.index)

    def have_index(self):
        return self._original_index is not None

    def get_index(self):
        return self._original_index

    def generating_index(self):
        return self.index_builder is not None

    def set_generate_index(self, generate_index):
        if self._original_index is None:
            if generate_index:
                self.logger.debug("Generating index file '%s'." % self.index_path)
                self.index_builder = file_index.FileIndexBuilder()
            else:
                self.logger.debug("Index generation disabled.")
                self.index_builder = None

    def set_show_progress(self, show_progress):
        self.show_progress = show_progress

    def set_max_bytes(self, max_bytes):
        if max_bytes is None:
            self.max_bytes = sys.maxsize
        else:
            self.max_bytes = max_bytes
            if self.index_builder is not None:
                self.logger.debug('Max bytes specified. Disabling index generation.')
                self.set_generate_index(False)

    def get_bytes_read(self):
        return self.total_bytes_read

    def next(self):
        return self.read_next()

    def read_next(self, require_p1_time=False, require_system_time=False, generate_index=True):
        return self._read_next(require_p1_time=require_p1_time, require_system_time=require_system_time,
                               generate_index=generate_index)

    def _read_next(self, require_p1_time=False, require_system_time=False, generate_index=True, force_eof=False):
        if force_eof:
            if not self.reached_eof():
                if self.generating_index():
                    raise ValueError('Cannot jump to EOF while building an index file.')

                self.logger.debug('Forcibly seeking to EOF.')
                if self.index is None:
                    self.input_file.seek(self.file_size_bytes, os.SEEK_SET)
                    self.total_bytes_read = self.file_size_bytes
                elif len(self.index) == 0:
                    self.next_index_elem = 0
                    self.total_bytes_read = 0
                else:
                    # Read the header of the last element so we can set total_bytes_read equal to the end of the index.
                    # We're not actually going to return this message.
                    offset_bytes = self.index.offset[-1]
                    self.input_file.seek(offset_bytes, os.SEEK_SET)
                    data = self.input_file.read(MessageHeader.calcsize())
                    header = MessageHeader()
                    header.unpack(data, warn_on_unrecognized=False)
                    self.total_bytes_read = offset_bytes + header.get_message_size()
                    self.next_index_elem = len(self.index)
            else:
                return

        while True:
            if not self._advance_to_next_sync():
                # End of file.
                self.logger.debug('EOF reached.')
                break

            start_offset_bytes = self.total_bytes_read
            self._print_progress()

            if start_offset_bytes + MessageHeader.calcsize() > self.max_bytes:
                self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                break

            if self.logger.isEnabledFor(logging.getTraceLevel(depth=2)):
                self.logger.trace('Reading candidate message @ %d (0x%x).' % (start_offset_bytes, start_offset_bytes),
                                  depth=2)

            # Read the next message header.
            data = self.input_file.read(MessageHeader.calcsize())
            read_len = len(data)
            self.total_bytes_read += len(data)
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
                    raise ValueError('Payload size (%d) too large. [message_type=%s]' %
                                     (header.payload_size_bytes, header.get_type_string()))

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
                self.total_bytes_read += len(payload_bytes)
                if len(payload_bytes) != header.payload_size_bytes:
                    raise ValueError('Not enough data - likely not a valid FusionEngine header. [message_type=%s]' %
                                     header.get_type_string())

                data += payload_bytes
                header.validate_crc(data)

                message_length_bytes = MessageHeader.calcsize() + header.payload_size_bytes
                if self.logger.isEnabledFor(logging.getTraceLevel(depth=1)):
                    self.logger.trace('Read %s message @ %d (0x%x). [length=%d B, sequence=%d, # messages=%d]' %
                                      (header.get_type_string(), start_offset_bytes, start_offset_bytes,
                                       message_length_bytes, header.sequence_number, self.valid_count + 1),
                                      depth=1)

                if start_offset_bytes + message_length_bytes > self.max_bytes:
                    self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                    break

                self.valid_count += 1
                self.message_counts.setdefault(header.message_type, 0)
                self.message_counts[header.message_type] += 1

                # Check for sequence number gaps. If we're filtering to just specific message types, we'll likely have
                # gaps since we're omitting messages, so we'll skip this check.
                if not self.filtered_message_types and \
                   self.prev_sequence_number is not None and \
                   (header.sequence_number - self.prev_sequence_number) != 1 and \
                   not (header.sequence_number == 0 and self.prev_sequence_number == 0xFFFFFFFF):
                    func = self.logger.warning if self.warn_on_gaps else self.logger.debug
                    func('Data gap detected @ %d (0x%x). [sequence=%d, gap_size=%d, total_messages=%d]' %
                         (start_offset_bytes, start_offset_bytes, header.sequence_number,
                          header.sequence_number - self.prev_sequence_number, self.valid_count + 1))
                self.prev_sequence_number = header.sequence_number

                # Deserialize the payload if we need it.
                need_payload = self.return_payload or \
                               self.time_range is not None or \
                               require_p1_time or require_system_time or \
                               (self.index_builder is not None and generate_index)

                if need_payload:
                    cls = message_type_to_class.get(header.message_type, None)
                    if cls is not None:
                        try:
                            payload = cls()
                            payload.unpack(buffer=payload_bytes, offset=0, message_version=header.message_version)
                        except Exception as e:
                            self.logger.error("Error parsing %s message: %s" % (header.get_type_string(), str(e)))
                            payload = None
                    else:
                        payload = None

                    if require_p1_time and (payload is None or payload.get_p1_time() is None):
                        self.logger.trace("Skipping %s message. P1 time requested." % header.get_type_string())
                        continue
                    elif require_system_time and (payload is None or payload.get_system_time_ns() is None):
                        self.logger.trace("Skipping %s message. System time requested." % header.get_type_string())
                        continue

                # Extract P1 time if available.
                p1_time = payload.get_p1_time() if payload is not None else Timestamp()

                # Add this message to the index file.
                if self.index_builder is not None and generate_index:
                    self.index_builder.append(message_type=header.message_type, offset_bytes=start_offset_bytes,
                                              p1_time=p1_time)

                # Now, if this message is not in the user-specified filter criteria, skip it.
                #
                # If we have an index available, this is implied by the index (we won't seek to messages that don't meet
                # the criteria at all), so we do not need to do this check. Further, self.message_types and
                # self.time_range are _only_ valid if we are _not_ using an index, so this may end up incorrectly
                # filtering out some messages as unwanted.
                if self.index is None:
                    if self.message_types is not None and header.message_type not in self.message_types:
                        self.logger.trace("Message type not requested. Skipping.", depth=1)
                        continue
                    elif self.remove_invalid_p1_time and not p1_time:
                        self.logger.trace("Message does not have valid P1 time. Skipping.", depth=1)
                        continue
                    elif self.time_range is not None and not self.time_range.is_in_range(payload):
                        if self.time_range.in_range_started() and (self.index_builder is None or not generate_index):
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
                    result.append(start_offset_bytes)
                return result
            except ValueError as e:
                start_offset_bytes += 1
                if self.logger.isEnabledFor(logging.getTraceLevel(depth=2)):
                    self.logger.trace('%s Rewinding to offset %d (0x%x).' %
                                      (str(e), start_offset_bytes, start_offset_bytes),
                                      depth=2)
                self.input_file.seek(start_offset_bytes, os.SEEK_SET)
                self.total_bytes_read = start_offset_bytes

        # Out of the loop - EOF reached.
        self._print_progress(self.total_bytes_read)
        self.logger.debug("Read %d bytes total." % self.total_bytes_read)

        # If we are creating an index file, save it now.
        if self.index_builder is not None and generate_index:
            self.logger.debug("Saving index file as '%s'." % self.index_path)
            self._original_index = self.index_builder.save(self.index_path, self.input_file.name)
            self.index_builder = None

            self.index = self._original_index[self.message_types][self.time_range]
            if self.remove_invalid_p1_time:
                self.index = self.index.get_time_range(hint='remove_nans')
            self.message_types = None
            self.time_range = None
            self.next_index_elem = len(self.index)

        # Finished iterating.
        if force_eof:
            return
        else:
            raise StopIteration()

    def _advance_to_next_sync(self):
        if self.index is None:
            try:
                if self.logger.isEnabledFor(logging.getTraceLevel(depth=2)):
                    self.logger.trace('Starting next sync search @ %d (0x%x).' %
                                      (self.total_bytes_read, self.total_bytes_read),
                                      depth=2)
                while True:
                    if self.total_bytes_read + 1 >= self.max_bytes:
                        self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                        return False

                    byte0 = self.input_file.read(1)[0]
                    self.total_bytes_read += 1
                    while True:
                        if byte0 == MessageHeader.SYNC0:
                            if self.total_bytes_read + 1 >= self.max_bytes:
                                self.logger.debug('Max read length exceeded (%d B).' % self.max_bytes)
                                return False

                            byte1 = self.input_file.read(1)[0]
                            self.total_bytes_read += 1
                            if byte1 == MessageHeader.SYNC1:
                                self.input_file.seek(-2, os.SEEK_CUR)
                                self.total_bytes_read -= 2
                                if self.logger.isEnabledFor(logging.getTraceLevel(depth=3)):
                                    self.logger.trace('Sync bytes found @ %d (0x%x).' %
                                                      (self.total_bytes_read, self.total_bytes_read),
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
                offset_bytes = self.index.offset[self.next_index_elem]
                self.next_index_elem += 1
                self.input_file.seek(offset_bytes, os.SEEK_SET)
                self.total_bytes_read = offset_bytes
                return True

    def _print_progress(self, file_size=None):
        show_progress = self.show_progress

        # If this function is being called when we're done reading (file_size not None), and we used an index file which
        # did not have any entries for the requested set of data filters, don't print an info print stating "processed
        # 0/0 bytes". It's more confusing than helpful.
        if file_size is not None and self.index is not None and self.total_bytes_read == 0:
            show_progress = False

        if file_size is None:
            file_size = min(self.file_size_bytes, self.max_bytes)

        if self.total_bytes_read - self.last_print_bytes > 10e6 or self.total_bytes_read == file_size:
            elapsed_sec = (datetime.now() - self.start_time).total_seconds()
            self.logger.log(logging.INFO if show_progress else logging.DEBUG,
                            'Processed %d/%d bytes (%.1f%%). [elapsed=%.1f sec, rate=%.1f MB/s]' %
                            (self.total_bytes_read, file_size,
                             100.0 if file_size == 0 else 100.0 * float(self.total_bytes_read) / file_size,
                             elapsed_sec, (self.total_bytes_read / elapsed_sec / 1e6) if elapsed_sec > 0 else np.nan))
            self.last_print_bytes = self.total_bytes_read

    def clear_filters(self):
        self.filter_in_place(key=None, clear_existing=True)

    def filter_in_place(self, key, clear_existing: bool = False):
        """!
        @brief Limit the returned messages by type or time.

        @warning
        This operator modifies this class in-place.

        @param key One of the following:
               - An individual @ref MessageType to be returned
               - An iterable listing one or more @ref MessageType%s to be returned
               - A `slice` specifying the start/end of the desired absolute (P1) or relative time range
               - A @ref TimeRange object
        @param clear_existing If `True`, clear any previous filter criteria.

        @return A reference to this class.
        """
        # If we're reading using an index, determine the offset within the data file of the most recent message we have
        # read. Then below, after we filter the index down (or clear existing filtering), we'll locate the next entry to
        # be read in the file that meets the new criteria. That way we continue where we left off.
        #
        # If we're reading directly from the file without an index, we'll just pick up where the current seek is, so no
        # need to do anything special.
        if self.index is not None:
            if self.next_index_elem == 0:
                prev_offset_bytes = -1
            else:
                # Note that next_index_elem refers to the _next_ message to be read. We want the offset of the message
                # that we just read.
                prev_offset_bytes = self.index.offset[self.next_index_elem - 1]

        # If requested, clear previous filter criteria.
        if clear_existing:
            if self.index is None:
                self.message_types = copy.deepcopy(self._original_message_types)
                self.time_range = copy.deepcopy(self._original_time_range)
                self.remove_invalid_p1_time = False
            else:
                self.index = self._original_index

        # No key specified (convenience case).
        if key is None:
            pass
        # If we have an index file available, reduce the index to the requested criteria.
        elif self.index is not None:
            self.index = self.index[key]
            self.filtered_message_types = len(np.unique(self._original_index.type)) != \
                                          len(np.unique(self.index.type))
        # Otherwise, store the criteria and apply them while reading.
        else:
            # Return entries for a specific message type.
            if isinstance(key, MessageType):
                self.message_types = set((key,))
                self.filtered_message_types = True
            elif MessagePayload.is_subclass(key):
                self.message_types = set((key.get_type(),))
                self.filtered_message_types = True
            # Return entries for a list of message types.
            elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(next(iter(key)), MessageType):
                new_message_types = {t for t in key if t is not None}
                if self.message_types is None:
                    self.message_types = new_message_types
                else:
                    self.message_types = self.message_types & new_message_types
                self.filtered_message_types = True
            elif isinstance(key, (set, list, tuple)) and len(key) > 0 and MessagePayload.is_subclass(next(iter(key))):
                new_message_types = set([t.get_type() for t in key if t is not None])
                if self.message_types is None:
                    self.message_types = new_message_types
                else:
                    self.message_types = self.message_types & new_message_types
                self.filtered_message_types = True
            # Key is a slice in time. Return a subset of the data.
            elif isinstance(key, slice) and (isinstance(key.start, (Timestamp, float)) or
                                             isinstance(key.stop, (Timestamp, float))):
                time_range = TimeRange(start=key.start, end=key.stop, absolute=isinstance(key.start, Timestamp))
                if self.time_range is None:
                    self.time_range = time_range
                else:
                    self.time_range.intersect(time_range, in_place=True)
            # Key is a slice by index (# of messages). Return a subset of the index file.
            #
            # Note: Slicing is not supported if there is no index file. Slicing with an index file is handled above.
            elif isinstance(key, slice) and (isinstance(key.start, int) or isinstance(key.stop, int)):
                raise ValueError('Index slicing not supported when an index file is not present.')
            # Key is a TimeRange object. Return a subset of the data. All nan elements (messages without P1 time) will
            # be included in the results.
            elif isinstance(key, TimeRange):
                if self.time_range is None:
                    self.time_range = key
                else:
                    self.time_range.intersect(key, in_place=True)

        # Now, find the next entry in the newly filtered index starting after the most recent message we read. That
        # way we can continue reading where we left off.
        if self.index is not None:
            if len(self.index) == 0:
                self.next_index_elem = 0
            else:
                idx = np.argmax(self.index.offset > prev_offset_bytes)
                if idx == 0 and self.index.offset[0] <= prev_offset_bytes:
                    self.next_index_elem = len(self.index)
                else:
                    self.next_index_elem = idx

        return self

    def filter_out_invalid_p1_times(self, clear_existing: bool = False):
        """!
        @brief Limit the returned messages, removing any messages that do not have valid P1 time.

        @param clear_existing If `True`, clear any previous filter criteria.

        @return A reference to this class.
        """
        self.filter_in_place(key=None, clear_existing=clear_existing)

        # If we have an index file available, reduce the index to the requested criteria.
        if self.index is not None:
            self.index = self.index.get_time_range(hint='remove_nans')
            self.filtered_message_types = len(np.unique(self._original_index.type)) != \
                                          len(np.unique(self.index.type))
        else:
            self.remove_invalid_p1_time = True

        return self

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    @classmethod
    def generate_index_file(cls, input_file):
        reader = MixedLogReader(input_file=input_file, ignore_index=False, generate_index=True, return_payload=False)
        if reader.index is None:
            for _ in reader:
                pass
