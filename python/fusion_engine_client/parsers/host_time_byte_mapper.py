import os
from typing import Iterable, Tuple

import numpy as np
import numpy.typing as npt


class HostTimeByteMapper:
    """!
    @brief An index of host time to byte offset entries.

    A "host time" is the Unix time in seconds.

    This class reads a `*_host_times.bin` file from disk containing. This can then be used to associate messages with
    host times by there byte offset into their data files.
    """

    # [Host Posix Time in Seconds, Log Byte Offset]
    _DTYPE = np.dtype('f8,u8')

    def __init__(self, data_path: str = None):
        """!
        @brief Construct a new @ref HostTimeByteMapper instance.

        Data must be loaded with call to @ref load_from_file or @ref load_list.

        @param data_path The path to the message data file (`*.p1log`) to associate host times with.
        """
        self.data = np.array([], dtype=self._DTYPE)
        self.index_path = os.path.splitext(data_path)[0] + '_host_times.bin'

    def load_list(self, data: Iterable[Tuple[int, int]]):
        """!
        @brief Specify host time mappings from Python list.
        """
        self.data = np.array(data, dtype=self._DTYPE)

    def write_to_file(self):
        """!
        @brief Write host time mappings to file.
        """
        self.data.tofile(self.index_path)

    def does_host_time_file_exist(self) -> bool:
        """!
        @brief Check if host time data file exists for specified data_path.
        """
        return os.path.exists(self.index_path)

    def load_from_file(self):
        """!
        @brief Specify host time mappings from Python list.
        """
        self.data = np.fromfile(self.index_path, dtype=self._DTYPE)

    def map_to_msg_offsets(self, msg_offsets: Iterable[int]) -> npt.NDArray[np.float64]:
        """!
        @brief Get the host times corresponding to a list of offsets into the data_path.

        This might be faster in some cases with np.searchsorted. Doing a naive search for simplicity.

        @param msg_offsets A sorted list of offsets to get host times for.

        @return The host times associated with each `msg_offsets`. For each offset, the host time is where the
                received bytes exceeded the specified byte offset.
        """
        # This might be faster in some cases with np.searchsorted. Doing a naive
        # search for simplicity.
        host_times = np.zeros(len(msg_offsets), dtype=np.float64)
        host_idx = 0
        for i, offset in enumerate(msg_offsets):
            while offset > self.data[host_idx][1]:
                host_idx += 1
            host_times[i] = self.data[host_idx][0]
        return host_times
