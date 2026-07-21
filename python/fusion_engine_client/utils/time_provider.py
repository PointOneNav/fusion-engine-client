from typing import Optional, TYPE_CHECKING, Union

from datetime import datetime, timedelta

from gpstime import gpstime, gps2unix
import numpy as np

from ..messages import MessageHeader, MessagePayload, PoseMessage, Timestamp
from ..utils import trace as logging

if TYPE_CHECKING:
    from ..analysis.data_loader import DataLoader

_logger = logging.getLogger('point_one.fusion_engine.utils.time_provider')


class TimeProvider:
    """!
    @brief Utility for converting between P1 and GPS time.

    Time relationships may be learned sequentially, by feeding in FusionEngine messages in real time (see @ref
    handle_message()), or in bulk, by loading recorded data from an existing log (see @ref set_reference_data()). The
    time conversion functions (@ref p1_to_gps(), @ref gps_to_p1()) support both scalar (`Timestamp`/`datetime`) or
    vectorized (`numpy.ndarray`) input arguments, and their return types match the argument type.
    """
    def __init__(self):
        self._current_p1_time = Timestamp()
        self._current_gps_time = Timestamp()
        self._prev_p1_time = Timestamp()
        self._prev_gps_time = Timestamp()

        # Bulk P1/GPS correspondence table, used for vectorized conversions. Populated by set_reference_data().
        self._reference_p1_time = np.array([])
        self._reference_gps_time = np.array([])

    def reset(self):
        self._current_p1_time = Timestamp()
        self._current_gps_time = Timestamp()
        self._prev_p1_time = Timestamp()
        self._prev_gps_time = Timestamp()

    def set_reference_data(self, reader: 'DataLoader', source_id: Optional[int] = None):
        """!
        @brief Load time correspondence data from a recorded log file.

        This is intended for offline/post-processing use (e.g., generating plots from an entire log), where the full
        time relationships are available up front. For real-time operation, see @ref handle_message().

        @param reader The @ref DataLoader to read time data from.
        @param source_id If specified, only load time data from this source identifier.
        """
        result = reader.read(message_types=[PoseMessage], source_ids=source_id, return_numpy=True)
        pose_data = result[PoseMessage.MESSAGE_TYPE]

        valid = ~np.isnan(pose_data.p1_time) & ~np.isnan(pose_data.gps_time)
        p1_time = pose_data.p1_time[valid]
        gps_time = pose_data.gps_time[valid]

        # P1 time is monotonic within a single boot session, but resets to 0 after a device reboot, so a reset splits
        # the data into multiple per-session segments. If those segments' P1 time ranges don't overlap, a given P1 time
        # can only belong to one session, so we can safely combine them into a single table sorted by P1 time.
        # Otherwise, the same P1 time could mean two different real times, so we can only safely use the most recent
        # (last) session.
        segments = self._split_into_boot_segments(p1_time, gps_time)
        if len(segments) > 1 and not self._segments_mutually_exclusive(segments):
            _logger.warning('Detected %d device reset(s) in pose data used for time reference, with overlapping P1 '
                            'time ranges across boot sessions. Only using data from the most recent session (%d of '
                            '%d samples).' % (len(segments) - 1, len(segments[-1][0]), len(p1_time)))
            segments = segments[-1:]

        if len(segments) > 0:
            p1_time = np.concatenate([s[0] for s in segments])
            gps_time = np.concatenate([s[1] for s in segments])
            order = np.argsort(p1_time)
            p1_time = p1_time[order]
            gps_time = gps_time[order]

        # Drop non-increasing entries (e.g., duplicate timestamps) so later interpolation can assume P1 time is
        # strictly increasing.
        if len(p1_time) > 0:
            keep = np.concatenate(([True], np.diff(p1_time) > 0))
            p1_time = p1_time[keep]
            gps_time = gps_time[keep]

        self._reference_p1_time = p1_time
        self._reference_gps_time = gps_time

    @staticmethod
    def _split_into_boot_segments(p1_time: np.ndarray, gps_time: np.ndarray) -> list:
        """!
        @brief Split chronologically-ordered entries into contiguous per-boot-session segments, splitting wherever
               P1 time jumps backward (i.e., a device reset).

        @return A list of `(p1_time, gps_time)` `ndarray` pairs, one per boot session.
        """
        if len(p1_time) == 0:
            return []
        reset_idx = np.nonzero(np.diff(p1_time) < -1e-3)[0]
        boundaries = np.concatenate(([0], reset_idx + 1, [len(p1_time)]))
        return [(p1_time[boundaries[i]:boundaries[i + 1]], gps_time[boundaries[i]:boundaries[i + 1]])
                for i in range(len(boundaries) - 1)]

    @staticmethod
    def _segments_mutually_exclusive(segments: list) -> bool:
        """!
        @brief Test whether a list of `(p1_time, gps_time)` boot session segments have non-overlapping P1 time
               ranges, i.e., whether a given P1 time can unambiguously be attributed to a single session.
        """
        ranges = sorted((p1_time[0], p1_time[-1]) for p1_time, _ in segments)
        return all(ranges[i][1] < ranges[i + 1][0] for i in range(len(ranges) - 1))

    def handle_message(self, message: MessagePayload, header: Optional[MessageHeader] = None):
        """!
        @brief Learn time relationships from incoming FusionEngine messages.

        This is intended for handling incoming messages in real time. For post-processing operation, see @ref
        set_reference_data().

        @param header The message header (optional).
        @param message The message payload.
        """
        if isinstance(message, PoseMessage):
            # Sanity check for duplicate or backwards timestamps. In practice this should not happen normally unless the
            # device was reset. If time jumps backward, we'll assume it was a reset and store the new time. If we get a
            # duplicate timestamp, we'll ignore it as a possible error.
            if self._current_p1_time and message.p1_time:
                dt_sec = (message.p1_time - self._current_p1_time).total_seconds()
                if dt_sec < -1e-3:
                    _logger.warning(f'Backwards P1 time jump detected. Did the device restart? '
                                    f'[prev={self._current_p1_time.to_p1_str()}, '
                                    f'current={message.p1_time.to_p1_str()}, dt={dt_sec:.2f} sec]')
                    self.reset()
                elif dt_sec < 1e-3:
                    _logger.warning(f'Duplicate P1 timestamp detected. Ignoring. '
                                    f'[prev={self._current_p1_time.to_p1_str()}, '
                                    f'current={message.p1_time.to_p1_str()}, dt={dt_sec:.2f} sec]')
                    return

            # Store the current and previous P1/GPS times, and use them to convert to/from P1 or GPS time by
            # interpolating (or extrapolating as needed).
            #
            # Note: If we had GPS time and the incoming message no longer does, we will no longer be able to convert
            # P1<->GPS time.
            self._prev_p1_time = self._current_p1_time
            self._prev_gps_time = self._current_gps_time
            self._current_p1_time = message.p1_time
            self._current_gps_time = message.gps_time
            if _logger.isEnabledFor(logging.DEBUG):
                if self._current_p1_time and self._current_gps_time and self._prev_p1_time and self._prev_gps_time:
                    scale_sps = ((self._current_p1_time - self._prev_p1_time).total_seconds() /
                                 (self._current_gps_time - self._prev_gps_time).total_seconds())
                    scale_sps_str = f'{scale_sps:.9f} sec/sec'
                else:
                    scale_sps_str = '<unknown>'
                _logger.debug(f"""\
Received time update ({message.get_type()} message) at:
  P1: {self._current_p1_time.to_p1_str()}
  GPS: {self._current_gps_time.to_gps_str()}
  P1/GPS: {scale_sps_str}
""")

    def p1_to_gps(self, p1_time: Union[Timestamp, np.ndarray], format: str = 'timestamp') -> \
            Union[Timestamp, datetime, np.ndarray]:
        """!
        @brief Convert a P1 timestamp (or array of P1 timestamps) to GPS time.

        @param p1_time The P1 time to convert, either a FusionEngine @ref Timestamp object, or a `numpy.ndarray` of P1
               times in seconds.
        @param format The desired output format:
               - `timestamp` - A FusionEngine @ref Timestamp object, or an `ndarray` of GPS times in seconds
               - `datetime` - A Python `datetime` object, or an `ndarray` of `datetime64[ns]` UTC times

        @return The resulting GPS time, matching the input type (invalid entries are NaN/NaT).
        """
        if isinstance(p1_time, np.ndarray):
            return self._p1_to_gps_array(p1_time, format)
        else:
            return self._p1_to_gps_scalar(p1_time, format)

    def _p1_to_gps_scalar(self, p1_time: Timestamp, format: str = 'timestamp') -> Union[Timestamp, datetime]:
        if not p1_time:
            _logger.trace('Cannot convert invalid P1 time to GPS time.')
            if format == 'datetime':
                return None
            else:
                return Timestamp()
        elif not self._current_p1_time or not self._current_gps_time:
            if _logger.isEnabledFor(logging.TRACE):
                _logger.trace(f'P1/GPS relationship not known. Cannot convert P1 {p1_time.to_p1_str()} to GPS time.')
            if format == 'datetime':
                return None
            else:
                return Timestamp()

        # If we have both P1 and GPS time from the previous update, interpolate (or extrapolate) between the previous
        # update and the current one for the most accurate result.
        if self._prev_p1_time and self._prev_gps_time:
            elapsed_p1_sec = (self._current_p1_time - self._prev_p1_time).total_seconds()
            elapsed_gps_sec = (self._current_gps_time - self._prev_gps_time).total_seconds()
            delta_p1_sec = (p1_time - self._prev_p1_time).total_seconds()
            delta_gps_sec = elapsed_gps_sec * delta_p1_sec / elapsed_p1_sec
            gps_time = self._prev_gps_time + timedelta(seconds=delta_gps_sec)
        # Otherwise, use the current P1/GPS time offset with no interpolation. This will be less accurate since it
        # cannot account for drift between P1 and GPS time, but for most purposes it will be fine as long as
        # _current_*_time is recent.
        else:
            offset_sec = (self._current_gps_time - self._current_p1_time).total_seconds()
            gps_time = p1_time + offset_sec

        if _logger.isEnabledFor(logging.TRACE):
            _logger.trace('Converted P1 %s to GPS %s.', p1_time.to_p1_str(), gps_time.to_gps_str())

        if format == 'datetime':
            return gpstime.fromgps(float(gps_time))
        else:
            return gps_time

    def _p1_to_gps_array(self, p1_time: np.ndarray, format: str) -> np.ndarray:
        xp, fp = self._reference_p1_time, self._reference_gps_time
        if len(xp) == 0:
            xp, fp = self._fallback_reference()

        gps_time = self._interp_extrap(np.asarray(p1_time, dtype=float), xp, fp)

        if format == 'datetime':
            return self._gps_sec_to_datetime64_array(gps_time)
        else:
            return gps_time

    def gps_to_p1(self, gps_time: Union[Timestamp, datetime, gpstime, np.ndarray]) -> Union[Timestamp, np.ndarray]:
        """!
        @brief Convert a GPS timestamp (or array of GPS timestamps) to P1 time.

        @param gps_time The GPS time (or UTC `datetime`) to convert, or a `numpy.ndarray` of GPS times in seconds.

        @return The resulting P1 time, matching the input type (an invalid timestamp, or NaN entries, if the time
                could not be converted).
        """
        if isinstance(gps_time, np.ndarray):
            return self._gps_to_p1_array(gps_time)
        else:
            return self._gps_to_p1_scalar(gps_time)

    def _gps_to_p1_scalar(self, gps_time: Union[Timestamp, datetime, gpstime]) -> Timestamp:
        if not gps_time:
            _logger.trace('Cannot convert invalid GPS time to P1 time.')
            return Timestamp()
        elif isinstance(gps_time, (datetime, gpstime)):
            gps_time = Timestamp.from_datetime(gps_time)

        if not self._current_gps_time or not self._current_p1_time:
            if _logger.isEnabledFor(logging.TRACE):
                _logger.trace(f'GPS/P1 relationship not known. Cannot convert GPS {gps_time.to_gps_str()} to P1 time.')
            return Timestamp()

        # If we have both GPS and P1 time from the previous update, interpolate (or extrapolate) between the previous
        # update and the current one for the most accurate result.
        if self._prev_gps_time and self._prev_p1_time:
            elapsed_p1_sec = (self._current_p1_time - self._prev_p1_time).total_seconds()
            elapsed_gps_sec = (self._current_gps_time - self._prev_gps_time).total_seconds()
            delta_gps_sec = (gps_time - self._prev_gps_time).total_seconds()
            delta_p1_sec = elapsed_p1_sec * delta_gps_sec / elapsed_gps_sec
            p1_time = self._prev_p1_time + timedelta(seconds=delta_p1_sec)
        # Otherwise, use the current GPS/P1 time offset with no interpolation. This will be less accurate since it
        # cannot account for drift between GPS and P1 time, but for most purposes it will be fine as long as
        # _current_*_time is recent.
        else:
            offset_sec = (self._current_p1_time - self._current_gps_time).total_seconds()
            p1_time = gps_time + offset_sec

        if _logger.isEnabledFor(logging.TRACE):
            _logger.trace('Converted GPS %s to P1 %s.', gps_time.to_gps_str(), p1_time.to_p1_str())
        return p1_time

    def _gps_to_p1_array(self, gps_time: np.ndarray) -> np.ndarray:
        xp, fp = self._reference_gps_time, self._reference_p1_time
        if len(xp) == 0:
            fp, xp = self._fallback_reference()

        return self._interp_extrap(np.asarray(gps_time, dtype=float), xp, fp)

    def _fallback_reference(self) -> (np.ndarray, np.ndarray):
        """!
        @brief Build a (p1_time, gps_time) reference table from the current sequential state, for use when no bulk
               reference table has been loaded via @ref set_reference_data().

        @return A tuple `(p1_time, gps_time)` `ndarray`s with 0, 1, or 2 entries.
        """
        if not self._current_p1_time or not self._current_gps_time:
            return np.array([]), np.array([])
        elif self._prev_p1_time and self._prev_gps_time:
            return (np.array([float(self._prev_p1_time), float(self._current_p1_time)]),
                    np.array([float(self._prev_gps_time), float(self._current_gps_time)]))
        else:
            return np.array([float(self._current_p1_time)]), np.array([float(self._current_gps_time)])

    @staticmethod
    def _interp_extrap(query: np.ndarray, xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
        """!
        @brief Vectorized linear interpolation across a reference table, extrapolating beyond either end using the
               nearest segment's slope.

        @param query The query points.
        @param xp Reference table domain values, strictly increasing.
        @param fp Reference table range values, one per entry in `xp`.

        @return The interpolated/extrapolated values, one per entry in `query`. NaN if `xp` is empty.
        """
        n = len(xp)
        if n == 0:
            return np.full_like(query, np.nan, dtype=float)
        elif n == 1:
            return query + (fp[0] - xp[0])
        else:
            idx = np.clip(np.searchsorted(xp, query), 1, n - 1)
            x0, x1 = xp[idx - 1], xp[idx]
            f0, f1 = fp[idx - 1], fp[idx]
            return f0 + (f1 - f0) * (query - x0) / (x1 - x0)

    @staticmethod
    def _gps_sec_to_datetime64_array(gps_time_sec: np.ndarray) -> np.ndarray:
        """!
        @brief Vectorized conversion of GPS times (in seconds) to UTC `datetime64[ns]`.
        """
        result = np.full(gps_time_sec.shape, np.datetime64('NaT'), dtype='datetime64[ns]')
        valid = ~np.isnan(gps_time_sec)
        if np.any(valid):
            # The GPS/UTC offset is constant aside from leap seconds, so compute it once from a representative
            # sample and apply it to the whole array, rather than converting one value at a time.
            ref_gps_sec = gps_time_sec[valid][0]
            posix_offset_sec = gps2unix(ref_gps_sec) - ref_gps_sec
            result[valid] = ((gps_time_sec[valid] + posix_offset_sec) * 1e9).astype('datetime64[ns]')
        return result

