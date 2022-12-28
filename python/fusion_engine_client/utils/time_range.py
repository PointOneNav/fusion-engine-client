from __future__ import annotations

import copy
import math
from typing import Tuple, Union

from ..messages.defs import Timestamp
from ..messages.defs import MessagePayload


class TimeRange(object):
    def __init__(self, start: Union[float, Timestamp] = None, end: Union[float, Timestamp] = None,
                 absolute: bool = False, p1_t0: Timestamp = None, system_t0: float = None):
        """!
        @brief Specify a time range (`[start, end)`) used to restrict data reads.

        @param start The start of the time interval (inclusive). May be a relative timestamp (in seconds), or a @ref
               Timestamp object containing a P1 time.
        @param end The end of the time interval (exclusive). May be a relative timestamp (in seconds), or a @ref
               Timestamp object containing a P1 time.
        @param absolute If `True`, treat the time range as absolute P1 times.
        @param p1_t0 The P1 time at the start of the data, if known.
        @param system_t0 The system time (in seconds) at the start of the data, if known.
        """
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
        self._p1_time_seen = self.p1_t0 is not None and self.p1_t0

    def restart(self):
        self._in_range_started = False
        self._in_range_ended = False
        self._p1_time_seen = self.p1_t0 is not None and self.p1_t0

    def make_absolute(self, p1_t0: Timestamp = None, in_place: bool = True) -> TimeRange:
        if not in_place:
            return copy.copy(self).make_absolute(p1_t0=p1_t0)

        if self.p1_t0 is None:
            self.p1_t0 = p1_t0
            self._p1_time_seen = self.p1_t0 is not None and self.p1_t0

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
            self._p1_time_seen = self.p1_t0 is not None and self.p1_t0
        if self.system_t0 is None:
            self.system_t0 = other.system_t0

        return self

    def is_specified(self) -> bool:
        return self._range_specified

    def in_range_started(self) -> bool:
        return self._in_range_started

    def is_in_range(self, message: Union[MessagePayload, bytes], return_timestamps: bool = False) ->\
            Union[bool, Tuple[bool, Timestamp, float]]:
        """!
        @brief Check if a message falls within the specified time range.

        Important: For relative time ranges, this function treats P1 and system _start_ times independently, but the end
        of the time range depends on P1 time. For example, consider the following sequence of messages:
        ```
        Event (system time 0)
        Pose (P1 time 1)
        Pose (P1 time 2)
        Event (system time 2)
        Pose (P1 time 3)
        Event (system time 3)
        Pose (P1 time 4)
        Event (system time 4)
        ```

        Say we specify a relative time range ending after 3 seconds (exclusive):
        ```py
        TimeRange(end=3.0)
        ```

        The results will include event messages from system time 0.0-2.0, and pose messages from P1 time 1.0-3.0.
        Even though the system time range, dictated by the event data, ends before the pose at P1 time 3.0, P1 time is
        considered independent of system time.

        On the other hand, if we omit the event at system time 0:
        ```
        Pose (P1 time 1)
        Pose (P1 time 2)
        Event (system time 2)
        Pose (P1 time 3)
        Event (system time 3)
        Pose (P1 time 4)
        Event (system time 4)
        ```

        Now, the relative range for system time is <3 seconds. However, since the P1 time range ends at P1 time 4.0,
        only system times 2.0-3.0 are included.

        @note
        While odd, this behavior is intentional for consistency with `.p1i` index files (@ref FileIndex). Index files do
        not have knowledge of system timestamps, only P1 timestamps, so they cannot consider each time type
        independently.

        Separately, for absolute time ranges, system time messages occurring before the first _included_ P1 timestamp
        will be omitted. P1 and system time are not correlated, so we must wait for P1 time to know if messages with
        system timestamps may be included.

        For the first example above, say we have the following time range ending at P1 time 4.0 (exclusive):
        ```py
        TimeRange(end=4.0, absolute=True)
        ```

        The results will include pose data from P1 time 1.0-3.0 and event messages for system time 2.0-3.0. The event at
        system time 0.0 will be dropped even though the time range does not specify a start time.

        @param message The message object to be tested. For parsing convenience, if the object is not @ref
               MessagePayload it will be treated as a generic non-timestamped object, possibly falling within the range
               of valid P1 messages.
        @param return_timestamps If `True`, return a length-3 tuple containing the boolean result, plus the extracted
               P1 and system timestamps, if applicable.
        """
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
                    self._p1_time_seen = self.p1_t0 is not None and self.p1_t0

            if system_time_sec is not None:
                if self.system_t0 is None:
                    self.system_t0 = system_time_sec
        else:
            p1_time = None
            system_time_ns = None
            system_time_sec = None

        p1_time_orig = p1_time
        p1_time = Timestamp() if p1_time_orig is None else p1_time_orig

        # Shortcut if no range is specified.
        if not self._range_specified:
            self._in_range_started = True
            return True, p1_time, system_time_ns

        # Select the appropriate timestamp and reference t0 value.
        message_time_sec = None
        ref_time_sec = None
        if not p1_time and (self.absolute or system_time_sec is None):
            # No timestamps available. Handled below.
            pass
        elif p1_time:
            message_time_sec = float(p1_time)
            ref_time_sec = float(self.p1_t0)
        elif not self.absolute:
            message_time_sec = system_time_sec
            ref_time_sec = self.system_t0

        # Test if we fall within the time range.
        if self._in_range_ended:
            in_range = False
        elif message_time_sec is None:
            # If this message doesn't have any timestamps, or we're testing against absolute P1 time and it only has
            # system time, we'll set its status based on whether or not previous messages were in range. For example:
            #   PoseMessage @ 123.4 [out of range]
            #   DummyMessage @ no timestamp [out of range]
            #   PoseMessage @ 124.0 [in range]
            #   DummyMessage @ no timestamp [in range]
            #   PoseMessage @ 125.0 [in range]
            #   DummyMessage @ no timestamp [in range]
            #   PoseMessage @ 126.0 [out of range]
            #   DummyMessage @ no timestamp [out of range]
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
            elif self.end is not None and comparison_time_sec >= self.end:
                in_range = False
            else:
                in_range = True

        # If this message is within the bounds, we are now in the time range. Any non-timestamped messages will be
        # considered in range.
        if in_range:
            self._in_range_started = True
        # If the message is no longer in the bounds, we _may_ end the time range. If this message has P1 time, that is
        # the end of the range: do not consider _any_ messages after this one. If the message does not have P1 time,
        # only system time, _and_ we have not ever seen P1 time, we'll let system time declare end of range.
        #
        # For example, say we have a relative range from (0.0, 2.0]:
        #   PoseMessage @ P1 124.0 [in range]
        #   EventNotificationMessage @ system 4.7 [in range]
        #   PoseMessage @ P1 125.0 [in range]
        #   EventNotificationMessage @ system 5.7  [in range]
        #   PoseMessage @ P1 126.0 [out of range]
        #   EventNotificationMessage @ system 6.2  [out of range]
        #   ^-- Considered out of range, even though it's only 1.5 seconds away from the first event
        #
        # This is a slightly unexpected behavior, but is necessary for consistency with FileIndex. Index files do not
        # have access to system time, so they cannot treat P1 and system timestamps independently for relative ranges.
        elif self._in_range_started and (p1_time or not self._p1_time_seen):
            self._in_range_ended = True

        if return_timestamps:
            return in_range, p1_time_orig, system_time_ns
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
