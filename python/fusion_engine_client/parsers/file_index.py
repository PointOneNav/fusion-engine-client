from typing import Union

from collections import namedtuple
import copy
import io
import os

import numpy as np

from ..messages import MessageHeader, MessagePayload, MessageType, Timestamp
from ..utils.enum_utils import IntEnum
from ..utils.numpy_utils import find_first
from ..utils.time_range import TimeRange


FileIndexEntry = namedtuple('Element', ['time', 'type', 'offset', 'message_index'])


class FileIndexIterator(object):
    def __init__(self, enum_class=None, np_iterator=None):
        self.enum_class = enum_class
        self.np_iterator = np_iterator

    def __next__(self):
        if self.np_iterator is None:
            raise StopIteration()
        else:
            entry = next(self.np_iterator)
            return FileIndexEntry(time=Timestamp(entry[0]), type=self.enum_class(entry[1], raise_on_unrecognized=False),
                                  offset=entry[2], message_index=entry[3])


class FileIndex(object):
    """!
    @brief An index of FusionEngine message entries within a `.p1log` file used to facilitate quick access.

    This class reads a `.p1i` file from disk containing FusionEngine message index entries. Each index entry includes
    the P1 time of the message (if applicable), the @ref MessageType, and the message offset within the file (in bytes).
    A @ref FileIndex instance may be used to quickly locate entries within a specific time range, or entries for one or
    more message types, without having to parse the variable-length messages in the `.p1log` file itself.

    @section file_index_examples Usage Examples

    @subsection file_index_iterate Iterate Over Elements

    @ref FileIndex supports supports two methods for accessing individual FusionEngine message entries. You can iterate
    over the @ref FileIndex class itself, accessing one @ref FileIndexEntry object at a time:

    ```py
    for entry in file_index:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```

    Alternatively, you can access any of the `time`, `type`, or `offset` arrays directly. Each of these members returns
    a NumPy `ndarray` object listing the P1 times (in seconds), @ref MessageType values, or byte offsets respectively:

    ```.py
    for offset in file_index.offset:
        log_file.seek(offset, io.SEEK_SET)
        ...
    ```

    @subsection file_index_type Find All Messages For A Specific Type

    @ref FileIndex supports slicing by a single @ref MessageType:

    ```py
    for entry in file_index[MessageType.POSE]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```

    or by a list containing one or more @ref MessageType values:

    ```py
    for entry in file_index[(MessageType.POSE, MessageType.GNSS_INFO)]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```

    @subsection file_index_time Find All Messages For A Specific Time Range

    One of the most common uses is to search for messages within a specific time range. @ref FileIndex supports slicing
    by P1 time using `Timestamp` objects or `float` values:

    ```py
    for entry in file_index[Timestamp(2.0):Timestamp(5.0)]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...

    for entry in file_index[2.0:5.0]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```

    As with all Python `slice()` operations, the start time is inclusive and the stop time is exclusive. Either time may
    be omitted to slice from the beginning or to the end of the data:

    ```py
    for entry in file_index[:5.0]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...

    for entry in file_index[2.0:]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```

    @subsection file_index_by_index Access Messages By Index

    Similar to @ref file_index_time "slicing by time", if desired you can access elements within a specific range of
    indices within the file. For example, the following returns elements 2 through 7 in the file:

    ```py
    for entry in file_index[2:8]:
        log_file.seek(entry.offset, io.SEEK_SET)
        ...
    ```
    """
    # Note: To reduce the index file size, we've made the following limitations:
    # - Fractional timestamp is floored so time 123.4 becomes 123. The data read should not assume that an entry's
    #   timestamp is its exact time
    _RAW_DTYPE = np.dtype([('int', '<u4'), ('type', '<u2'), ('offset', '<u8')])

    _DTYPE = np.dtype([('time', '<f8'), ('type', '<u2'), ('offset', '<u8'), ('message_index', '<u8')])

    def __init__(self,
                 index_path: str = None,
                 data_path: str = None,
                 delete_on_error=True,
                 data: Union[np.ndarray,
                             list] = None,
                 t0: Timestamp = None,
                 enum_class=MessageType,
                 enum_class_invalid=MessageType.INVALID):
        """!
        @brief Construct a new @ref FileIndex instance.

        @param index_path The path to a `.p1i` index file to be loaded.
        @param data_path The path to the `.p1log` data file corresponding with `index_path`, used to validate the loaded
               index entries. If `None`, defaults to `filename.p1log` if it exists.
        @param delete_on_error If `True`, delete the index file if an error is detected before raising an exception.
               Otherwise, leave the file unchanged.
        @param data A NumPy `ndarray` or Python `list` containing information about each FusionEngine message in the
               `.p1log` file. For internal use.
        @param t0 The P1 time corresponding with the start of the `.p1log` file, if known. For internal use.
        @param enum_class The @ref IntEnum class used to identify the messages.
        @param enum_class_invalid The value of enum_class to use for invalid entries.
        """
        self.enum_class = enum_class
        self.enum_class_invalid = enum_class_invalid
        if data is None:
            self._data = None
        else:
            if isinstance(data, list):
                self._data = FileIndex._from_list(data)
            elif data.dtype == FileIndex._DTYPE:
                self._data = data
            else:
                raise ValueError('Unsupported array format.')

        if index_path is not None:
            if self._data is None:
                self.load(index_path=index_path, data_path=data_path, delete_on_error=delete_on_error)
            else:
                raise ValueError('Cannot specify both path and data.')

        if self._data is None:
            self._data = np.array([], dtype=FileIndex._DTYPE)

        if t0 is not None:
            self.t0 = t0
        elif len(self._data) == 0:
            self.t0 = None
        else:
            idx = find_first(~np.isnan(self._data['time']))
            if idx >= 0:
                self.t0 = Timestamp(self._data['time'][idx])
            else:
                self.t0 = None

    def load(self, index_path, data_path=None, delete_on_error=True):
        """!
        @brief Load a `.p1i` index file from disk.

        @param index_path The path to the file to be read.
        @param data_path The path to the `.p1log` data file corresponding with `index_path`, used to validate the loaded
               index entries. If `None`, defaults to `filename.p1log` if it exists.
        @param delete_on_error If `True`, delete the index file if an error is detected before raising an exception.
               Otherwise, leave the file unchanged.
        """
        if os.path.exists(index_path):
            raw_data = np.fromfile(index_path, dtype=FileIndex._RAW_DTYPE)
            self._data = FileIndex._from_raw(raw_data)
        else:
            raise FileNotFoundError("Index file '%s' does not exist." % index_path)

        # If a .p1log data file exists for this index file, check that the data file size is consistent with the index.
        # If the index doesn't cover the full binary file, the user might have interrupted the read when it was being
        # generated, or they may have overwritten the .p1log file.
        if data_path is None:
            data_path = os.path.splitext(index_path)[0] + '.p1log'
            if not os.path.exists(data_path):
                # If the user didn't explicitly set data_path and the default file doesn't exist, it is not considered
                # an error.
                if self._data['type'][-1] == self.enum_class_invalid:
                    self._data = self._data[:-1]
                return
        elif not os.path.exists(data_path):
            raise ValueError("Specified data file '%s' not found." % data_path)

        with open(data_path, 'rb') as data_file:
            # Compute the data file size.
            data_file.seek(0, io.SEEK_END)
            data_file_size = data_file.tell()
            data_file.seek(0, 0)

            # Check for empty files.
            if data_file_size == 0 and len(self) != 0:
                if delete_on_error:
                    os.remove(index_path)
                raise ValueError("Data file empty but index populated. [%d elements]" % len(self))
            elif data_file_size != 0 and len(self) == 0:
                if delete_on_error:
                    os.remove(index_path)
                raise ValueError("Index file empty but data file not 0 length. [size=%d B]" % data_file_size)

            # Get the last entry in the index. If its message type is INVALID, it's a special marker at the end of the
            # index file indicating the size of the binary data file when the index was created. If it exists, we can
            # use it to check if the data file size has changed.
            if self.type[-1] == self.enum_class_invalid:
                expected_data_file_size = self.offset[-1]
                self._data = self._data[:-1]

                if data_file_size == expected_data_file_size:
                    # If this check passes, we don't need to continue with the other checks below.
                    return
                else:
                    raise ValueError("Size expected by index file does not match binary file. [size=%d B, "
                                     "expected=%d B]" %
                                     (data_file_size, expected_data_file_size))

            # If the index file didn't have a marker entry, try to determine the expected file size based on the index
            # entries. Note that this may fail if the binary file has non-FusionEngine content after the last complete
            # FusionEngine message.

            # See if the last entry in the index is past the end of the data file.
            last_offset = self.offset[-1]
            if last_offset > data_file_size - MessageHeader.calcsize():
                if delete_on_error:
                    os.remove(index_path)
                raise ValueError("Last index entry past end of file. [size=%d B, start_offset=%d B]" %
                                 (data_file_size, last_offset))

            # Read the header of the last entry to get its size, then use that to compute the expected data file size
            # from the offset in the last index entry.
            data_file.seek(last_offset, io.SEEK_SET)
            buffer = data_file.read(MessageHeader.calcsize())
            data_file.seek(0, io.SEEK_SET)

            header = MessageHeader()
            header.unpack(buffer=buffer, warn_on_unrecognized=False)
            message_size_bytes = MessageHeader.calcsize() + header.payload_size_bytes

            expected_data_file_size = last_offset + message_size_bytes
            if expected_data_file_size != data_file_size:
                if delete_on_error:
                    os.remove(index_path)
                raise ValueError("Size expected by index file does not match binary file. [size=%d B, expected=%d B]" %
                                 (data_file_size, expected_data_file_size))

    def save(self, index_path: str, data_path: str):
        """!
        @brief Save the contents of this index as a `.p1i` file.

        @param index_path The path to the file to be written.
        @param data_path The path to the `.p1log` file.
        """
        if len(self._data) > 0:
            # Append an EOF marker at the end of the data if data_path is specified.
            data = self._data
            if data['type'][-1] != self.enum_class_invalid and data_path is not None:
                file_size_bytes = os.stat(data_path).st_size
                data = np.append(data, np.array((np.nan, self.enum_class_invalid, file_size_bytes, -1),
                                                dtype=FileIndex._DTYPE))

            raw_data = FileIndex._to_raw(data)

            if os.path.exists(index_path):
                os.remove(index_path)
            raw_data.tofile(index_path)

    def get_time_range(self, start: Union[Timestamp, float] = None, stop: Union[Timestamp, float] = None,
                       hint: str = None, time_range: TimeRange = None) -> 'FileIndex':
        """!
        @brief Get a subset of the contents for a specified time range.

        @param start The P1 time at the start of the desired time range (inclusive).
        @param stop The P1 time at the end of the desired time range (exclusive).
        @param hint A hint indicating how to handle entries that do not have P1 time (`nan` timestamps):
               - `all_nans` - Return _all_ elements with nan timestamps in addition to entries within the time range,
                 including nan elements outside the time range
               - `include_nans` - Include nan elements within the requested time range (default)
               - `remove_nans` - Do not return nan elements; remove elements falling within the requested time range
        @param time_range A @ref TimeRange object to use instead of `start` and `stop`.

        @return Returns a _copy_ of this class, limited to the requested range.
        """
        if hint is None:
            hint = 'include_nans'

        # If the caller provided a TimeRange object, use that to set start/stop.
        if time_range is not None:
            if start is not None or stop is not None:
                raise ValueError('Cannot specify both a TimeRange and start/stop times.')

            if time_range.absolute:
                start = time_range.start
                stop = time_range.end
            else:
                # If the caller explicitly set t0 in the relative time range, assume they intended for the relative
                # values to be evaluated with respect to that t0, even if it does not match the first message in the
                # index file.
                if time_range.p1_t0:
                    p1_t0 = time_range.p1_t0
                else:
                    p1_t0 = self.t0 if self.t0 is not None else Timestamp()

                start = p1_t0 + time_range.start if time_range.start is not None else None
                stop = p1_t0 + time_range.end if time_range.end is not None else None

        # No data available. Skip time indexing (argmax will fail on an empty vector).
        if len(self._data) == 0:
            return FileIndex(data=np.copy(self._data), t0=self.t0)
        # No time bounds specified. Return the complete dataset.
        elif start is None and stop is None:
            return FileIndex(data=np.copy(self._data), t0=self.t0)
        # If there's no P1 timestamps in the index file whatsoever, t0 will be None. In that case, we cannot apply time
        # bounds to the data, since they are based on P1 time. This should be extremely rare.
        elif self.t0 is None:
            raise IndexError('No P1 timestamps present in index. Cannot apply time bounds.')
        else:
            # Note: The index stores only the integer part of the timestamp.

            # If self._data['time'] ends _before_ `start``, use 0 as start_idx. If self._data['time'] ends _after_
            # `end`, use len(self._data['time']) as end_idx.
            with np.errstate(invalid='ignore'):
                start_idx = find_first(self._data['time'] >= np.floor(start)) if start is not None else 0
                end_idx = find_first(self._data['time'] >= stop) if stop is not None else len(self._data)

            if start_idx < 0:
                start_idx = 0

            if end_idx < 0:
                end_idx = len(self._data['time'])

            if hint == 'include_nans':
                return FileIndex(data=self._data[start_idx:end_idx], t0=self.t0)
            else:
                idx = np.full_like(self._data['time'], False, dtype=bool)
                idx[start_idx:end_idx] = True

                nan_idx = np.isnan(self._data['time'])
                if hint == 'all_nans':
                    idx[nan_idx] = True
                elif hint == 'remove_nans':
                    idx[nan_idx] = False
                else:
                    raise ValueError('Unrecognized control hint.')

            return FileIndex(data=self._data[idx], t0=self.t0)

    def __len__(self):
        return len(self._data['time'])

    def __getattr__(self, key):
        if key == 'time':
            return self._data['time']
        elif key == 'type':
            return self._data['type']
        elif key == 'offset':
            return self._data['offset']
        elif key == 'message_index':
            return self._data['message_index']
        else:
            raise AttributeError

    def __getitem__(self, key):
        # No key specified (convenience case).
        if key is None:
            return copy.copy(self)
        # Key is a string (e.g., index['type']), defer to getattr() (e.g., index.type).
        elif isinstance(key, str):
            return getattr(self, key)
        # No data available.
        elif len(self._data) == 0:
            return FileIndex()
        # Return entries for a specific message type.
        elif isinstance(key, IntEnum):
            idx = self._data['type'] == key
            return FileIndex(data=self._data[idx], t0=self.t0)
        elif MessagePayload.is_subclass(key):
            idx = self._data['type'] == key.get_type()
            return FileIndex(data=self._data[idx], t0=self.t0)
        # Return entries for a list of message types.
        elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(next(iter(key)), IntEnum):
            idx = np.isin(self._data['type'], [int(k) for k in key])
            return FileIndex(data=self._data[idx], t0=self.t0)
        elif isinstance(key, (set, list, tuple)) and len(key) > 0 and MessagePayload.is_subclass(next(iter(key))):
            idx = np.isin(self._data['type'], [int(k.get_type()) for k in key])
            return FileIndex(data=self._data[idx], t0=self.t0)
        # Return a single element by index.
        elif isinstance(key, int):
            return FileIndex(data=self._data[key:(key + 1)], t0=self.t0)
        # Key is a slice in time. Return a subset of the data.
        #
        # For convenience, the user may optionally include a hint string in the `step` portion of the slicing range. For
        # example:
        #   my_index[10:12:'remove_nans']
        elif isinstance(key, slice) and (isinstance(key.start, (Timestamp, float)) or
                                         isinstance(key.stop, (Timestamp, float))):
            hint = key.step
            if hint is not None and not isinstance(hint, str):
                raise ValueError('Step size not supported for time range slicing.')
            return self.get_time_range(start=key.start, stop=key.stop, hint=hint)
        # Key is a TimeRange object. Return a subset of the data. All nan elements (messages without P1 time) will be
        # included in the results.
        elif isinstance(key, TimeRange):
            return self.get_time_range(time_range=key, hint='include_nans')
        # Key is an index slice or a list of individual element indices. Return a subset of the data.
        elif isinstance(key, slice):
            return FileIndex(data=self._data[key], t0=self.t0)
        elif isinstance(key, (set, list, tuple)):
            if len(key) > 0:
                key = np.array(key)
                return FileIndex(data=self._data[key], t0=self.t0)
            else:
                return FileIndex(data=[], t0=self.t0)
        else:
            raise ValueError('Unsupported key type.')

    def __iter__(self):
        if len(self._data) == 0:
            return FileIndexIterator()
        else:
            return FileIndexIterator(self.enum_class, iter(self._data))

    @classmethod
    def get_path(cls, data_path):
        """!
        @brief Get the `.p1i` index file path corresponding with a FusionEngine `.p1log` file.

        @param data_path The path to the `.p1log` file.

        @return The corresponding `.p1i` file path.
        """
        return os.path.splitext(data_path)[0] + '.p1i'

    @classmethod
    def _from_list(cls, data):
        if len(data) == 0:
            return np.array([], dtype=cls._DTYPE)

        if len(data[0]) == 3:
            data = [(*entry, i) for i, entry in enumerate(data)]
        return np.array(data, dtype=FileIndex._DTYPE)

    @classmethod
    def _from_raw(cls, raw_data):
        idx = raw_data['int'] == Timestamp._INVALID

        raw_dtype_with_index = np.dtype(cls._RAW_DTYPE.descr + [('message_index', '<u8')])
        raw_data_with_index = np.ndarray(raw_data.shape, dtype=raw_dtype_with_index)
        for name, _ in cls._RAW_DTYPE.descr:
            raw_data_with_index[name] = raw_data[name]
        raw_data_with_index['message_index'] = np.arange(len(raw_data))

        data = raw_data_with_index.astype(dtype=cls._DTYPE)
        data['time'][idx] = np.nan
        return data

    @classmethod
    def _to_raw(cls, data):
        time_sec = data['time']
        idx = np.isnan(time_sec)
        # Ignore `RuntimeWarning: invalid value encountered in cast` since we want the NaN to be cast to int.
        np.seterr(invalid="ignore")
        raw_data = data[['time', 'type', 'offset']].astype(dtype=cls._RAW_DTYPE)
        np.seterr(invalid="warn")
        raw_data['int'][idx] = Timestamp._INVALID
        return raw_data


class FileIndexBuilder(object):
    """!
    @brief Helper class for constructing a @ref FileIndex.

    This class can be used to construct a @ref FileIndex and a corresponding `.p1i` file when reading a `.p1log` file.
    """

    def __init__(self):
        self.raw_data = []

    def from_file(self, data_path: str):
        """!
        @brief Construct a @ref FileIndex from an existing `.p1log` file.

        @param data_path The path to the `.p1log` file.

        @return The generated @ref FileIndex instance.
        """
        from ..parsers import MixedLogReader
        reader = MixedLogReader(data_path, ignore_index=True, return_offset=True)
        for header, message, offset_bytes in reader:
            p1_time = message.get_p1_time()
            self.append(message_type=header.message_type, offset_bytes=offset_bytes, p1_time=p1_time)
        return self.to_index()

    def append(self, message_type: IntEnum, offset_bytes: int, p1_time: Timestamp = None):
        """!
        @brief Add an entry to the index data being accumulated.

        @param message_type The type of the FusionEngine message.
        @param offset_bytes The offset of the message within the `.p1log` file (in bytes).
        @param p1_time The P1 time of the message, or `None` if the message does not have P1 time.
        """
        if p1_time is None:
            time_sec = np.nan
        else:
            time_sec = float(p1_time)

        self.raw_data.append((time_sec, int(message_type), offset_bytes, len(self.raw_data)))

    def save(self, index_path: str, data_path: str):
        """!
        @brief Save the contents of the generated index as a `.p1i` file.

        @param index_path The path to the file to be written.
        @param data_path The path to the `.p1log` file.
        """
        index = self.to_index()
        index.save(index_path, data_path)
        return index

    def to_index(self):
        """!
        @brief Construct a @ref FileIndex from the current set of data.

        @return The generated @ref FileIndex instance.
        """
        return FileIndex(data=self.raw_data)

    def __len__(self):
        return len(self.raw_data)
