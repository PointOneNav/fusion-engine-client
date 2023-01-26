from typing import Dict, Iterable, Tuple, Union

from collections import deque
import copy
from datetime import datetime
import io
import logging
import os

import numpy as np

from ..messages import *
from ..parsers.file_index import FileIndex, FileIndexBuilder
from ..parsers.mixed_log_reader import MixedLogReader
from ..utils.trace import SilentLogger
from ..utils.enum_utils import IntEnum
from ..utils.time_range import TimeRange


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
                                    if len(value) == len(keep_idx):
                                        self.__dict__[key] = value[keep_idx]
                                    else:
                                        # Field has a different length than the time vector. It is likely a
                                        # non-time-varying element (e.g., a position std dev threshold).
                                        pass
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

    def __init__(self, path=None, generate_index=True, ignore_index=False):
        """!
        @brief Create a new reader instance.

        @param path The path to a binary file containing FusionEngine messages, or an existing Python file object.
        @param generate_index If `True`, generate a `.p1i` index file if one does not exist for faster reading in the
               future. See @ref FileIndex for details.
        @param ignore_index If `True`, ignore the existing index file and read from the `.p1log` binary file directly.
               If `generate_index == True`, this will delete the existing file and create a new one.
        """
        self.reader: MixedLogReader = None

        self.data: Dict[MessageType, MessageData] = {}
        self.t0 = None
        self.system_t0 = None
        self.system_t0_ns = None

        self._generate_index = generate_index
        if path is not None:
            self.open(path, generate_index=generate_index, ignore_index=ignore_index)

    def open(self, path, generate_index=True, ignore_index=False):
        """!
        @brief Open a FusionEngine binary file.

        @param path The path to a binary file containing FusionEngine messages, or an existing Python file object.
        @param generate_index If `True`, generate a `.p1i` index file if one does not exist for faster reading in the
               future. See @ref FileIndex for details.
        @param ignore_index If `True`, ignore the existing index file and read from the `.p1log` binary file directly.
               If `generate_index == True`, this will delete the existing file and create a new one.
        """
        self.close()

        self.reader = MixedLogReader(input_file=path, generate_index=generate_index, ignore_index=ignore_index)
        if self.reader.have_index():
            self.logger.debug("Using index file '%s'." % self.reader.index_path)

        # Read the first message (with P1 time) in the file to set self.t0.
        #
        # Note that we explicitly set a start time since, if the time range is not specified, read() will include
        # messages that do not have P1 time. We want to make sure the 1 message is one with time.
        self.t0 = None
        self.system_t0 = None
        self.system_t0_ns = None

        if self.reader.have_index():
            self.t0 = self.reader.index.t0
            if self.t0 is None:
                self.logger.warning('Unable to set t0 - no P1 timestamps found in index file.')
        else:
            self.read(require_p1_time=True, max_messages=1, disable_index_generation=True, show_progress=False,
                      ignore_cache=True)

        # Similarly, we also set the system t0 based on the first system-stamped (typically POSIX) message to appear in
        # the log, if any (profiling data, etc.). Unlike P1 time, since the index file does not contain system
        # timestamps, we have to do a read() even if an index exists. read() will use the index to at least speed up the
        # read operation.
        self.read(require_system_time=True, max_messages=1, disable_index_generation=True, show_progress=False,
                  ignore_cache=True)

    def close(self):
        """!
        @brief Close the file.
        """
        if self.reader is not None:
            self.reader = None

    def generate_index(self, show_progress=False):
        """!
        @brief Generate an index file for the current binary file if one does not already exist.
        """
        if not self.reader.have_index():
            # We'll read pose data (doesn't actually matter which). Store the currently cached data and restore it when
            # we're done. That way if the user already did a read (with generate_index == False), they don't have to
            # re-read the data if they try to use it again.
            prev_data = self.data.get(MessageType.POSE, None)

            if show_progress:
                self.logger.info('Generating data index for faster access. This may take a few minutes...')
            else:
                self.logger.debug('Generating data index for faster access. This may take a few minutes...')

            self._generate_index = True
            self.read(message_types=[MessageType.POSE], max_messages=1, disable_index_generation=False,
                      ignore_cache=True, show_progress=show_progress, quiet=True)

            if prev_data is not None:
                self.data[MessageType.POSE] = prev_data

    def read(self, *args, **kwargs) \
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
        @param time_range An optional @ref TimeRange object specifying desired start and end time bounds of the data to
               be read. See @ref TimeRange for more details.

        @param show_progress If `True`, print the read progress every 10 MB (useful for large files).
        @param disable_index_generation If `True`, override the `generate_index` argument provided to `open()` and do
               not generate an index file during this call (intended for internal use only).
        @param ignore_cache If `True`, ignore any cached data from a previous @ref read() call, and reload the requested
               data from disk.

        @param max_messages If set, read up to the specified maximum number of messages. Applies across all message
               types. If negative, read the last N messages.
        @param require_p1_time If `True`, omit messages that do not contain valid P1 timestamps.
        @param require_system_time If `True`, omit messages that do not contain valid system timestamps.

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

        @return A dictionary, keyed by @ref fusion_engine_client.messages.defs.MessageType "MessageType", containing
               @ref MessageData objects with the data read for each of the requested message types.
        """
        return self._read(*args, **kwargs)

    def _read(self,
             message_types: Union[Iterable[MessageType], MessageType] = None,
             time_range: TimeRange = None,
             show_progress: bool = False,
             ignore_cache: bool = False, disable_index_generation: bool = False,
             max_messages: int = None, require_p1_time: bool = False, require_system_time: bool = False,
             return_numpy: bool = False, keep_messages: bool = False, remove_nan_times: bool = True,
             time_align: TimeAlignmentMode = TimeAlignmentMode.NONE,
             aligned_message_types: Union[list, tuple, set] = None,
             quiet: bool = False) \
            -> Dict[MessageType, MessageData]:
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
            'require_p1_time': require_p1_time,
            'require_system_time': require_system_time,
        }

        # Parse the message types argument into a list of MessageType elements.
        if message_types is None:
            pass
        elif isinstance(message_types, MessageType):
            message_types = set((message_types,))
        elif MessagePayload.is_subclass(message_types):
            message_types = set((message_types.get_type(),))
        else:
            message_types = set([(t.get_type() if MessagePayload.is_subclass(t) else t) for t in message_types])
            if len(message_types) == 0:
                message_types = None

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
            data_cache[type] = MessageData(message_type=type, params=params)

            cls = message_type_to_class.get(type, None)
            if cls is None:
                logger.warning('Decode not supported for message type %s. Omitting from output.' %
                               MessageType.get_type_string(type))
            else:
                supported_message_types.add(type)

        needed_message_types = supported_message_types

        # Check if the user requested any message types that use system time, not P1 time. When using an index file for
        # fast reading, messages with system times may have their index entry timestamps set to NAN since A) they can
        # occur in a log before P1 time is established, and B) there's not necessarily a direct way to convert between
        # system and P1 time.
        system_time_messages_requested = any([t in messages_with_system_time for t in needed_message_types])

        # Create a dict with references to the requested types only to be returned below. If any data was already
        # cached, it will be present in self.data and populated here.
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
            self.reader.set_generate_index(self._generate_index and not disable_index_generation)
            self.reader.set_show_progress(show_progress)

        # If we need to establish t0 (either P1 time or system time), we will wait to apply the user's filter criteria.
        # We can get t0 from any message type.
        reader_max_messages_applied = False
        if self.t0 is None or (self.system_t0 is None and system_time_messages_requested):
            logger.debug('Establishing t0. Postponing reader filter setup.')
            filters_applied = False
        else:
            filters_applied = True

            self.reader.filter_in_place(message_types, clear_existing=True)
            self.reader.filter_in_place(time_range, clear_existing=False)

            # If the user requested max messages, tell the reader to return max N results. The reader only supports this
            # if it has an index file, so we still check for N ourselves below.
            if max_messages is not None and self.reader.have_index():
                reader_max_messages_applied = True
                if max_messages >= 0:
                    self.reader.filter_in_place(slice(None, max_messages), clear_existing=False)
                else:
                    self.reader.filter_in_place(slice(max_messages, None), clear_existing=False)

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
                header, payload = self.reader.read_next(require_p1_time=require_p1_time and filters_applied,
                                                        require_system_time=require_system_time and filters_applied)
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

            # Store t0 if this is the first message with a (valid) timestamp.
            if p1_time is not None and p1_time:
                if self.t0 is None:
                    logger.debug('Received first message. [type=%s, time=%s]' %
                                 (header.get_type_string(), str(p1_time)))
                    self.t0 = p1_time

            if system_time_ns is not None:
                if self.system_t0 is None:
                    logger.debug('Received first system-timestamped message. [type=%s, time=%s]' %
                                 (header.get_type_string(), system_time_to_str(system_time_ns)))
                    self.system_t0 = system_time_sec
                    self.system_t0_ns = system_time_ns

            # If we waited to apply filters above in order to establish t0, manually apply the filter criteria here.
            # Once we know t0, the reader will do the filtering and we won't hit this condition again.
            if not filters_applied:
                # Once we know t0, enable the reader's internal filtering to take effect on the next message.
                if self.t0 is not None and (self.system_t0 is not None or not system_time_messages_requested):
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
                elif require_system_time and system_time_ns is None:
                    logger.debug('  Message does not contain system time. Discarding.')
                    continue

            # Store the message.
            #
            # If we haven't reached the max message count yet, or none was specified, store the message by type. If
            # max_messages is negative however, the user requested the N latest messages. In that case, we add them to
            # an N-length circular buffer and pick off the newest ones when we're done with the file.
            message_count += 1
            if newest_messages is not None:
                newest_messages.append((header, payload))
            elif max_messages is None or message_count <= abs(max_messages):
                data_cache[header.message_type].messages.append(payload)

            if max_messages is not None:
                # If we reached the max message count but we're generating an index file, we need to read through the
                # entire data file. Keep reading but discard any further messages.
                if self.reader.generating_index() and message_count > abs(max_messages):
                    logger.debug('  Max messages reached. Discarding. [# messages=%d]' % message_count)
                    continue
                # If we're not generating an index and we hit the max message count, we're done reading.
                elif not self.reader.generating_index() and message_count == abs(max_messages):
                    logger.debug('  Max messages reached. Done reading. [# messages=%d]' % message_count)
                    break

        # Fast-forward the reader to EOF to print out one last progress update. If we already reached EOF and printed
        # the update, this should have no effect.
        self.reader.seek_to_eof()

        # If the user only wanted the N newest messages, take them from the circular buffer now.
        if newest_messages is not None:
            for entry in newest_messages:
                data_cache[entry[0].message_type].messages.append(entry[1])

        # Time-align the data if requested.
        DataLoader.time_align_data(result, mode=time_align, message_types=aligned_message_types)

        # Convert the resulting message data to numpy (if supported).
        if return_numpy:
            DataLoader.to_numpy(result, keep_messages=keep_messages, remove_nan_times=remove_nan_times)

        # Done.
        return result

    def get_t0(self):
        return self.t0

    def get_system_t0(self):
        return self.system_t0

    def get_system_t0_ns(self):
        return self.system_t0_ns

    def get_index(self):
        return self.reader.get_index()

    def get_input_path(self):
        return self.reader.input_file.name

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