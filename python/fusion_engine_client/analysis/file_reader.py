from typing import Dict, Tuple, Union

from collections import deque
from datetime import datetime
import io
import logging
import os

import numpy as np

from ..messages import *
from ..messages import internal


class MessageData(object):
    def __init__(self, message_type, params):
        self.message_type = message_type
        self.message_class = message_type_to_class.get(self.message_type, None)
        self.params = params
        self.messages = []

    def to_numpy(self, remove_nan_times: bool = True):
        """!
        @brief Convert the raw FusionEngine message data into numpy arrays that can be used for data analysis.

        On return, this function will add additional member variables to the class containing numpy arrays as returned
        by the `to_numpy()` function in the individual message data class (if supported).

        For example, if called on a @ref fusion_engine_client.messages.solution.PoseMessage "PoseMessage", this function
        will generate new members including `lla_deg`, a 3xN numpy array with the WGS-84 latitude, longitude, and
        altitude data for all available time epochs that can be used as follows:

        ```{.py}
        pose_data.to_numpy()
        mean_lla_deg = np.mean(pose_data.lla_deg, axis=1)
        ```

        @param remove_nan_times If `True`, remove entries whose P1 timestamps are `NaN` (if P1 time is available for
               this message type).
        """
        if hasattr(self.message_class, 'to_numpy'):
            have_cached_numpy_data = 'p1_time' in self.__dict__
            if have_cached_numpy_data:
                # If we don't have message data we can't do any conversion so the currently cached numpy data is as good
                # as it's gonna get. If it doesn't exist, so be it.
                if len(self.messages) == 0:
                    do_conversion = False
                else:
                    do_conversion = (len(self.messages) != len(self.p1_time) or
                                     float(self.messages[0].p1_time) != self.p1_time[0] or
                                     float(self.messages[-1].p1_time) != self.p1_time[-1])
            else:
                do_conversion = True

            if do_conversion:
                self.__dict__.update(self.message_class.to_numpy(self.messages))

                if remove_nan_times and 'p1_time' in self.__dict__:
                    is_nan = np.isnan(self.p1_time)
                    if np.any(is_nan):
                        keep_idx = ~is_nan
                        for key, value in self.__dict__.items():
                            if (key not in ('message_type', 'message_class', 'params', 'messages') and
                                isinstance(value, np.ndarray)):
                                if len(value.shape) == 1:
                                    self.__dict__[key] = value[keep_idx]
                                elif len(value.shape) == 2:
                                    if value.shape[0] == len(is_nan):
                                        # Assuming first dimension is time.
                                        self.__dict__[key] = value[keep_idx, :]
                                    elif value.shape[1] == len(is_nan):
                                        # Assuming second dimension is time.
                                        self.__dict__[key] = value[:, keep_idx]
                                    else:
                                        # Unrecognized data shape.
                                        pass
                                else:
                                    # Unrecognized data shape.
                                    pass
        else:
            raise ValueError('Message type %s does not support numpy conversion.' %
                             MessageType.get_type_string(self.message_type))


class FileIndex(object):
    # Note: To reduce the index file size, we've made the following limitations:
    # - Fractional timestamp is floored so time 123.4 becomes 123. The data read should not assume that an entry's
    #   timestamp is its exact time
    RAW_DTYPE = np.dtype([('int', '<u4'), ('type', '<u2'), ('offset', '<u8')])

    DTYPE = np.dtype([('time', '<f8'), ('type', '<u2'), ('offset', '<u8')])

    @classmethod
    def load(cls, index_path):
        raw_data = np.fromfile(index_path, dtype=cls.RAW_DTYPE)
        return cls._from_raw(raw_data)

    @classmethod
    def save(cls, index_path, data: Union[np.ndarray, list]):
        if isinstance(data, np.ndarray) and data.dtype == cls.RAW_DTYPE:
            raw_data = data
            data = cls._from_raw(raw_data)
        else:
            if isinstance(data, list):
                data = np.array(data, dtype=cls.DTYPE)

            if data.dtype == cls.DTYPE:
                raw_data = cls._to_raw(data)
            else:
                raise ValueError('Unsupported array format.')

        raw_data.tofile(index_path)
        return data

    @classmethod
    def get_path(cls, data_path):
        return os.path.splitext(data_path)[0] + '.p1i'

    @classmethod
    def _from_raw(cls, raw_data):
        idx = raw_data['int'] == Timestamp._INVALID
        data = raw_data.astype(dtype=cls.DTYPE)
        data['time'][idx] = np.nan
        return data

    @classmethod
    def _to_raw(cls, data):
        time_sec = data['time']
        idx = np.isnan(time_sec)
        raw_data = data.astype(dtype=cls.RAW_DTYPE)
        raw_data['int'][idx] = Timestamp._INVALID
        return raw_data


class FileReader(object):
    logger = logging.getLogger('point_one.fusion_engine.analysis.file_reader')

    def __init__(self, path=None):
        """!
        @brief Create a new reader instance.

        @param path The path to a FusionEngine binary file to open.
        """
        self.file = None
        self.file_size = 0
        self.data: Dict[MessageType, MessageData] = {}
        self.t0 = None
        self.posix_t0 = None
        self.posix_t0_ns = None

        self.index = None

        if path is not None:
            self.open(path)

    def open(self, path):
        """!
        @brief Open a FusionEngine binary file.

        @param path The path to the file, or an existing Python file object.
        """
        self.close()

        if isinstance(path, io.IOBase):
            self.file = path
        else:
            self.file = open(path, 'rb')

        self.file.seek(0, io.SEEK_END)
        self.file_size = self.file.tell()
        self.file.seek(0, 0)

        if self.file_size == 0:
            raise RuntimeError("File '%s' is empty." % path)

        # Load the data index file if present.
        index_path = FileIndex.get_path(self.file.name)
        if os.path.exists(index_path):
            self.logger.debug("Reading index file '%s'." % index_path)
            self.index = FileIndex.load(index_path)

            # If the index doesn't cover the full binary file, the user might have interrupted the read when it was
            # being generated. Delete it and create a new one.
            index_valid = True
            if len(self.index['time']) == 0:
                self.logger.warning("Index file '%s' is empty. Deleting." % index_path)
                index_valid = False
            else:
                last_offset = self.index['offset'][-1]
                if last_offset > self.file_size + MessageHeader.calcsize():
                    self.logger.warning("Last index entry past end of file. Deleting index.")
                    index_valid = False
                else:
                    # Read the header of the last entry to get its size.
                    self.file.seek(last_offset, io.SEEK_SET)
                    buffer = self.file.read(MessageHeader.calcsize())
                    self.file.seek(0, io.SEEK_SET)

                    header = MessageHeader()
                    header.unpack(buffer=buffer, warn_on_unrecognized=False)
                    message_size_bytes = MessageHeader.calcsize() + header.payload_size_bytes

                    index_size = last_offset + message_size_bytes
                    if index_size != self.file_size:
                        self.logger.warning("Size expected by index file does not match binary file. Deleting index.")
                        index_valid = False

            if not index_valid:
                os.remove(index_path)
                self.index = None
        else:
            self.index = None

        # Read the first message (with P1 time) in the file to set self.t0.
        #
        # Note that we explicitly set a start time since, if the time range is not specified, read() will include
        # messages that do not have P1 time. We want to make sure the 1 message is one with time.
        if self.index is None:
            self.t0 = None
            self.read(time_range=(0.0, None), max_messages=1, generate_index=False)
        else:
            idx = np.argmax(~np.isnan(self.index['time']))
            self.t0 = Timestamp(self.index['time'][idx])

    def close(self):
        """!
        @brief Close the file.
        """
        if self.file is not None:
            self.file = None

    def generate_index(self):
        """!
        @brief Generate an index file for the current binary file if one does not already exist.
        """
        if self.index is None:
            # We'll read pose data (doesn't actually matter which). Store the currently cached data and restore it when
            # we're done. That way if the user already did a read (with generate_index == False), they don't have to
            # re-read the data if they try to use it again.
            prev_data = self.data.get(MessageType.POSE, None)

            self.read(message_types=[MessageType.POSE], max_messages=1, generate_index=True)

            if prev_data is not None:
                self.data[MessageType.POSE] = prev_data

    def read(self, message_types: Union[list, tuple] = None,
             time_range: Tuple[Union[float, Timestamp], Union[float, Timestamp]] = None, absolute_time: bool = False,
             max_messages: int = None,
             return_numpy: bool = False, keep_messages: bool = False, remove_nan_times: bool = True,
             generate_index: bool = True, show_progress: bool = False,
             ignore_index: bool = False, ignore_index_max_messages: bool = False) \
            -> Dict[MessageType, MessageData]:
        """!
        @brief Read data for one or more desired message types.

        The read data will be cached internally. Subsequent reads for the same data type will return the cached data.

        @note
        This function uses a data index file to speed up reads when available. If `generate_index == True` and no index
        file exists, one will be generated automatically. In order to do this, this function must read the entire data
        file, even if it could normally return early when `max_messages` or the end of `time_range` are reached.

        @param message_types A list of one or more @ref fusion_engine_client.messages.defs.MessageType "MessageTypes" to
               be returned. If `None` or an empty list, read all available messages.
        @param time_range An optional length-2 tuple specifying desired start and end bounds on the data timestamps.
               Both the start and end values may be set to `None` to read all data.
        @param absolute_time If `True`, interpret the timestamps in `time_range` as absolute P1 times. Otherwise, treat
               them as relative to the first message in the file.
        @param max_messages If set, read up to the specified maximum number of messages. Applies across all message
               types. If negative, read the last N messages.
        @param return_numpy If `True`, convert the results to numpy arrays for analysis.
        @param keep_messages If `return_numpy == True` and `keep_messages == False`, the raw data in the `messages`
               field will be cleared for each @ref MessageData object for which numpy conversion is supported.
        @param remove_nan_times If `True`, remove messages whose P1 timestamps are `NaN` when converting to numpy.
               Ignored if `return_numpy == False`.
        @param show_progress If `True`, print the read progress every 10 MB (useful for large files).
        @param generate_index If `True` and an index file does not exist for this data file, read the entire data file
               and create an index file on the first call to this function. The file will be stored in the same
               directory as the input file.
        @param ignore_index If `True`, ignore the data index if loaded.
        @param ignore_index_max_messages If `True`, do not apply the `max_messages` limit when listing messages to be
               loaded from the data index file. `max_messages` _will_ still be applied after the data is decoded.

        @return A dictionary, keyed by @ref fusion_engine_client.messages.defs.MessageType "MessageType", containing
               @ref MessageData objects with the data read for each of the requested message types.
        """
        if message_types is None:
            message_types = []
        elif not isinstance(message_types, (list, tuple)):
            message_types = (message_types,)

        if time_range is None:
            time_range = (None, None)
            time_range_specified = False
        else:
            time_range_specified = (time_range[0] is not None or time_range[1] is not None)

        if max_messages is None:
            max_messages = 0

        params = {
            'time_range': time_range,
            'absolute_time': absolute_time,
            'max_messages': max_messages
        }

        # Allow the user to pass in a list of message classes for convenience and convert them to message types
        # automatically.
        message_types = [(t if isinstance(t, MessageType) else t.MESSAGE_TYPE) for t in message_types]

        # If the message type list is empty, read all messages.
        if len(message_types) == 0:
            message_types = list(message_type_to_class.keys())

        # If any of the requested types were already read from the file for the requested parameters, skip them.
        needed_message_types = [t for t in message_types
                                if (t not in self.data or self.data[t].params != params)]
        needed_message_types = set(needed_message_types)

        # Make cache entries for the messages to be read.
        message_class = {}
        for type in needed_message_types:
            self.data[type] = MessageData(message_type=type, params=params)

            message_class[type] = message_type_to_class.get(type, None)
            if message_class[type] is None:
                self.logger.warning('Decode not supported for message type %s. Omitting from output.' %
                                    MessageType.get_type_string(type))

        needed_message_types = [t for t in needed_message_types if message_class[t] is not None]

        # Create a dict with references to the requested types only to be returned below.
        result = {t: self.data[t] for t in message_types}

        num_needed = len(needed_message_types)
        if num_needed == 0:
            # Nothing to read. Return cached data.
            self.logger.debug('Requested data already cached. [# types=%d, start=%s, end=%s]' %
                              (len(message_types),  str(time_range[0]), str(time_range[1])))
            return result
        elif self.file is None:
            raise IOError("File not open.")

        num_total = len(message_types)
        self.logger.debug('Reading data for %d message types. [cached=%d, start=%s, end=%s, max=%d]' %
                          (num_total, num_total - num_needed, str(time_range[0]), str(time_range[1]), max_messages))

        # Set the reference time used to compare timestamps against the user-specified time range. If we don't know t0
        # yet, it will be set later. If we already loaded an index file, t0 should have been set from that.
        if absolute_time:
            p1_reference_time_sec = 0.0
        elif self.t0 is not None:
            p1_reference_time_sec = float(self.t0)
        else:
            p1_reference_time_sec = None

        # If there's an index file, use it to determine the offsets to all the messages we're interested in.
        if self.index is not None and not ignore_index:
            idx = np.full_like(self.index['time'], False, dtype=bool)
            for type in needed_message_types:
                idx = np.logical_or(idx, self.index['type'] == type)

            # If t0 has never been set, this is probably the "first message" read done in open() to set t0. Ignore the
            # time range.
            if time_range_specified and self.t0 is not None:
                limit_time = self.index['time'] - p1_reference_time_sec
                if time_range[0] is not None:
                    # Note: The index stores only the integer part of the timestamp.
                    idx = np.logical_and(idx, limit_time >= np.floor(time_range[0]))
                if time_range[1] is not None:
                    idx = np.logical_and(idx, limit_time <= time_range[1])

            data_index = self.index[idx]

            if not ignore_index_max_messages:
                if max_messages > 0:
                    data_index = data_index[:max_messages]
                elif max_messages < 0:
                    # If max is negative, take the last N entries.
                    data_index = data_index[max_messages:]

            generate_index = False
            data_offsets = data_index['offset']
        # Otherwise, seek to the start of the file and read all messages.
        else:
            data_offsets = None
            index_entries = []
            self.file.seek(0, 0)

            if generate_index:
                self.logger.debug('Reading all contents to generate index file.')

        # Read all messages meeting the criteria.
        HEADER_SIZE = MessageHeader.calcsize()

        total_bytes_read = 0
        bytes_used = 0
        message_count = 0
        index_count = 0

        if max_messages < 0:
            # Used for max_messages < 0 only.
            newest_messages = deque(maxlen=abs(max_messages))
        else:
            newest_messages = None

        last_print_bytes = 0
        start_time = datetime.now()
        while True:
            # Read the next message header. If we have an index, seek directly to the message.
            if data_offsets is not None:
                # All messages read.
                if index_count >= len(data_offsets):
                    break

                message_offset_bytes = data_offsets[index_count]
                self.file.seek(message_offset_bytes, io.SEEK_SET)
                index_count += 1
            else:
                message_offset_bytes = self.file.tell()

            buffer = self.file.read(HEADER_SIZE)
            if len(buffer) == 0:
                break

            # Deserialize the header.
            try:
                header = MessageHeader()
                header.unpack(buffer=buffer, warn_on_unrecognized=False)
                message_size_bytes = HEADER_SIZE + header.payload_size_bytes

                # Check if this is one of the message types we need. If not, continue to read the payload and then skip
                # the message below.
                try:
                    if data_offsets is not None:
                        message_needed = True
                    else:
                        message_needed = header.message_type.value in needed_message_types
                except AttributeError:
                    # If the message type was not recognized, header.message_type will be an int instead of MessageType
                    # enum. If it's not in MessageType, there's definitely no message class for it so skip it.
                    message_needed = False

                self.logger.debug('  Deserializing %s message @ %d. [length=%d B]%s' %
                                  (header.get_type_string(), message_offset_bytes, message_size_bytes,
                                   '' if message_needed else ' [skip]'))
            except Exception as e:
                self.logger.error('Error decoding header @ %d: %s' % (message_offset_bytes, repr(e)))
                break

            # Read the message payload and append it to the header.
            try:
                buffer += self.file.read(header.payload_size_bytes)
            except Exception as e:
                self.logger.error('Error reading %s payload @ %d: %s' %
                                  (header.get_type_string(), message_offset_bytes, repr(e)))
                break

            if len(buffer) != message_size_bytes:
                self.logger.warning('Unexpected EOF.')
                break

            # Validate the CRC.
            try:
                header.validate_crc(buffer)
            except ValueError as e:
                self.logger.error('Error reading %s message @ %d: %s' %
                                  (header.get_type_string(), message_offset_bytes, repr(e)))
                break

            total_bytes_read = self.file.tell()

            if total_bytes_read - last_print_bytes > 10e6:
                elapsed_sec = (datetime.now() - start_time).total_seconds()
                self.logger.log(logging.INFO if show_progress else logging.DEBUG,
                                '%sProcessed %d/%d bytes (%.1f%%). [elapsed=%.1f sec, rate=%.1f MB/s]' %
                                ('' if show_progress else '  ',
                                 total_bytes_read, self.file_size, 100.0 * float(total_bytes_read) / self.file_size,
                                 elapsed_sec, total_bytes_read / elapsed_sec / 1e6))
                last_print_bytes = total_bytes_read

            # If this isn't one of the requested messages, skip it. If we don't know t0 yet or we need the message's P1
            # time to generate an index, continue to unpack.
            if not message_needed and self.t0 is not None and not generate_index:
                continue

            # Now decode the payload.
            try:
                # Get the message class for this type and unpack the payload.
                cls = message_class.get(header.message_type, None)
                if cls is None:
                    is_reserved = int(header.message_type) >= int(MessageType.RESERVED)
                    self.logger.log(logging.DEBUG,
                                    '  Skipping message type %s @ %d. [needed=%s, reserved=%s]' %
                                    (header.get_type_string(), message_offset_bytes, repr(message_needed),
                                     repr(is_reserved)))
                    p1_time = None
                    contents = None
                else:
                    contents = cls()
                    contents.unpack(buffer=buffer, offset=HEADER_SIZE)

                    # Extract P1 time from this message, if applicable.
                    p1_time = contents.__dict__.get('p1_time', None)

                # If we're building up an index file, add an entry for this message. If this is an unrecognized message
                # type, we won't have P1 time so we'll just insert a nan.
                if generate_index:
                    index_entries.append((float(p1_time) if p1_time is not None else np.nan, int(header.message_type),
                                          message_offset_bytes))

                if contents is None:
                    # Unrecognized type - skip.
                    continue

                # Store t0 if this is the first message with a (valid) timestamp.
                if p1_time is not None and p1_time:
                    if self.t0 is None:
                        self.logger.debug('Received first message. [type=%s, time=%s]' %
                                          (header.get_type_string(), str(p1_time)))
                        self.t0 = p1_time

                        if p1_reference_time_sec is None:
                            p1_reference_time_sec = float(p1_time)

                # Now skip this message if we don't need it.
                if not message_needed:
                    continue

                # If this message has P1 time, test it against the specified range. If not, if a time range was
                # specified, skip this message since we can't be sure it's in the correct range.
                if time_range_specified:
                    if p1_time is None or not p1_time:
                        self.logger.debug('  Message does not contain time and time range specified. Discarding.')
                        continue

                    time_offset_sec = float(p1_time) - p1_reference_time_sec
                    if time_range[0] is not None and time_offset_sec < float(time_range[0]):
                        self.logger.debug('  Message before requested time range. Discarding. [time=%s]' % str(p1_time))
                        continue
                    elif time_range[1] is not None and time_offset_sec > float(time_range[1]):
                        # Assuming data is in order so if we pass the end of the time range we're done.
                        if generate_index:
                            self.logger.debug('  Message past requested time range. Discarding. [time=%s]' %
                                              str(p1_time))
                            continue
                        else:
                            self.logger.debug('  Message past requested time range. Done reading. [time=%s]' %
                                              str(p1_time))
                            break

                # Store the message.
                #
                # If we haven't reached the max message count yet, or it is 0 (disabled), store the message by type. If
                # max_messages is negative, the user requested the N latest messages. Add them to an N-length circular
                # buffer and pick off the newest ones when we're done with the file.
                message_count += 1
                if max_messages < 0:
                    newest_messages.append((header, contents))
                    bytes_used += message_size_bytes
                elif max_messages == 0 or message_count <= abs(max_messages):
                    self.data[header.message_type].messages.append(contents)
                    bytes_used += message_size_bytes

                if max_messages > 0:
                    if generate_index and message_count > max_messages:
                        self.logger.debug('  Max messages reached. Discarding. [# messages=%d]' % message_count)
                        continue
                    elif not generate_index and message_count == max_messages:
                        self.logger.debug('  Max messages reached. Done reading. [# messages=%d]' % message_count)
                        break
            except Exception as e:
                # Since the CRC passed we know we read the correct number of bytes, so if the decode fails because of
                # a format version mismatch or something, we can simply skip this message. No need to stop reading the
                # file.
                self.logger.warning('Error decoding %s payload @ %d: %s' %
                                    (header.get_type_string(), message_offset_bytes, repr(e)))

        # If the user only wanted the N newest messages, take them from the circular buffer now.
        if max_messages < 0:
            for entry in newest_messages:
                self.data[entry[0].message_type].messages.append(entry[1])

        # Print a summary.
        end_time = datetime.now()
        elapsed_sec = (end_time - start_time).total_seconds()
        self.logger.log(logging.INFO if show_progress else logging.DEBUG,
                        '%sRead %d bytes, used %d bytes. [elapsed=%s sec]' %
                        ('' if show_progress else '  ',
                         total_bytes_read, bytes_used,
                         ('%.1f' if elapsed_sec > 1.0 else '%e') % elapsed_sec))

        # Save the index file for faster reading in the future.
        if generate_index:
            index_path = FileIndex.get_path(self.file.name)
            self.logger.debug("Saving index file '%s' with %d entries." % (index_path, len(index_entries)))
            self.index = FileIndex.save(index_path, index_entries)

        # Convert the resulting message data to numpy (if supported).
        if return_numpy:
            FileReader.to_numpy(result, keep_messages=keep_messages, remove_nan_times=remove_nan_times)

        # Done.
        return result

    def get_posix_t0(self):
        if self.posix_t0 is None:
            # Determine the POSIX t0 based on the first profiling message to appear in the log.
            result = self.read(message_types=internal.PROFILING_TYPES, max_messages=1)
            if len(result) > 0:
                self.posix_t0_ns = list(result.values())[0].messages[0].posix_time_ns
                self.posix_t0 = self.posix_t0_ns * 1e-9
        return self.posix_t0

    def get_posix_t0_ns(self):
        if self.posix_t0_ns is None:
            self.get_posix_t0()
        return self.posix_t0_ns

    @classmethod
    def to_numpy(cls, data: dict, keep_messages: bool = True, remove_nan_times: bool = True):
        """!
        @brief Convert all (supported) messages in a data dictionary to numpy for analysis.

        See @ref MessageData.to_numpy().

        @param data A data dictionary as returned by @ref read().
        @param keep_messages If `False`, the raw data in the `messages` field will be cleared for each @ref MessageData
               object for which numpy conversion is supported.
        @param remove_nan_times If `True`, remove entries whose P1 timestamps are `NaN` (if P1 time is available for
               this message type).
        """
        for entry in data.values():
            try:
                entry.to_numpy(remove_nan_times=remove_nan_times)
                if not keep_messages:
                    entry.messages = []
            except ValueError:
                pass



