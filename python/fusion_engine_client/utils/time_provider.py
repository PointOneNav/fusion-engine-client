from typing import Optional, Union

from datetime import datetime, timedelta

from gpstime import gpstime

from ..messages import MessageHeader, MessagePayload, PoseMessage, Timestamp
from ..utils import trace as logging

_logger = logging.getLogger('point_one.fusion_engine.utils.time_provider')


class TimeProvider:
    """!
    @brief Utility for converting between P1 and GPS time.
    """
    def __init__(self):
        self._current_p1_time = Timestamp()
        self._current_gps_time = Timestamp()
        self._prev_p1_time = Timestamp()
        self._prev_gps_time = Timestamp()

    def reset(self):
        self._current_p1_time = Timestamp()
        self._current_gps_time = Timestamp()
        self._prev_p1_time = Timestamp()
        self._prev_gps_time = Timestamp()

    def handle_message(self, message: MessagePayload, header: Optional[MessageHeader] = None):
        """!
        @brief Learn time relationships from incoming FusionEngine messages.

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

    def p1_to_gps(self, p1_time: Timestamp, format: str = 'timestamp') -> Union[Timestamp, datetime]:
        """!
        @brief Convert a P1 timestamp to GPS time.

        @param p1_time The P1 time to convert.
        @param format The desired output format:
               - `timestamp` - A FusionEngine @ref Timestamp object
               - `datetime` - A Python `datetime` object with the corresponding UTC time

        @return The resulting GPS time, or an invalid timestamp if the time could not be converted.
        """
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

    def gps_to_p1(self, gps_time: Union[Timestamp, datetime, gpstime]) -> Timestamp:
        """!
        @brief Convert a GPS timestamp to P1 time.

        @param gps_time The GPS time (or UTC `datetime`) to convert.

        @return The resulting P1 time, or an invalid timestamp if the time could not be converted.
        """
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

