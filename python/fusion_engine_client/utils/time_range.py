from __future__ import annotations

import copy
import math
from typing import Tuple, Union

from ..messages.defs import Timestamp
from ..messages.defs import MessagePayload


class TimeRange(object):
    def __init__(self, start: Union[float, Timestamp], end: Union[float, Timestamp], absolute: bool = False,
                 p1_t0: Timestamp = None, system_t0: float = None):
        self.start = start
        self.end = end
        self.absolute = absolute

        self.p1_t0 = p1_t0
        self.system_t0 = system_t0

        # Convert from Timestamp to seconds.
        if isinstance(self.start, Timestamp):
            if self.start:
                self.start = float(self.start)
            else:
                self.start = None

        if isinstance(self.end, Timestamp):
            if self.end:
                self.end = float(self.end)
            else:
                self.end = None

        # Set 0/inf to None for shortcutting in is_in_range().
        if self.start == 0.0:
            self.start = None

        if self.end is not None and math.isinf(self.end):
            self.end = None

        self._range_specified = self.start is not None or self.end is not None

        self._in_range_started = False
        self._in_range_ended = False

    def restart(self):
        self._in_range_started = False
        self._in_range_ended = False

    def make_absolute(self, p1_t0: Timestamp = None, in_place: bool = True) -> TimeRange:
        if not in_place:
            return copy.copy(self).make_absolute(p1_t0=p1_t0)

        if self.p1_t0 is None:
            self.p1_t0 = p1_t0

        if not self.absolute:
            if p1_t0 is None:
                raise ValueError("T0 not specified. Cannot convert to absolute time range.")

            if self.start is not None:
                self.start += float(self.p1_t0)
            if self.end is not None:
                self.end += float(self.p1_t0)

        return self

    def intersect(self, other: TimeRange, in_place: bool = True) -> TimeRange:
        if not in_place:
            return copy.copy(self).intersect(other)

        # If either range is absolute, enforce that both ranges are absolute before intersecting.
        if self.absolute and not other.absolute:
            other = other.make_absolute(self.p1_t0, in_place=False)
        elif not self.absolute and other.absolute:
            self.make_absolute(other.p1_t0)

        # Intersect the start/end times.
        if self.start is None:
            self.start = other.start
        elif other.start is not None:
            self.start = max(self.start, other.start)

        if self.end is None:
            self.end = other.end
        elif other.end is not None:
            self.end = min(self.end, other.end)

        # Update metadata.
        self._range_specified = self.start is not None or self.end is not None
        if self.p1_t0 is None:
            self.p1_t0 = other.p1_t0
        if self.system_t0 is None:
            self.system_t0 = other.system_t0

        return self

    def is_specified(self) -> bool:
        return self._range_specified

    def in_range_started(self) -> bool:
        return self._in_range_started

    def is_in_range(self, message: Union[MessagePayload, bytes], return_timestamps: bool = False) ->\
            Union[bool, Tuple[bool, Timestamp, float]]:
        # Shortcut if no range is specified.
        if not self._range_specified and not return_timestamps:
            self._in_range_started = True
            return True

        # Extract P1 and system timestamps, where applicable.
        if isinstance(message, MessagePayload):
            p1_time = message.get_p1_time()
            system_time_ns = message.get_system_time_ns()
            system_time_sec = system_time_ns * 1e-9 if system_time_ns is not None else None

            if p1_time is not None and p1_time:
                if self.p1_t0 is None:
                    self.p1_t0 = p1_time

            if system_time_sec is not None:
                if self.system_t0 is None:
                    self.system_t0 = system_time_sec
        else:
            p1_time = None
            system_time_ns = None
            system_time_sec = None

        # Shortcut if no range is specified.
        if not self._range_specified:
            self._in_range_started = True
            return True, p1_time, system_time_ns

        # Select the appropriate timestamp and reference t0 value.
        message_time_sec = None
        ref_time_sec = None
        if (p1_time is None or not p1_time) and (self.absolute or system_time_sec is None):
            # No timestamps available. Handled below.
            pass
        elif p1_time is not None and p1_time:
            message_time_sec = float(p1_time)
            ref_time_sec = float(self.p1_t0)
        elif not self.absolute:
            message_time_sec = system_time_sec
            ref_time_sec = self.system_t0

        # Test if we fall within the time range.
        if message_time_sec is None:
            # If this message doesn't have any timestamps, or we're testing against absolute P1 time and it only has
            # system time, we'll set its status based on whether or not previous messages were in range. For example:
            #   PoseMessage @ 123.4 [out of range]
            #   DummyMessage @ no P1 time [out of range]
            #   PoseMessage @ 124.0 [in range]
            #   DummyMessage @ no P1 time [in range]
            #   PoseMessage @ 125.0 [in range]
            #   DummyMessage @ no P1 time [in range]
            #   PoseMessage @ 126.0 [out of range]
            #   DummyMessage @ no P1 time [out of range]
            #
            # Note that this assumes data is processed in order. If timestamps are received out of order, all messages
            # received after _in_range_ended is set to True will be discarded.
            in_range = self._in_range_started and not self._in_range_ended
        else:
            if self.absolute:
                comparison_time_sec = message_time_sec
            else:
                comparison_time_sec = message_time_sec - ref_time_sec

            if self.start is not None and comparison_time_sec < self.start:
                in_range = False
            elif self.end is not None and comparison_time_sec > self.end:
                in_range = False
            else:
                in_range = True

        if in_range:
            self._in_range_started = True
        elif self._in_range_started:
            self._in_range_ended = True

        if return_timestamps:
            return in_range, p1_time, system_time_ns
        else:
            return in_range

    def __str__(self):
        if self.start is None:
            start = '-inf'
        elif self.absolute:
            start = str(Timestamp(self.start))
        else:
            start = '%.3f sec' % self.start

        if self.end is None:
            end = 'inf'
        elif self.absolute:
            end = str(Timestamp(self.end))
        else:
            end = '%.3f sec' % self.end

        if self.absolute:
            type = 'abs'
        else:
            type = 'rel'

        return f'[start={start}, end={end}, type={type}]'

    @classmethod
    def parse(cls,
              time_range: Union[str,
                                Tuple[Union[float, Timestamp],
                                      Union[float, Timestamp]]],
              absolute: bool = False) -> 'TimeRange':
        if time_range is None:
            return TimeRange(None, None, absolute=absolute)

        start = None
        end = None

        # Split a string range "[START][:END]" into its components.
        is_str = isinstance(time_range, str)
        if is_str:
            time_range = time_range.split(':')

        # Pull out the start and end times.
        if len(time_range) == 1:
            start = time_range[0]
        elif len(time_range) == 2:
            start = time_range[0]
            end = time_range[1]
        elif len(time_range) > 2:
            raise ValueError('Invalid time range specification.')

        # Convert string values to absolute/relative times in seconds. Empty strings are set to None.
        if is_str:
            def _str_to_time(value):
                if value is not None:
                    if value == '':
                        value = None
                    else:
                        value = float(value)
                        if value < 0.0:
                            value = None
                return value

            start = _str_to_time(start)
            end = _str_to_time(end)

        # Construct a time range.
        return TimeRange(start=start, end=end, absolute=absolute)
