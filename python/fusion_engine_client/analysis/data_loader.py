from enum import Enum, auto
from typing import Dict, Iterable, Union

from collections import deque
from datetime import datetime, timezone

from gpstime import gpstime, unix2gps
import numpy as np
import scipy as sp

from ..messages import *
from ..messages.timestamp import is_gps_time
from ..parsers.file_index import FileIndex
from ..parsers.mixed_log_reader import MixedLogReader
from ..utils import trace as logging
from ..utils.trace import SilentLogger
from ..utils.enum_utils import IntEnum
from ..utils.time_range import TimeRange


class TimeConversionType:
    P1_TO_GPS = auto()
    GPS_TO_P1 = auto()


class MessageData(object):
    def __init__(self, message_type, params):
        self.message_type = message_type
        self.message_class = message_type_to_class.get(self.message_type, None)
        self.params = params
        self.messages = []
        self.messages_bytes = []
        self.message_index = []

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
                self.messages_bytes = np.array(self.messages_bytes, dtype=np.uint64)
                self.message_index = np.array(self.message_index, dtype=int)

                if remove_nan_times and 'p1_time' in self.__dict__:
                    is_nan = np.isnan(self.p1_time)
                    if np.any(is_nan):
                        keep_idx = ~is_nan
                        for key, value in self.__dict__.items():
                            if (key not in ('message_type', 'message_class', 'params', 'messages') and
                                    isinstance(value, np.ndarray)):
                                if key in self.__dict__.get('__metadata__', {}).get('not_time_dependent', []):
                                    # Data is not time-dependent, even if it happens to have the same number of elements
                                    # as the time vector.
                                    pass
                                elif len(value.shape) == 1:
                                    if len(value) == len(keep_idx):
                                        self.__dict__[key] = value[keep_idx]
                                    else:
                                        # Field has a different length than the time vector. It is likely a
                                        # non-time-varying element (e.g., a position std dev threshold).
                                        pass
                                elif len(value.shape) == 2:
                                    # We typically transpose data arrays to be AxN, where A is the number of axes, and N
                                    # is the number of data points. If A == N, we'll assume that the time dimension is
                                    # along the columns.
                                    if value.shape[1] == len(is_nan):
                                        # Assuming second dimension (columns) is time.
                                        self.__dict__[key] = value[:, keep_idx]
                                    # Otherwise, check to see if the data is transposed as NxA.
                                    elif value.shape[0] == len(is_nan):
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

    def __repr__(self):
        return f'{MessageType.get_type_string(self.message_type)} data ({len(self.messages)} messages)'


class TimeAlignmentMode(IntEnum):
    NONE = 0
    DROP = 1
    INSERT = 2


class DataLoader(object):
    """!
    @brief Load FusionEngine data from one or more message types, optionally converting the data to numeric (Numpy)
           representation for analysis.

    If desired, data from different message types can be time-aligned automatically. See @ref read() and @ref
    time_align_data().

    By default, the loaded data will be cached internally for future access.
    """

    logger = logging.getLogger('point_one.fusion_engine.analysis.data_loader')

    def __init__(self, path=None, save_index=True, ignore_index=False):
        """!
        @brief Create a new reader instance.

        @param path The path to a binary file containing FusionEngine messages, or an existing Python file object.
        @param save_index If `True`, save a `.p1i` index file if one does not exist for faster reading in the
               future. See @ref FileIndex for details.
        @param ignore_index If `True`, ignore the existing index file and read from the `.p1log` binary file directly.
               If `save_index == True`, this will delete the existing file and create a new one.
        """
        self.reader: MixedLogReader = None

        self.data: Dict[MessageType, MessageData] = {}
        self.t0 = None
        self.system_t0 = None
        self.system_t0_ns = None

        self._need_t0 = True
        self._need_system_t0 = True

        self._generate_index = save_index
        if path is not None:
            self.open(path, save_index=save_index, ignore_index=ignore_index)

    def open(self, path, save_index=True, ignore_index=False):
        """!
        @brief Open a FusionEngine binary file.

        @param path The path to a binary file containing FusionEngine messages, or an existing Python file object.
        @param save_index If `True`, generate a `.p1i` index file if one does not exist for faster reading in the
               future. See @ref FileIndex for details.
        @param ignore_index If `True`, ignore the existing index file and read from the `.p1log` binary file directly.
               If `save_index == True`, this will delete the existing file and create a new one.
        """
        self.close()

        self.reader = MixedLogReader(input_file=path, save_index=save_index, ignore_index=ignore_index,
                                     return_bytes=True, return_message_index=True)

        # Read the first message (with P1 time) in the file to set self.t0.
        #
        # Note that we explicitly set a start time since, if the time range is not specified, read() will include
        # messages that do not have P1 time. We want to make sure the 1 message is one with time.
        self.t0 = None
        self.system_t0 = None
        self.system_t0_ns = None

        self._need_t0 = True
        self._need_system_t0 = True

        if self.reader.have_index():
            # If we have t0 in the index, capture it. If not, there must not be any messages with P1 time.
            self.t0 = self.reader.index.t0
            if self.t0 is None:
                self.logger.warning('Unable to set t0 - no P1 timestamps found in index file.')
            self._need_t0 = False

            # If there are no messages in the index that have system time, disable the search below. Otherwise, continue
            # below to search for system t0.
            if not np.any(np.isin(self.reader.get_index().type, list(messages_with_system_time))):
                self.logger.warning('Unable to set system t0 - no system timestamps found in index file.')
                self._need_system_t0 = False
        else:
            self.read(require_p1_time=True, max_messages=1, max_bytes=1 * 1024 * 1024,
                      disable_index_generation=True, ignore_cache=True, show_progress=False)

        # Similarly, we also set the system t0 based on the first system-stamped (typically POSIX) message to appear in
        # the log, if any (profiling data, etc.). Unlike P1 time, since the index file does not contain system
        # timestamps, we have to do a read() even if an index exists. read() will use the index to at least speed up the
        # read operation.
        if self._need_system_t0:
            self.read(require_system_time=True, max_messages=1, max_bytes=1 * 1024 * 1024,
                      disable_index_generation=True, ignore_cache=True, show_progress=False)

    def close(self):
        """!
        @brief Close the file.
        """
        if self.reader is not None:
            self.reader = None

    def read(self, *args, **kwargs) \
            -> Union[Dict[MessageType, MessageData], MessageData]:
        """!
        @brief Read data for one or more desired message types.

        The read data will be cached internally. Subsequent reads for the same data type will return the cached data.

        @note
        This function uses a data index file to speed up reads when available. If `save_index == True` and no index
        file exists, one will be generated automatically. In order to do this, this function must read the entire data
        file, even if it could normally return early when `max_messages` or the end of `time_range` are reached.

        @param message_types A list of one or more @ref fusion_engine_client.messages.defs.MessageType "MessageTypes" to
               be returned. If `None` or an empty list, read all available messages.
        @param time_range An optional @ref TimeRange object specifying desired start and end time bounds of the data to
               be read. See @ref TimeRange for more details.

        @param show_progress If `True`, print the read progress every 10 MB (useful for large files).
        @param disable_index_generation If `True`, override the `save_index` argument provided to `open()` and do
               not generate an index file during this call (intended for internal use only).
        @param ignore_cache If `True`, ignore any cached data from a previous @ref read() call, and reload the requested
               data from disk.

        @param max_messages If set, read up to the specified maximum number of messages. Applies across all message
               types. If negative, read the last N messages.
        @param max_bytes If set, read up to the specified maximum number of bytes.
        @param require_p1_time If `True`, omit messages that do not contain valid P1 timestamps.
        @param require_system_time If `True`, omit messages that do not contain valid system timestamps.

        @param return_in_order Return a `list` containing the messages in the order that they were found in the log.
               Note that this implies `return_numpy = False`, `time_align = TimeAlignmentMode.NONE`, and
               `ignore_cache = True`.
        @param return_bytes If `True`, store the encoded messages as `bytes` objects in the returned @ref MessageData
               objects.
        @param return_message_index If `True`, return the 0-based index of the message within the file.
        @param return_numpy If `True`, convert the results to numpy arrays for analysis.
        @param keep_messages If `return_numpy == True` and `keep_messages == False`, the raw data in the `messages`
               field will be cleared for each @ref MessagePayload object for which numpy conversion is supported.
        @param remove_nan_times If `True`, remove messages whose P1 timestamps are `NaN` when converting to numpy.
               Ignored if `return_numpy == False`.

        @param time_align The type of alignment to be performed (for data with P1 timestamps):
               - @ref TimeAlignmentMode.NONE - Do nothing
               - @ref TimeAlignmentMode.DROP - Drop messages at times when _all_ message types are not present
               - @ref TimeAlignmentMode.INSERT - Insert default-constructed messages for any message types not present
                 at a given time epoch
        @param aligned_message_types A list of message types for which time alignment will be performed. Any message
               types not present in the list will be left unmodified. If `None`, all message types will be aligned.

        @return - If `return_in_order == False`, return a `dict`, keyed by @ref
                  fusion_engine_client.messages.defs.MessageType "MessageType", containing @ref MessageData objects with
                  the data read for each of the requested message types.
                - If `return_in_order == True`, return a single @ref MessageData object containing all message types in
                  the order that they were recorded.
        """
        return self._read(*args, **kwargs)

    def _read(self,
              message_types: Union[Iterable[MessageType], MessageType] = None,
              time_range: TimeRange = None,
              show_progress: bool = False,
              ignore_cache: bool = False, disable_index_generation: bool = False,
              max_messages: int = None, max_bytes: int = None,
              require_p1_time: bool = False, require_system_time: bool = False,
              return_in_order: bool = False, return_bytes: bool = False, return_message_index: bool = False,
              return_numpy: bool = False, keep_messages: bool = False, remove_nan_times: bool = True,
              time_align: TimeAlignmentMode = TimeAlignmentMode.NONE,
              aligned_message_types: Union[list, tuple, set] = None,
              quiet: bool = False) \
            -> Union[Dict[MessageType, MessageData], MessageData]:
        if quiet:
            logger = SilentLogger(self.logger.name)
        else:
            logger = self.logger

        # Parse the time range params.
        if time_range is None:
            time_range = TimeRange()
        elif isinstance(time_range, TimeRange):
            pass
        else:
            time_range = TimeRange.parse(time_range)

        # Store the set of parameters used to perform this read along with the cache data. When doing reads for the
        # requested message type(s) in the future, if the parameters match exactly, we can return the cached data.
        # Otherwise, we need to read from disk again.
        params = {
            'time_range': time_range,
            'max_messages': max_messages,
            'max_bytes': max_bytes,
            'require_p1_time': require_p1_time,
            'require_system_time': require_system_time,
            'return_bytes': return_bytes,
            'return_message_index': return_message_index,
            'remove_nan_times': remove_nan_times,
        }

        # If the user requested output in the order that it was logged, we need to ignore cached data since that data
        # has already been separated by message type, and cannot be interleaved back into its original order.
        #
        # We also disable numpy conversion and time alignment, since those features assume the data is being returned as
        # a dict separated by message type.
        if return_in_order:
            ignore_cache = True
            return_numpy = False
            time_align = TimeAlignmentMode.NONE
            empty_result = MessageData(None, None)
        else:
            empty_result = {}

        # Parse the message types argument into a list of MessageType elements.
        if message_types is None:
            pass
        elif isinstance(message_types, MessageType):
            message_types = set((message_types,))
        elif MessagePayload.is_subclass(message_types):
            message_types = set((message_types.get_type(),))
        elif len(message_types) > 0:
            message_types = set([(t.get_type() if MessagePayload.is_subclass(t) else t) for t in message_types
                                 if t is not None])
            if len(message_types) == 0:
                return empty_result

        # If the message type list is empty, read all messages.
        if message_types is None or len(message_types) == 0:
            message_types = list(message_type_to_class.keys())

        # If any of the requested types were already read from the file for the requested parameters, skip them.
        if ignore_cache:
            needed_message_types = set(message_types)
        else:
            needed_message_types = [t for t in message_types
                                    if (t not in self.data or self.data[t].params != params)]
            needed_message_types = set(needed_message_types)

        # Make cache entries for the messages to be read.
        supported_message_types = set()

        if ignore_cache:
            data_cache = {}
        else:
            data_cache = self.data

        for type in needed_message_types:
            if not return_in_order:
                data_cache[type] = MessageData(message_type=type, params=params)

            cls = message_type_to_class.get(type, None)
            if cls is None:
                logger.warning('Decode not supported for message type %s. Omitting from output.' %
                               MessageType.get_type_string(type))
            else:
                supported_message_types.add(type)

        needed_message_types = supported_message_types

        # If P1 or system time is required, filter out message types that we know don't have it.
        if require_p1_time and require_system_time:
            needed_message_types = [t for t in needed_message_types
                                    if t in (messages_with_p1_time | messages_with_system_time)]
        elif require_p1_time:
            needed_message_types = [t for t in needed_message_types if t in messages_with_p1_time]
        elif require_system_time:
            needed_message_types = [t for t in needed_message_types if t in messages_with_system_time]

        # Check if the user requested any message types that use system time, not P1 time. When using an index file for
        # fast reading, messages with system times may have their index entry timestamps set to NAN since A) they can
        # occur in a log before P1 time is established, and B) there's not necessarily a direct way to convert between
        # system and P1 time.
        p1_time_messages_requested = any([t in messages_with_p1_time for t in needed_message_types])
        system_time_messages_requested = any([t in messages_with_system_time for t in needed_message_types])

        # Create a dict with references to the requested types only to be returned below. If any data was already
        # cached, it will be present in self.data and populated here.
        #
        # If we're returning in-order, we'll simply populate and return a MessageData object directly.
        if return_in_order:
            result = MessageData(message_type=None, params=params)
        else:
            result = {t: data_cache[t] for t in message_types}

        num_needed = len(needed_message_types)
        if num_needed == 0:
            # Nothing to read. Return cached data.
            logger.debug('Requested data already cached. [# types=%d, time_range=%s]' %
                         (len(message_types), str(time_range)))
            return result

        # Reset the filter criteria for the reader.
        if self.reader is None:
            raise IOError("File not open.")
        else:
            self.reader.rewind()
            self.reader.clear_filters()
            self.reader.set_show_progress(show_progress)
            self.reader.set_max_bytes(max_bytes)

        # If we need to establish t0 (either P1 time or system time), we will wait to apply the user's filter criteria.
        # We can get t0 from any message type.
        need_t0 = self._need_t0 and p1_time_messages_requested
        need_system_t0 = self._need_system_t0 and system_time_messages_requested

        reader_max_messages_applied = False
        if need_t0 or need_system_t0:
            logger.debug('Establishing t0. Postponing reader filter setup.')
            filters_applied = False
        else:
            filters_applied = True

            self.reader.filter_in_place(time_range)
            self.reader.filter_in_place(message_types)

            # If the user is requiring (valid) P1 timestamps, filter to those now.
            if require_p1_time and not system_time_messages_requested:
                self.reader.filter_out_invalid_p1_times()

            # If the user requested max messages, tell the reader to return max N results. The reader only supports this
            # if it has an index file, so we still check for N ourselves below.
            #
            # Additionally, if the caller requires the results to have (valid) system timestamps, we'll skip this here
            # since we need to decode the messages to see if they have valid timestamps. The index only stores P1 time,
            # not system time. The read_next() call below will apply this condition and only return messages with valid
            # system time.
            if (max_messages is not None and self.reader.have_index() and
                    not (require_system_time and system_time_messages_requested)):
                reader_max_messages_applied = True
                if max_messages >= 0:
                    self.reader.filter_in_place(slice(None, max_messages))
                else:
                    self.reader.filter_in_place(slice(max_messages, None))

        # When the user requests max_messages < 0, they would like the _last_ N messages in the file. If the reader does
        # not have an index file, so we can't do a slice above, we will create a circular buffer and store the last N
        # messages we see.
        if max_messages is not None and max_messages < 0 and not reader_max_messages_applied:
            newest_messages = deque(maxlen=abs(max_messages))
        else:
            newest_messages = None

        # Now read each available message matching the user criteria.
        num_total = len(message_types)
        logger.debug('Reading data for %d message types. [cached=%d, max=%s, time_range=%s]' %
                     (num_total, num_total - num_needed, 'N/A' if max_messages is None else str(max_messages),
                      str(time_range)))

        message_count = 0
        while True:
            try:
                header, payload, message_bytes, message_index = \
                    self.reader.read_next(require_p1_time=require_p1_time,
                                          require_system_time=require_system_time)
            except StopIteration:
                break

            message_size_bytes = header.get_message_size()
            message_offset_bytes = self.reader.get_bytes_read() - message_size_bytes

            # Unsupported/unrecognized message type.
            if payload is None:
                logger.debug('  Skipping unsupported %s message @ %d. [length=%d B]' %
                             (header.get_type_string(), message_offset_bytes, message_size_bytes))
                continue

            logger.debug('  Parsed %s message @ %d. [length=%d B]' %
                         (header.get_type_string(), message_offset_bytes, message_size_bytes))

            # Extract P1 and system times from this message, if applicable.
            p1_time = payload.get_p1_time()
            system_time_ns = payload.get_system_time_ns()
            system_time_sec = None if system_time_ns is None else (system_time_ns * 1e-9)
            system_time_valid = system_time_ns is not None and not np.isnan(system_time_ns)

            # Store t0 if this is the first message with a (valid) timestamp.
            if p1_time is not None and p1_time:
                if self.t0 is None:
                    logger.debug('Received first message. [type=%s, time=%s]' %
                                 (header.get_type_string(), str(p1_time)))
                    self.t0 = p1_time
                    self._need_t0 = False

            if system_time_valid:
                if self.system_t0 is None:
                    logger.debug('Received first system-timestamped message. [type=%s, time=%s]' %
                                 (header.get_type_string(), system_time_to_str(system_time_ns)))
                    self.system_t0 = system_time_sec
                    self.system_t0_ns = system_time_ns
                    self._need_system_t0 = False

            # If we waited to apply filters above in order to establish t0, manually apply the filter criteria here.
            # Once we know t0, the reader will do the filtering and we won't hit this condition again.
            if not filters_applied:
                # Once we know t0, enable the reader's internal filtering to take effect on the next message.
                if not need_t0 and not need_system_t0:
                    logger.debug('Established t0. Applying reader filters.')
                    self.reader.filter_in_place(message_types)
                    self.reader.filter_in_place(time_range)
                    filters_applied = True

                # Apply any filtering the reader would have.
                if header.message_type.value not in needed_message_types:
                    logger.debug('  Message not in requested types. Discarding.')
                    continue
                elif not time_range.is_in_range(payload):
                    logger.debug('  Message not in specified time range. Discarding.')
                    continue
                elif require_p1_time and not p1_time:
                    logger.debug('  Message does not contain P1 time. Discarding.')
                    continue
                elif require_system_time and not system_time_valid:
                    logger.debug('  Message does not contain system time. Discarding.')
                    continue

            # Store the message.
            #
            # If we haven't reached the max message count yet, or none was specified, store the message by type. If
            # max_messages is negative however, the user requested the N latest messages. In that case, we add them to
            # an N-length circular buffer and pick off the newest ones when we're done with the file.
            message_count += 1
            if newest_messages is not None:
                newest_messages.append((header, payload, message_bytes, message_index))
            elif max_messages is None or message_count <= abs(max_messages):
                if return_in_order:
                    result.messages.append(payload)
                    if return_bytes:
                        result.messages_bytes.append(message_bytes)
                    if return_message_index:
                        result.message_index.append(message_index)
                else:
                    data_cache[header.message_type].messages.append(payload)
                    if return_bytes:
                        data_cache[header.message_type].messages_bytes.append(message_bytes)
                    if return_message_index:
                        data_cache[header.message_type].message_index.append(message_index)

            if max_messages is not None:
                # If we hit the max message count, we're done reading.
                if message_count == abs(max_messages):
                    logger.debug('  Max messages reached. Done reading. [# messages=%d]' % message_count)
                    break

        # Fast-forward the reader to EOF to print out one last progress update. If we already reached EOF and printed
        # the update, this should have no effect.
        self.reader.seek_to_eof()

        # If we were searching for t0 and did not find it, it must not be present in the log. Don't look again on
        # subsequent read calls.
        if need_t0 and require_p1_time:
            self._need_t0 = False

        if need_system_t0 and require_system_time:
            self._need_system_t0 = False

        # If the user only wanted the N newest messages, take them from the circular buffer now.
        if newest_messages is not None:
            for header, payload, message_bytes, message_index in newest_messages:
                if return_in_order:
                    result.messages.append(payload)
                    if return_bytes:
                        result.messages_bytes.append(message_bytes)
                    if return_message_index:
                        result.message_index.append(message_index)
                else:
                    data_cache[header.message_type].messages.append(payload)
                    if return_bytes:
                        data_cache[header.message_type].messages_bytes.append(message_bytes)
                    if return_message_index:
                        data_cache[header.message_type].message_index.append(message_index)

        # Time-align the data if requested.
        if time_align != TimeAlignmentMode.NONE:
            DataLoader.time_align_data(result, mode=time_align, message_types=aligned_message_types)

        # Convert the resulting message data to numpy (if supported).
        if return_numpy:
            DataLoader.to_numpy(result, keep_messages=keep_messages, remove_nan_times=remove_nan_times)

        # Done.
        return result

    def read_next(self, return_bytes: bool = False, return_message_index: bool = False):
        header, payload, message_bytes, message_index = self.reader.read_next()
        result = [header, payload]
        if return_bytes:
            result.append(message_bytes)
        if return_message_index:
            result.append(message_index)
        return result

    def get_t0(self):
        return self.t0

    def get_system_t0(self):
        return self.system_t0

    def get_system_t0_ns(self):
        return self.system_t0_ns

    def get_index(self) -> FileIndex:
        return self.reader.get_index()

    def get_log_reader(self) -> MixedLogReader:
        return self.reader

    def get_input_path(self):
        return self.reader.input_file.name

    def _convert_time(self, conversion_type: TimeConversionType,
                      times: Union[Iterable[Union[datetime, gpstime, Timestamp, float]],
                                   Union[datetime, gpstime, Timestamp, float]],
                      assume_utc: bool = False) ->\
            np.ndarray:
        """!
        @brief Convert UTC or GPS timestamps to P1 time or Convert UTC or P1 timestamps to GPS time.

        @param conversion_type If `GPS_TO_P1`, convert to P1 time. If `P1_TO_GPS`, convert to GPS time.
        @param times A list of one or more timestamps to be converted, using any of the following formats:
               - `datetime` - A UTC or local timezone date and time
               - `gpstime` - A GPS timestamp
               - A @ref fusion_engine_client.messages.timestamps.Timestamp containing GPS time or P1 time
               - A @ref fusion_engine_client.messages.timestamps.MeasurementDetails containing GPS time or P1 time
               - `float` - A GPS or P1 time value (in seconds)
                 - Note that UTC timestamps cannot be specified `float` unless `assume_utc == True`
        @param assume_utc If `True`:
               - For `float` values, assume values greater than the POSIX offset for 2000/1/1 are UTC timestamps in
                 seconds.
               - For `datetime`, if `tzinfo` is not set, assume it is `timezone.utc`. Otherwise, interpret the timestamp
                 in the local timezone.

        @return A numpy array containing time values (in seconds), or `nan` if the value could not be converted.
        """
        # Load pose messages, which contain the relationship between P1 and GPS time. Omit any NAN values from the
        # reference timestamps.
        #
        # If no pose data is available, we can't convert to P1 time. We'll return nan for any values that are not
        # already P1 time below.
        if PoseMessage.MESSAGE_TYPE in self.data:
            # If the caller already read in pose data, we'll use the cached messages read with whatever parameters they
            # specified (e.g., a specific time range). That way, A) we don't read from disk multiple times, and B) for a
            # very long log, we don't read a ton of data from disk when the caller is only interested in a short
            # snippet. We assume the requested timestamps won't be too far out of the time range specified for the
            # cached messages.
            self.logger.debug('Using existing cached pose data for P1 time conversion.')
            pose_data = self.data[PoseMessage.MESSAGE_TYPE]
        else:
            result = self.read(message_types=[PoseMessage], return_numpy=True)
            pose_data = result[PoseMessage.MESSAGE_TYPE]

        idx = ~np.logical_or(np.isnan(pose_data.p1_time), np.isnan(pose_data.gps_time))
        p1_ref_sec = pose_data.p1_time[idx]
        gps_ref_sec = pose_data.gps_time[idx]

        if len(p1_ref_sec) == 0:
            self.logger.debug('Pose data not available. Cannot convert timestamps to P1 time.')
            p1_ref_sec = None
            gps_ref_sec = None

        # First, convert all UTC times and all timestamp objects to GPS time or P1 values in seconds.
        timezone_warn_issued = False

        def _to_gps_or_p1(value):
            nonlocal timezone_warn_issued
            if isinstance(value, gpstime):
                return value.gps()
            elif isinstance(value, datetime):
                if value.tzinfo is None:
                    if assume_utc:
                        value = value.replace(tzinfo=timezone.utc)
                    elif not timezone_warn_issued:
                        self.logger.warning('datetime object detected without timezone. Assuming local timezone.')
                        timezone_warn_issued = True
                return gpstime.fromdatetime(value).gps()
            elif isinstance(value, Timestamp):
                return value.seconds
            elif assume_utc and is_gps_time(value):
                return unix2gps(value)
            else:
                return value

        # If the input is a numpy array and we're not assuming the timestamps are UTC, they're already floats and either
        # GPS timestamps or already P1 timestamps. We don't need to convert anything to GPS time, so we can skip right
        # to the P1 conversion step below.
        if isinstance(times, np.ndarray) and not assume_utc:
            return_scalar = False
            time_sec = times
        else:
            # If the user passed in an iterable object (list, tuple numpy array, etc.), convert all entries to GPS or
            # P1 values in seconds.
            try:
                iter(times)
                return_scalar = False
                time_sec = np.array([_to_gps_or_p1(t) for t in times])
            # Otherwise, if they passed in a single element, convert it to a numpy array with one value. We'll return a
            # single scalar P1 value below.
            except TypeError:
                return_scalar = True
                time_sec = np.array((_to_gps_or_p1(times),))

        # Now, find all values that are GPS time (i.e., big enough that we assume they're not P1 times already) and
        # convert them to P1 time or vice versa.
        if conversion_type == TimeConversionType.GPS_TO_P1:
            gps_idx = is_gps_time(time_sec)
            if np.any(gps_idx):
                if p1_ref_sec is None:
                    time_sec[gps_idx] = np.nan
                else:
                    # The relationship between P1 time and GPS time should not change rapidly since P1 time is rate-steered
                    # to align with GPS time. As a result, it should be safe to extrapolate between gaps in P1 or GPS times,
                    # as long as the gaps aren't extremely large. NumPy's interp() function does not extrapolate, so we
                    # instead use SciPy's function.
                    f = sp.interpolate.interp1d(gps_ref_sec, p1_ref_sec, fill_value='extrapolate')
                    time_sec[gps_idx] = f(time_sec[gps_idx])
        elif conversion_type == TimeConversionType.P1_TO_GPS:
            p1_idx = np.logical_not(is_gps_time(time_sec))
            if np.any(p1_idx):
                if p1_idx is None:
                    time_sec[p1_idx] = np.nan
                else:
                    # See comment on sp.interpolate.interp1d above.
                    f = sp.interpolate.interp1d(p1_ref_sec, gps_ref_sec, fill_value='extrapolate')
                    time_sec[p1_idx] = f(time_sec[p1_idx])

        if return_scalar:
            return time_sec[0]
        else:
            return time_sec

    def convert_to_p1_time(self,
                           times: Union[Iterable[Union[datetime, gpstime, Timestamp, float]],
                                        Union[datetime, gpstime, Timestamp, float]],
                           assume_utc: bool = False) ->\
            np.ndarray:
        """!
        @brief Convert UTC or GPS timestamps to P1 time.

        @param times A list of one or more timestamps to be converted, using any of the following formats:
               - `datetime` - A UTC or local timezone date and time
               - `gpstime` - A GPS timestamp
               - A @ref fusion_engine_client.messages.timestamps.Timestamp containing GPS time or P1 time
               - A @ref fusion_engine_client.messages.timestamps.MeasurementDetails containing GPS time or P1 time
               - `float` - A GPS or P1 time value (in seconds)
                 - Note that UTC timestamps cannot be specified `float` unless `assume_utc == True`
        @param assume_utc If `True`:
               - For `float` values, assume values greater than the POSIX offset for 2000/1/1 are UTC timestamps in
                 seconds.
               - For `datetime`, if `tzinfo` is not set, assume it is `timezone.utc`. Otherwise, interpret the timestamp
                 in the local timezone.

        @return A numpy array containing P1 time values (in seconds), or `nan` if the value could not be converted.
        """
        return self._convert_time(conversion_type=TimeConversionType.GPS_TO_P1, times=times, assume_utc=assume_utc)

    def convert_to_gps_time(self,
                            times: Union[Iterable[Union[datetime, gpstime, Timestamp, float]],
                                         Union[datetime, gpstime, Timestamp, float]],
                            assume_utc: bool = False) ->\
            np.ndarray:
        """!
        @brief Convert UTC or P1 timestamps to GPS time.

        @param times A list of one or more timestamps to be converted, using any of the following formats:
               - `datetime` - A UTC or local timezone date and time
               - `gpstime` - A GPS timestamp
               - A @ref fusion_engine_client.messages.timestamps.Timestamp containing GPS time or P1 time
               - A @ref fusion_engine_client.messages.timestamps.MeasurementDetails containing GPS time or P1 time
               - `float` - A GPS or P1 time value (in seconds)
                 - Note that UTC timestamps cannot be specified `float` unless `assume_utc == True`
        @param assume_utc If `True`:
               - For `float` values, assume values greater than the POSIX offset for 2000/1/1 are UTC timestamps in
                 seconds.
               - For `datetime`, if `tzinfo` is not set, assume it is `timezone.utc`. Otherwise, interpret the timestamp
                 in the local timezone.

        @return A numpy array containing GPS time values (in seconds), or `nan` if the value could not be converted.
        """
        return self._convert_time(conversion_type=TimeConversionType.P1_TO_GPS, times=times, assume_utc=assume_utc)

    @classmethod
    def time_align_data(cls, data: dict, mode: TimeAlignmentMode = TimeAlignmentMode.INSERT,
                        message_types: Union[list, tuple, set] = None):
        """!
        @brief Time-align messages of different types.

        @post
        `data` will be modified in-place. Message types that do not contain P1 time will be left unmodified.

        @param data A data `dict` as returned by @ref read().
        @param mode The type of alignment to be performed:
               - @ref TimeAlignmentMode.NONE - Do nothing
               - @ref TimeAlignmentMode.DROP - Drop messages at times when _all_ message types are not present
               - @ref TimeAlignmentMode.INSERT - Insert default-constructed messages for any message types not present
                 at a given time epoch
        @param message_types A list of message types for which alignment will be performed. Any message types not
               present in the list will be left unmodified. If `None`, all message types will be aligned.

        @return A modified `dict` with removed or inserted messages.
        """
        # Time alignment disabled - do nothing.
        if mode == TimeAlignmentMode.NONE:
            return data

        if message_types is not None:
            # Allow the user to pass in a list of message classes for convenience and convert them to message types
            # automatically.
            message_types = set([(t if isinstance(t, MessageType) else t.MESSAGE_TYPE) for t in message_types])

        # Pull out the P1 times for each message type. In drop mode, compute the intersection of all P1 timestamps. In
        # insert mode, make a list of all unique P1 timestamps.
        info_by_type = {}
        time_set = None
        for type, entry in data.items():
            default = entry.message_class()
            if 'p1_time' in default.__dict__ and (message_types is None or entry.message_type in message_types):
                p1_time = np.array([float(m.p1_time) for m in entry.messages])
                info_by_type[type] = {'p1_time': p1_time, 'messages': entry.messages, 'class': entry.message_class}

                if mode == TimeAlignmentMode.DROP:
                    if time_set is None:
                        time_set = p1_time
                    else:
                        time_set = np.intersect1d(time_set, p1_time)
                else:
                    if time_set is None:
                        time_set = p1_time
                    else:
                        time_set = np.hstack((time_set, p1_time))

        # In insertion mode, insert default-constructed objects for any missing timestamps.
        if mode == TimeAlignmentMode.INSERT:
            time_set = np.unique(time_set)

            for type, entry in info_by_type.items():
                # Locate the timestamps where we do/do not have data. For timestamps with data we store the index of the
                # corresponding message. For timestamps without we store -1.
                _, idx, all_idx = np.intersect1d(entry['p1_time'], time_set, return_indices=True)
                message_indices = np.full_like(time_set, -1, dtype=int)
                message_indices[all_idx] = idx

                # Now interlace messages with defaults as needed.
                messages = entry['messages']
                cls = entry['class']

                def _get_value(i):
                    message_idx = message_indices[i]
                    if message_idx >= 0:
                        return messages[message_idx]
                    else:
                        default = cls()
                        default.p1_time = time_set[i]
                        return default
                data[type].messages = [_get_value(i) for i in range(len(time_set))]
        # In drop mode, drop messages that aren't present across _all_ message types.
        elif mode == TimeAlignmentMode.DROP:
            for type, entry in info_by_type.items():
                _, idx, _ = np.intersect1d(entry['p1_time'], time_set, return_indices=True)
                data[type].messages = [entry['messages'][i] for i in idx]
        else:
            raise ValueError('Unrecognized alignment mode.')

        return data

    @classmethod
    def to_numpy(cls, data: dict, keep_messages: bool = True, remove_nan_times: bool = True):
        """!
        @brief Convert all (supported) messages in a data dictionary to numpy for analysis.

        See @ref MessageData.to_numpy().

        @param data A data `dict` as returned by @ref read().
        @param keep_messages If `False`, the raw data in the `messages` field will be cleared for each @ref
               MessagePayload object for which numpy conversion is supported.
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
