from typing import Union

import os

import numpy as np

from ..messages import MessageType, Timestamp


class FileIndex(object):
    # Note: To reduce the index file size, we've made the following limitations:
    # - Fractional timestamp is floored so time 123.4 becomes 123. The data read should not assume that an entry's
    #   timestamp is its exact time
    RAW_DTYPE = np.dtype([('int', '<u4'), ('type', '<u2'), ('offset', '<u8')])

    DTYPE = np.dtype([('time', '<f8'), ('type', '<u2'), ('offset', '<u8')])

    def __init__(self, data: Union[np.ndarray, list] = None, index_path: str = None, t0: Timestamp = None):
        if data is None:
            self._data = None
        elif isinstance(data, np.ndarray) and data.dtype == FileIndex.RAW_DTYPE:
            self._data = FileIndex._from_raw(data)
        else:
            if isinstance(data, list):
                self._data = np.array(data, dtype=FileIndex.DTYPE)
            elif data.dtype == FileIndex.DTYPE:
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
        if os.path.exists(index_path):
            raw_data = np.fromfile(index_path, dtype=FileIndex.RAW_DTYPE)
            self._data = FileIndex._from_raw(raw_data)
        else:
            raise FileNotFoundError("Index file '%s' does not exist." % index_path)

    def save(self, index_path):
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
        if self._data is None:
            return FileIndex()
        elif isinstance(key, MessageType):
            idx = self._data['type'] == key
            return FileIndex(self._data[idx], t0=self.t0)
        elif isinstance(key, (set, list, tuple)) and len(key) > 0 and isinstance(key[0], MessageType):
            idx = np.isin(self._data['type'], key)
            return FileIndex(self._data[idx], t0=self.t0)
        elif isinstance(key, int):
            return FileIndex(self._data[key:(key + 1)], t0=self.t0)
        else:
            if isinstance(key, (set, list, tuple)):
                key = np.array(key)
            return FileIndex(self._data[key], t0=self.t0)

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


class FileIndexBuilder(object):
    def __init__(self):
        self.raw_data = []

    def append(self, message_type: MessageType, offset_bytes: int, p1_time: Timestamp = None):
        if p1_time is None:
            time_sec = np.nan
        else:
            time_sec = float(p1_time)

        self.raw_data.append((time_sec, int(message_type), offset_bytes))

    def to_index(self):
        return FileIndex(self.raw_data)

    def __len__(self):
        return len(self.raw_data)
