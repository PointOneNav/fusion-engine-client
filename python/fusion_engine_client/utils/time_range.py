import copy
import math
from typing import Optional, Tuple, Union

from ..messages.defs import Timestamp
from ..messages.defs import MessagePayload


class TimeRange(object):
    """!
    @brief Relative or absolute P1 time range specification.

    This class defines a time range of interest, similar to a `slice()` operation for indexed data. The time range is
    defined as `[start, end)`, where both `start` and `end` may be omitted to start at the beginning or the end of the
    dataset.

    For an absolute time range, the start and end values are specified in P1 time. All messages occurring outside the
    time range will be excluded. For example:
    ```
    TimeRange(start=2.0, end=4.0, absolute=True)
    PoseMessage (P1 time 1.0)  <-- Not included
    PoseMessage (P1 time 2.0)  <-- Included
    PoseMessage (P1 time 3.0)  <-- Included
    PoseMessage (P1 time 4.0)  <-- Not included
    ```

    For a relative time range, the start and end values are specified with respect to an initial time, `t0`. `t0` may be
    known ahead of time, or may be determined automatically based on the first P1 timestamp to arrive. For example:
    ```
    TimeRange(start=1.0, end=3.0, absolute=False)
    PoseMessage (P1 time 1.0)  <-- Set t0=1.0; not included (1.0 - t0 = 0.0)
    PoseMessage (P1 time 2.0)  <-- Included (2.0 - t0 = 1.0)
    PoseMessage (P1 time 3.0)  <-- Included (3.0 - t0 = 2.0)
    PoseMessage (P1 time 4.0)  <-- Not included (4.0 - t0 = 3.0)
    ```

    For messages that do not contain P1 timestamps (e.g., @ref EventNotificationMessage), they will be considered in
    range while P1 time is still in range. For example, consider the following sequence of messages:
    ```
    TimeRange(start=1.0, end=3.0, absolute=False)
    EventNotificationMessage (system time 40.0)  <-- Not included
    PoseMessage (P1 time 1.0)                    <-- Set t0=P1 1.0; not included
    EventNotificationMessage (system time 41.0)  <-- Not included (P1 time range not started)
    PoseMessage (P1 time 2.0)                    <-- Included
    EventNotificationMessage (system time 42.0)  <-- Included
    PoseMessage (P1 time 3.0)                    <-- Included
    EventNotificationMessage (system time 43.0)  <-- Included
    PoseMessage (P1 time 4.0)                    <-- Not included
    EventNotificationMessage (system time 44.0)  <-- Not included (P1 time range ended)
    ```

    Note that this is true for all messages that do not contain P1 time, including when applying a relative time range
    to messages with system timestamps. All time ranges are driven by P1 time. It is assumed that any device operating
    normally will continue to output one or more messages containing P1 time.

    For example, even though a relative time range beginning at 0.0 technically includes the first message below
    according to system time, it will be omitted as only P1 timestamps are considered, and no messages with P1 time have
    been included yet:
    ```
    TimeRange(start=0.0, absolute=False)
    EventNotificationMessage (system time 0.0)  <-- Not included
    PoseMessage (P1 time 1.0)                   <-- Set t0=P1 0.0; included (P1 time range started)
    EventNotificationMessage (system time 1.0)  <-- Included
    ```

    The one exception is a time range with an open-ended start time:
    ```
    TimeRange(end=2.0, absolute=False)
    EventNotificationMessage (system time 0.0)  <-- Included (no start time requirement specified)
    PoseMessage (P1 time 1.0)                   <-- Set t0=P1 0.0; included
    EventNotificationMessage (system time 1.0)  <-- Included
    PoseMessage (P1 time 2.0)                   <-- Not included
    EventNotificationMessage (system time 2.0)  <-- Not included (P1 time range started)
    ```
    """
    def __init__(self, start: Optional[Union[float, Timestamp]] = None, end: Optional[Union[float, Timestamp]] = None,
                 absolute: Optional[bool] = None, p1_t0: Optional[Timestamp] = None):
        """!
        @brief Specify a time range (`[start, end)`) used to restrict data reads.

        If `absolute == True`, treat `start` and `end` as absolute P1 timestamps, both for @ref Timestamp objects and
        for `float` values. If `absolute == False`, treat `start` and `end` as relative to the start of the log in P1
        time (`p1_t0`).

        If `absolute` is not specified, apply an absolute time range if either `start` or `end` is a @ref Timestamp
        object, otherwise apply a relative time range with respect to `p1_t0`.

        For relative time ranges, if `p1_t0` is not specified here, it will be determined automatically in @ref
        is_in_range() when the first message containing P1 time arrives.

        @param start The start of the time interval (inclusive). May be a @ref Timestamp object containing a P1 time, or
               an absolute (P1) or relative timestamp (in seconds) depending on the value of `absolute`.
        @param end The end of the time interval (exclusive). May be a @ref Timestamp object containing a P1 time, or
               an absolute (P1) or relative timestamp (in seconds) depending on the value of `absolute`.
        @param absolute If `True`, treat the time range as absolute P1 times.
        @param p1_t0 The P1 time at the start of the data, if known.
        """
        self.start = start
        self.end = end
        self.p1_t0 = Timestamp(p1_t0) if p1_t0 is not None else Timestamp()

        if absolute is None:
            # If absolute is not set, assume an absolute time range if either endpoint is a Timestamp object.
            if isinstance(start, Timestamp) or isinstance(end, Timestamp):
                self.absolute = True
            # Otherwise, assume a relative time range by default.
            else:
                self.absolute = False
        else:
            self.absolute = absolute

        # Convert from Timestamp to seconds. We store timestamps as floats, even for absolute P1 times, so we don't have
        # to handle both Timestamp and float later.
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

        # Set 0/inf to None for shortcutting in is_in_range(). We do not expect P1 time to ever be negative.
        if self.start == 0.0 and self.absolute:
            self.start = None

        if self.end is not None and math.isinf(self.end):
            self.end = None

        self._range_specified = self.start is not None or self.end is not None

        self._in_range_started = False
        self._in_range_ended = False

    def restart(self):
        self._in_range_started = False
        self._in_range_ended = False

    def make_absolute(self, p1_t0: Timestamp = None, in_place: bool = True) -> 'TimeRange':
        if not in_place:
            return copy.deepcopy(self).make_absolute(p1_t0=p1_t0)

        if p1_t0 and not self.p1_t0:
            self.p1_t0 = p1_t0

        if not self.absolute:
            if not self.p1_t0:
                raise ValueError("P1 t0 not specified. Cannot convert to absolute time range.")

            if self.start is not None:
                self.start += float(self.p1_t0)
            if self.end is not None:
                self.end += float(self.p1_t0)

        return self

    def intersect(self, other: 'TimeRange', in_place: bool = True) -> 'TimeRange':
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
        if not self.p1_t0:
            self.p1_t0 = other.p1_t0

        return self

    def is_specified(self) -> bool:
        return self._range_specified

    def in_range_started(self) -> bool:
        return self._in_range_started

    def is_in_range(self, message: Union[MessagePayload, bytes], return_timestamps: bool = False) ->\
            Union[bool, Tuple[bool, Timestamp, float]]:
        """!
        @brief Check if a message falls within the specified time range.

        If `t0` (@ref p1_t0) has not been established and this message contains P1 time, its timestamp will be used to
        set `t0`. Relative time ranges are applied with respect to `t0`.

        @param message The message object to be tested. For parsing convenience, if the object is not @ref
               MessagePayload it will be treated as a generic non-timestamped object, possibly falling within the range
               of valid P1 messages.
        @param return_timestamps If `True`, return a length-3 tuple containing the boolean result, plus the extracted
               P1 and system timestamps, if applicable.

        @return - If `return_timestamps == False`, `True` if the message falls within the time range, or `False`
                  otherwise
                - If `return_timestamps == True`, a `tuple` containing:
                  - The `bool` in-range value described above
                  - The P1 @ref Timestamp extracted from the message if applicable, or `None` otherwise
                  - The system timestamp (in ns) extracted from the message if applicable, or `None` otherwise
        """
        # Shortcut if no range is specified.
        if not self._range_specified and not return_timestamps:
            self._in_range_started = True
            return True

        # Extract P1 and system timestamps, where applicable.
        p1_time_or_none = None
        p1_time = Timestamp()
        system_time_ns = None
        if isinstance(message, MessagePayload):
            p1_time_or_none = message.get_p1_time()
            system_time_ns = message.get_system_time_ns()
            if p1_time_or_none is not None:
                p1_time = p1_time_or_none

            if p1_time and not self.p1_t0:
                self.p1_t0 = p1_time

        # Shortcut if no range is specified.
        if not self._range_specified:
            self._in_range_started = True
            return True, p1_time_or_none, system_time_ns

        # Test if we fall within the time range.
        #
        # If the time range has ended (we went past the last in-range message), consider all further messages out of
        # range.
        if self._in_range_ended:
            in_range = False
        # If this message does not contain P1 time, consider it in range only if other P1-timestamped messages are in
        # currently range. This applies to messages with no timestamps at all, as well as messages that have system time
        # but not P1 time.
        #
        # For example, for absolute time range [124.0, 126.0):
        #   PoseMessage @ P1 123.4 [out of range]
        #   DummyMessage @ no timestamp [out of range]
        #   EventNotificationMessage @ system 3.4 [out of range]
        #   PoseMessage @ P1 124.0 [in range]                <-- Start of in-range region
        #   DummyMessage @ no timestamp [in range]
        #   EventNotificationMessage @ system 4.0 [in range]
        #   PoseMessage @ P1 125.0 [in range]
        #   DummyMessage @ no timestamp [in range]
        #   EventNotificationMessage @ system 5.0 [in range]
        #   PoseMessage @ P1 126.0 [out of range]            <-- End of in-range region
        #   DummyMessage @ no timestamp [out of range]
        #   EventNotificationMessage @ system 6.0 [out of range]
        #
        # Note that this assumes data is processed in order. If timestamps are received out of order, all messages
        # received after _in_range_ended is set to True will be discarded.
        elif not p1_time:
            # The one exception is if the time range has an open start. In that case, all messages are considered
            # in-range immediately, even if we have not seen P1 time yet.
            if self.start is None:
                in_range = True
            else:
                in_range = self._in_range_started
        else:
            # If this is an absolute time range, compare the P1 timestamp directly to the start/end values.
            if self.absolute:
                comparison_time_sec = float(p1_time)
            # Otherwise, compute elapsed time with respect to t0.
            else:
                comparison_time_sec = float(p1_time) - float(self.p1_t0)

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
        # If we entered the time range and the current message has P1 time and is no longer in range, the range has
        # ended. All further messages will be out of range.
        elif self._in_range_started and p1_time:
            self._in_range_ended = True

        if return_timestamps:
            return in_range, p1_time_or_none, system_time_ns
        else:
            return in_range

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end and self.absolute == other.absolute

    def __ne__(self, other):
        return not (self == other)

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
              absolute: Optional[bool] = None) -> 'TimeRange':
        if time_range is None:
            return TimeRange(None, None, absolute=absolute)
        elif isinstance(time_range, TimeRange):
            if absolute is None or absolute == time_range.absolute:
                return time_range
            else:
                raise ValueError('Cannot specify a TimeRange object and absolute argument.')

        start = None
        end = None

        # Split a string range "[START][:END]" into its components.
        is_str = isinstance(time_range, str)
        if is_str:
            time_range = time_range.split(':')

        # Pull out the start and end times.
        if len(time_range) == 1:
            start = time_range[0]
        elif len(time_range) >= 2:
            start = time_range[0]
            end = time_range[1]

        if len(time_range) == 3:
            if time_range[2] == 'abs':
                absolute = True
            elif time_range[2] == 'rel':
                absolute = False
            else:
                raise ValueError('Invalid time range type specifier.')
        elif len(time_range) > 3:
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
