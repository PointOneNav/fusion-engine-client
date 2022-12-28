from fusion_engine_client.messages import *
from fusion_engine_client.utils.time_range import TimeRange


def test_parse_full():
    time_range = TimeRange.parse('3:5')
    assert time_range.start == 3.0
    assert time_range.end == 5.0


def test_parse_start_only():
    time_range = TimeRange.parse('3')
    assert time_range.start == 3.0
    assert time_range.end is None

    time_range = TimeRange.parse('3:')
    assert time_range.start == 3.0
    assert time_range.end is None


def test_parse_end_only():
    time_range = TimeRange.parse(':5')
    assert time_range.start is None
    assert time_range.end == 5.0


def test_parse_empty():
    time_range = TimeRange.parse('')
    assert time_range.start is None
    assert time_range.end is None
    assert not time_range._range_specified


def test_absolute_p1_time():
    time_range = TimeRange.parse('3:5', absolute=True)
    message = PoseMessage()

    # In range.
    message.p1_time = Timestamp(3.0)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(3.5)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(4.999)
    assert time_range.is_in_range(message)

    # Out of range.
    message.p1_time = Timestamp(2.9)
    assert not time_range.is_in_range(message)
    message.p1_time = Timestamp(5.0)
    assert not time_range.is_in_range(message)


def test_relative_p1_time():
    time_range = TimeRange.parse('1:2', absolute=False)
    message = PoseMessage()

    # Establish t0 == 3 seconds. The range starts at 1, so this message is _not_ in the range.
    message.p1_time = Timestamp(3.0)
    assert not time_range.is_in_range(message)

    # In range.
    message.p1_time = Timestamp(4.0)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(4.5)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(4.999)
    assert time_range.is_in_range(message)

    # Out of range.
    message.p1_time = Timestamp(5.0)
    assert not time_range.is_in_range(message)


def test_relative_system_time():
    time_range = TimeRange.parse('1:2', absolute=False)
    message = VersionInfoMessage()

    # Establish t0 == 3 seconds. The range starts at 1, so this message is _not_ in the range.
    message.system_time_ns = int(3.0 * 1e9)
    assert not time_range.is_in_range(message)

    # In range.
    message.system_time_ns = int(4.0 * 1e9)
    assert time_range.is_in_range(message)
    message.system_time_ns = int(4.5 * 1e9)
    assert time_range.is_in_range(message)
    message.system_time_ns = int(4.999 * 1e9)
    assert time_range.is_in_range(message)

    # Out of range.
    message.system_time_ns = int(5.0 * 1e9)
    assert not time_range.is_in_range(message)


def test_absolute_mixed_time():
    time_range = TimeRange.parse('3:5', absolute=True)
    pose = PoseMessage()
    event = EventNotificationMessage()
    reset = ResetRequest()

    # All non-P1 timestamped messages occurring before the first P1 message will be considered out of range.
    event.system_time_ns = int(14.2 * 1e9)
    assert not time_range.is_in_range(event)
    event.system_time_ns = int(15.5 * 1e9)
    assert not time_range.is_in_range(event)
    assert not time_range.is_in_range(reset)

    pose.p1_time = Timestamp(2.999)
    assert not time_range.is_in_range(pose)
    event.system_time_ns = int(15.5 * 1e9)
    assert not time_range.is_in_range(event)
    assert not time_range.is_in_range(reset)

    # Begin in range.
    pose.p1_time = Timestamp(4.0)
    assert time_range.is_in_range(pose)
    assert time_range.is_in_range(event)
    assert time_range.is_in_range(reset)

    event.system_time_ns = int(14.2 * 1e9)  # Time went backwards, but only P1 time matters here.
    assert time_range.is_in_range(event)

    pose.p1_time = Timestamp(4.5)
    assert time_range.is_in_range(pose)
    pose.p1_time = Timestamp(4.999)
    assert time_range.is_in_range(pose)
    assert time_range.is_in_range(event)
    assert time_range.is_in_range(reset)

    # Out of range of P1 time.
    pose.p1_time = Timestamp(5.0)
    assert not time_range.is_in_range(pose)
    assert not time_range.is_in_range(event)


def test_relative_mixed_time():
    time_range = TimeRange.parse('1:2', absolute=False)
    pose = PoseMessage()
    event = EventNotificationMessage()
    reset = ResetRequest()

    # Establish t0 == 3 seconds. The range starts at 1, so this pose is _not_ in the range.
    pose.p1_time = Timestamp(3.0)
    assert not time_range.is_in_range(pose)

    # Establish system t0 = 13.5 seconds. This is independent of P1 time.
    event.system_time_ns = int(13.5 * 1e9)
    assert not time_range.is_in_range(event)

    # Check in range.
    #
    # We use reset requests messages as a stand-in for anything that doesn't have a timestamp. They are considered in
    # range only when the other message types are.
    assert not time_range.is_in_range(reset)

    pose.p1_time = Timestamp(4.0)
    assert time_range.is_in_range(pose)
    assert time_range.is_in_range(reset)

    event.system_time_ns = int(14.2 * 1e9)  # Not in range - independent of P1 time.
    assert not time_range.is_in_range(event)

    event.system_time_ns = int(14.5 * 1e9)
    assert time_range.is_in_range(event)

    pose.p1_time = Timestamp(4.5)
    assert time_range.is_in_range(pose)
    pose.p1_time = Timestamp(4.999)
    assert time_range.is_in_range(pose)

    event.system_time_ns = int(15.499 * 1e9)
    assert time_range.is_in_range(event)

    # This message is out of range for system time. It should not prevent us outputting non-timestamped messages,
    # however, since P1 time is present.
    event.system_time_ns = int(15.5 * 1e9)
    assert not time_range.is_in_range(event)
    assert time_range.is_in_range(reset)

    # Out of range of P1 time.
    pose.p1_time = Timestamp(5.0)
    assert not time_range.is_in_range(pose)
    assert not time_range.is_in_range(reset)

    # Now we'll check for an _in_ range system time message. If the P1 time declares the end of the range, all messages,
    # including system times, are considered out of range. This is necessary for consistency with FileIndex (see
    # is_in_range() documentation).
    #
    # This is out of order, but TimeRange shouldn't have any state with respect to system times, so that should be ok.
    event.system_time_ns = int(14.5 * 1e9)
    assert not time_range.is_in_range(event)


def test_return_timestamps():
    time_range = TimeRange.parse('0:2', absolute=False)

    message = PoseMessage()
    message.p1_time = Timestamp(3.0)
    result = time_range.is_in_range(message, return_timestamps=True)
    assert len(result) == 3
    assert result[0]
    assert result[1] == message.p1_time
    assert result[2] is None

    message = VersionInfoMessage()
    message.system_time_ns = int(3.0 * 1e9)
    result = time_range.is_in_range(message, return_timestamps=True)
    assert len(result) == 3
    assert result[0]
    assert result[1] is None
    assert result[2] == 3000000000


def test_timestamp_invalid():
    time_range = TimeRange.parse('', absolute=False)
    message = PoseMessage()
    assert time_range.is_in_range(message)

    time_range = TimeRange.parse('0:2', absolute=False)
    message = PoseMessage()
    assert not time_range.is_in_range(message)


def test_defer_no_timestamp():
    time_range = TimeRange.parse('1:2', absolute=False)
    timed_message = PoseMessage()
    untimed_message = PoseMessage()

    # Time range not entered yet - untimestamped messages will be considered out of range.
    timed_message.p1_time = Timestamp(3.0)
    assert not time_range.is_in_range(timed_message)
    assert not time_range.is_in_range(untimed_message)

    # Enter range - untimestamped messages now considered in range.
    timed_message.p1_time = Timestamp(4.0)
    assert time_range.is_in_range(timed_message)
    assert time_range.is_in_range(untimed_message)
    timed_message.p1_time = Timestamp(4.5)
    assert time_range.is_in_range(timed_message)
    assert time_range.is_in_range(untimed_message)

    # Exit time range - untimestamped messages no longer in range.
    timed_message.p1_time = Timestamp(5.1)
    assert not time_range.is_in_range(timed_message)
    assert not time_range.is_in_range(untimed_message)


def test_make_absolute():
    time_range = TimeRange.parse('1:2', absolute=False)
    assert not time_range.absolute

    time_range.make_absolute(p1_t0=Timestamp(4.5))
    assert time_range.start == 5.5
    assert time_range.end == 6.5


def test_intersect_in_place():
    a = TimeRange.parse('1:10', absolute=False)
    b = TimeRange.parse('2:6', absolute=False)
    a.intersect(b)
    assert a.start == 2
    assert a.end == 6

    a = TimeRange.parse('1:10', absolute=False)
    b = TimeRange.parse('2:12', absolute=False)
    a.intersect(b)
    assert a.start == 2
    assert a.end == 10

    a = TimeRange.parse('3:10', absolute=False)
    b = TimeRange.parse('1:12', absolute=False)
    a.intersect(b)
    assert a.start == 3
    assert a.end == 10


def test_intersect_copy():
    a = TimeRange.parse('1:10', absolute=False)
    b = TimeRange.parse('2:6', absolute=False)
    result = a.intersect(b, in_place=False)
    assert a.start == 1
    assert a.end == 10
    assert result.start == 2
    assert result.end == 6


def test_intersect_abs_rel():
    a = TimeRange.parse('4:10', absolute=True)
    a.make_absolute(Timestamp(3.0))
    b = TimeRange.parse('2:6', absolute=False)
    a.intersect(b)
    assert a.start == 5
    assert a.end == 9
