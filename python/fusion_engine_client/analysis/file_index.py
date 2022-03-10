from typing import Union

from collections import namedtuple
import os

import numpy as np

from ..messages import MessageType, Timestamp


FileIndexEntry = namedtuple('Element', ['time', 'type', 'offset'])


class FileIndexIterator(object):
    def __init__(self, np_iterator):
        self.np_iterator = np_iterator

    def __next__(self):
        if self.np_iterator is None:
            raise StopIteration()
        else:
            entry = next(self.np_iterator)
            return FileIndexEntry(time=Timestamp(entry[0]), type=MessageType(entry[1]), offset=entry[2])


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

    _DTYPE = np.dtype([('time', '<f8'), ('type', '<u2'), ('offset', '<u8')])

    def __init__(self, index_path: str = None, data: Union[np.ndarray, list] = None, t0: Timestamp = None):
        """!
        @brief Construct a new @ref FileIndex instance.

        @param index_path The path to a `.p1i` index file to be loaded.
        @param data A NumPy `ndarray` or Python `list` containing information about each FusionEngine message in the
               `.p1log` file. For internal use.
        @param t0 The P1 time corresponding with the start of the `.p1log` file, if known. For internal use.
        """
        if data is None:
            self._data = None
        else:
            if isinstance(data, list):
                self._data = np.array(data, dtype=FileIndex._DTYPE)
            elif data.dtype == FileIndex._DTYPE:
                self._data = data
            else:
                raise ValueError('Unsupported array format.')

        if index_path is not None:
            if self._data is None:
                self.load(index_path)
            else:
                raise ValueError('Cannot specify both path and data.')

        if t0 is not None:
            self.t0 = t0
        elif self._data is None:
            self.t0 = None
        else:
            idx = np.argmax(~np.isnan(self._data['time']))
            if idx >= 0:
                self.t0 = Timestamp(self._data['time'][idx])
            else:
                self.t0 = None

    def load(self, index_path):
        """!
        @brief Load a `.p1i` index file from disk.

        @param index_path The path to the file to be read.
        """
        if os.path.exists(index_path):
            raw_data = np.fromfile(index_path, dtype=FileIndex._RAW_DTYPE)
            self._data = FileIndex._from_raw(raw_data)
        else:
            raise FileNotFoundError("Index file '%s' does not exist." % index_path)

    def save(self, index_path):
        """!
        @brief Save the contents of this index as a `.p1i` file.

        @param index_path The path to the file to be written.
        """
        if self._data is not None:
            raw_data = FileIndex._to_raw(self._data)

            if os.path.exists(index_path):
                os.remove(index_path)
            raw_data.tofile(index_path)

    def __len__(self):
        if self._data is None:
            return 0
        else:
            return len(self._data['time'])

    def __getattr__(self, key):
        if key == 'time':
            return self._data['time'] if self._data is not None else None
        elif key == 'type':
            return self._data['type'] if self._data is not None else None
        elif key == 'offset':
            return self._data['offset'] if self._data is not None else None
        else:
            raise AttributeError

    def __getitem__(self, key):
        # No data available.
        if self._data is None:
            return FileIndex()
        # Key is a string (e.g., index['type']), defer to getattr() (e.g., index.type).
        elif isinstance(key, str):
            return getattr(self, key)
        # Return entries for a specific message type.
        elif isinstance(key, MessageType):
            idx = self._data['type'] == key
            return FileIndex(data=self._data[idx], t0=self.t0)
        # Return entries for a list of message types.
        elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(key[0], MessageType):
            idx = np.isin(self._data['type'], key)
            return FileIndex(data=self._data[idx], t0=self.t0)
        # Return a single element by index.
        elif isinstance(key, int):
            return FileIndex(data=self._data[key:(key + 1)], t0=self.t0)
        # Key is a slice in time. Return a subset of the data.
        elif isinstance(key, slice) and (isinstance(key.start, (Timestamp, float)) or
                                         isinstance(key.stop, (Timestamp, float))):
            # Time is continuous, so step sizes are not supported.
            if key.step is not None:
                raise ValueError('Step size not supported for time ranges.')
            else:
                start_idx = np.argmax(self._data['time'] >= key.start) if key.start is not None else 0
                end_idx = np.argmax(self._data['time'] >= key.stop) if key.stop is not None else len(self._data)
                return FileIndex(data=self._data[start_idx:end_idx], t0=self.t0)
        # Key is an index slice or a list of individual element indices. Return a subset of the data.
        else:
            if isinstance(key, (set, list, tuple)):
                key = np.array(key)
            return FileIndex(data=self._data[key], t0=self.t0)

    def __iter__(self):
        if self._data is None:
            return FileIndexIterator(None)
        else:
            return FileIndexIterator(iter(self._data))

    @classmethod
    def get_path(cls, data_path):
        """!
        @brief Get the `.p1i` index file path corresponding with a FusionEngine `.p1log` file.

        @param data_path The path to the `.p1log` file.

        @return The corresponding `.p1i` file path.
        """
        return os.path.splitext(data_path)[0] + '.p1i'

    @classmethod
    def _from_raw(cls, raw_data):
        idx = raw_data['int'] == Timestamp._INVALID
        data = raw_data.astype(dtype=cls._DTYPE)
        data['time'][idx] = np.nan
        return data

    @classmethod
    def _to_raw(cls, data):
        time_sec = data['time']
        idx = np.isnan(time_sec)
        raw_data = data.astype(dtype=cls._RAW_DTYPE)
        raw_data['int'][idx] = Timestamp._INVALID
        return raw_data


class FileIndexBuilder(object):
    """!
    @brief Helper class for constructing a @ref FileIndex.

    This class can be used to construct a @ref FileIndex and a corresponding `.p1i` file when reading a `.p1log` file.
    """
    def __init__(self):
        self.raw_data = []

    def append(self, message_type: MessageType, offset_bytes: int, p1_time: Timestamp = None):
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

        self.raw_data.append((time_sec, int(message_type), offset_bytes))

    def save(self, index_path):
        """!
        @brief Save the contents of the generated index as a `.p1i` file.

        @param index_path The path to the file to be written.
        """
        index = self.to_index()
        index.save(index_path)
        return index

    def to_index(self):
        """!
        @brief Construct a @ref FileIndex from the current set of data.

        @return The generated @ref FileIndex instance.
        """
        return FileIndex(data=self.raw_data)

    def __len__(self):
        return len(self.raw_data)
