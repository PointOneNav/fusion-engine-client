from fusion_engine_client.messages import PoseMessage, Timestamp, VersionInfoMessage
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


def test_absolute_in_range():
    time_range = TimeRange.parse('3:5', absolute=True)
    message = PoseMessage()

    # In range.
    message.p1_time = Timestamp(3.0)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(3.5)
    assert time_range.is_in_range(message)
    message.p1_time = Timestamp(5.0)
    assert time_range.is_in_range(message)

    # Out of range.
    message.p1_time = Timestamp(2.9)
    assert not time_range.is_in_range(message)
    message.p1_time = Timestamp(5.1)
    assert not time_range.is_in_range(message)


def test_relative_in_range():
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
    message.p1_time = Timestamp(5.0)
    assert time_range.is_in_range(message)

    # Out of range.
    message.p1_time = Timestamp(5.1)
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
    message.system_time_ns = int(5.0 * 1e9)
    assert time_range.is_in_range(message)

    # Out of range.
    message.system_time_ns = int(5.1 * 1e9)
    assert not time_range.is_in_range(message)


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
