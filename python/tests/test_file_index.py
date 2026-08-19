import os

import numpy as np
import pytest

from fusion_engine_client.messages import MessageType, Timestamp, message_type_to_class
from fusion_engine_client.parsers import FusionEngineEncoder
from fusion_engine_client.parsers.file_index import FileIndex, FileIndexBuilder, TimeRange

RAW_DATA = [
    (None, MessageType.VERSION_INFO, 0),
    (Timestamp(1.0), MessageType.POSE, 10),
    (Timestamp(2.0), MessageType.POSE, 20),
    (Timestamp(2.0), MessageType.GNSS_INFO, 30),
    (None, MessageType.VERSION_INFO, 40),
    (Timestamp(3.0), MessageType.POSE, 50),
    (Timestamp(4.0), MessageType.POSE, 60),
]
RAW_DATA = [(*entry, i) for i, entry in enumerate(RAW_DATA)]


def _make_index(entries):
    return FileIndex(data=[(*entry, i) for i, entry in enumerate(entries)])


def _test_time(time, raw_data):
    raw_time = [e[0] for e in raw_data]
    raw_is_none = [e is None for e in raw_time]
    idx = np.logical_or(time == raw_time, np.logical_and(np.isnan(time), raw_is_none))
    return idx.all()


def test_index():
    index = FileIndex(data=RAW_DATA)
    assert len(index) == len(RAW_DATA)

    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE]
    idx = index.type == MessageType.POSE
    assert np.sum(idx) == len(raw)
    assert _test_time(index.time[idx], raw)
    assert (index.offset[idx] == [e[2] for e in raw]).all()
    assert (index.message_index[idx] == [e[3] for e in raw]).all()

    raw = [e for e in RAW_DATA if e[1] == MessageType.VERSION_INFO]
    idx = index.type == MessageType.VERSION_INFO
    assert _test_time(index.time[idx], raw)
    assert (index.offset[idx] == [e[2] for e in raw]).all()
    assert (index.message_index[idx] == [e[3] for e in raw]).all()


def test_iterator():
    index = FileIndex(data=RAW_DATA)
    for i, entry in enumerate(index):
        assert entry.type == RAW_DATA[i][1]


def test_type_slice():
    index = FileIndex(data=RAW_DATA)

    pose_index = index[MessageType.POSE]
    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()
    assert (pose_index.message_index == [e[3] for e in raw]).all()

    pose_index = index[(MessageType.POSE, MessageType.GNSS_INFO)]
    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE or e[1] == MessageType.GNSS_INFO]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()
    assert (pose_index.message_index == [e[3] for e in raw]).all()

    pose_index = index[MessageType.POSE, 'invert']
    raw = [e for e in RAW_DATA if e[1] != MessageType.POSE]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()
    assert (pose_index.message_index == [e[3] for e in raw]).all()


def test_index_slice():
    index = FileIndex(data=RAW_DATA)

    # Access a single element.
    sliced_index = index[3]
    raw = [RAW_DATA[3]]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access to the end.
    sliced_index = index[3:]
    raw = RAW_DATA[3:]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access from the beginning.
    sliced_index = index[:3]
    raw = RAW_DATA[:3]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access a range.
    sliced_index = index[2:4]
    raw = RAW_DATA[2:4]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access individual indices.
    sliced_index = index[(2, 3, 5)]
    raw = [RAW_DATA[i] for i in (2, 3, 5)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Pass empty set -- remove all elements.
    sliced_index = index[set()]
    raw = []
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()


def test_time_slice():
    def _lower_bound(time):
        return next(i for i, e in enumerate(RAW_DATA) if (e[0] is not None and e[0] >= time))

    index = FileIndex(data=RAW_DATA)

    # Access to the end.
    sliced_index = index[2.0:]
    raw = RAW_DATA[_lower_bound(2.0):]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access from the beginning.
    sliced_index = index[:3.0]
    raw = RAW_DATA[:_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access a range.
    sliced_index = index[2.0:3.0]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access by Timestamp.
    sliced_index = index[Timestamp(2.0):Timestamp(3.0)]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()


def test_time_range_slice():
    def _lower_bound(time):
        return next(i for i, e in enumerate(RAW_DATA) if (e[0] is not None and e[0] >= time))

    index = FileIndex(data=RAW_DATA)

    # Access to the end.
    sliced_index = index[TimeRange(start=2.0, absolute=True)]
    raw = RAW_DATA[_lower_bound(2.0):]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access from the beginning.
    sliced_index = index[TimeRange(end=3.0, absolute=True)]
    raw = RAW_DATA[:_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Access a range.
    sliced_index = index[TimeRange(start=2.0, end=3.0, absolute=True)]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Relative time range, assuming the first P1 time is 1.0.
    sliced_index = index[TimeRange(start=1.0, end=2.0, absolute=False)]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Relative time range with an explicit t0 that differs from the actual index data: use the t0 in the range.
    sliced_index = index[TimeRange(start=1.0, end=2.0, absolute=False, p1_t0=Timestamp(0.0))]
    raw = RAW_DATA[_lower_bound(1.0):_lower_bound(2.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # End time beyond end of data: the range extends to the end of the data.
    sliced_index = index[TimeRange(end=1000.0, absolute=True)]
    assert _test_time(sliced_index.time, RAW_DATA)
    assert (sliced_index.offset == [e[2] for e in RAW_DATA]).all()
    assert (sliced_index.message_index == [e[3] for e in RAW_DATA]).all()

    # Start time within the data, end time beyond the end of the data.
    sliced_index = index[TimeRange(start=3.0, end=1000.0, absolute=True)]
    raw = RAW_DATA[_lower_bound(3.0):]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Start time beyond end of data.
    sliced_index = index[TimeRange(start=1000.0, absolute=True)]
    assert len(sliced_index) == 0

    # End time before start of data.
    sliced_index = index[TimeRange(end=-1.0, absolute=True)]
    assert len(sliced_index) == 0

    # Start time beyond end of data, but "all_nans" requested.
    sliced_index = index.get_time_range(time_range=TimeRange(start=1000.0, absolute=True), hint='all_nans')
    raw = [m for m in RAW_DATA if m[0] is None]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Same using getitem hint syntax.
    sliced_index = index[TimeRange(start=1000.0, absolute=True), 'all_nans']
    raw = [m for m in RAW_DATA if m[0] is None]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()


def test_time_range_slice_corner_cases():
    index = FileIndex(data=RAW_DATA)

    # The index stores only the integer part of each timestamp, so both bounds are intentionally over-inclusive: a
    # fractional `start` is floored so we don't drop a message whose true time may fall in range, and a fractional
    # `stop` keeps the messages sharing its integer second.
    sliced_index = index[TimeRange(start=2.5, end=3.5, absolute=True)]
    raw = RAW_DATA[2:6]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    # Empty and inverted ranges.
    assert len(index[TimeRange(start=3.0, end=3.0, absolute=True)]) == 0
    assert len(index[TimeRange(start=3.0, end=2.0, absolute=True)]) == 0

    # An initial block of messages without P1Time is treated as being "before" a specified `start`, and is included only
    # when `start` is not specified. Note that TimeRange normalizes an absolute start of 0.0 to None ("not specified"),
    # so use a nonzero start that still precedes the first timestamp.
    leading_index = _make_index([
        (None, MessageType.VERSION_INFO, 0),
        (None, MessageType.VERSION_INFO, 10),
        (Timestamp(6.0), MessageType.POSE, 20),
        (Timestamp(7.0), MessageType.POSE, 30),
        (Timestamp(8.0), MessageType.POSE, 40),
    ])
    sliced_index = leading_index[TimeRange(end=7.0, absolute=True)]
    assert (sliced_index.message_index == [0, 1, 2]).all()
    sliced_index = leading_index[TimeRange(start=1.0, end=7.0, absolute=True)]
    assert (sliced_index.message_index == [2]).all()

    # Corner case: the log starts after the requested stop time, but begins with messages without P1Time. Those
    # messages must not be treated as in range, since no timestamped data is in range at all.
    assert len(leading_index[TimeRange(end=4.0, absolute=True)]) == 0

    # The leading messages are still returned if the caller explicitly asks for all nans.
    sliced_index = leading_index[TimeRange(end=4.0, absolute=True), 'all_nans']
    assert (sliced_index.message_index == [0, 1]).all()

    # Same corner case, but with a `stop` of 0.0: the range is empty, so the leading messages are still out of range.
    # Note that this requires testing `stop is not None`, not the truthiness of `stop`.
    assert len(leading_index[TimeRange(end=0.0, absolute=True)]) == 0
    assert len(leading_index.get_time_range(stop=0.0)) == 0

    # A final block of messages without P1Time is in range as long as the range has not already ended, i.e. as long as
    # no timestamp >= `stop` was found. This matches TimeRange.is_in_range(), which only ends a range on a timestamped
    # message, so that an indexed read and a non-indexed read of the same log agree.
    trailing_index = _make_index([
        (Timestamp(1.0), MessageType.POSE, 0),
        (Timestamp(2.0), MessageType.POSE, 10),
        (None, MessageType.VERSION_INFO, 20),
        (None, MessageType.VERSION_INFO, 30),
    ])
    sliced_index = trailing_index[TimeRange(start=1.0, absolute=True)]
    assert (sliced_index.message_index == [0, 1, 2, 3]).all()
    sliced_index = trailing_index[TimeRange(start=1.0, end=1000.0, absolute=True)]
    assert (sliced_index.message_index == [0, 1, 2, 3]).all()

    # ...but once a timestamp >= `stop` is found, the range ends there, so a following block is out of range.
    sliced_index = trailing_index[TimeRange(start=1.0, end=2.0, absolute=True)]
    assert (sliced_index.message_index == [0]).all()

    # A block of messages without P1Time between two timestamps is in range as usual.
    interior_index = _make_index([
        (Timestamp(1.0), MessageType.POSE, 0),
        (None, MessageType.VERSION_INFO, 10),
        (Timestamp(9.0), MessageType.POSE, 20),
    ])
    sliced_index = interior_index[TimeRange(start=1.0, end=1000.0, absolute=True)]
    assert (sliced_index.message_index == [0, 1, 2]).all()
    sliced_index = interior_index[TimeRange(start=1.0, end=9.0, absolute=True)]
    assert (sliced_index.message_index == [0, 1]).all()

    # Untimed messages within the range may be dropped on request.
    sliced_index = index.get_time_range(time_range=TimeRange(start=1.0, end=3.0, absolute=True), hint='remove_nans')
    raw = [e for e in RAW_DATA[1:5] if e[0] is not None]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.message_index == [e[3] for e in raw]).all()

    with pytest.raises(ValueError):
        index.get_time_range(time_range=TimeRange(start=1.0, absolute=True), hint='not_a_hint')

    # No time bounds specified: return everything.
    sliced_index = index.get_time_range()
    assert (sliced_index.message_index == [e[3] for e in RAW_DATA]).all()

    # An index containing _only_ messages without P1Time, but which still knows its t0 -- as produced by an 'all_nans'
    # slice -- can be sliced by time again. Its handling depends on which bounds were specified:
    nan_only = index[TimeRange(start=1000.0, absolute=True), 'all_nans']
    assert len(nan_only) > 0 and np.isnan(nan_only.time).all() and nan_only.t0 is not None

    # - Neither bound: it is okay to return messages outside the extreme P1Times, so return everything.
    assert (nan_only.get_time_range().message_index == list(nan_only.message_index)).all()
    # - `stop` specified: no timestamped data is in range, so the range is empty.
    assert len(nan_only[TimeRange(end=1000.0, absolute=True)]) == 0
    assert len(nan_only[TimeRange(start=1.0, end=1000.0, absolute=True)]) == 0
    # - Only `start` specified: there is no timestamp at or after it, so the range is empty as well.
    assert len(nan_only[TimeRange(start=1.0, absolute=True)]) == 0

    # An empty index has nothing to bound. Note that __getitem__() short-circuits empty indices, so call
    # get_time_range() directly to exercise its own empty handling.
    assert len(FileIndex().get_time_range(time_range=TimeRange(start=1.0, end=2.0, absolute=True))) == 0
    assert len(FileIndex()[TimeRange(start=1.0, end=2.0, absolute=True)]) == 0

    # `start`/`stop` and a TimeRange are mutually exclusive.
    with pytest.raises(ValueError):
        index.get_time_range(start=1.0, time_range=TimeRange(start=1.0, absolute=True))


def test_time_slice_no_p1_time():
    def _lower_bound(time):
        return next(i for i, e in enumerate(RAW_DATA) if (e[0] is not None and e[0] >= time))

    raw_data = [e for e in RAW_DATA if e[0] is None]
    index = FileIndex(data=raw_data)
    assert index.t0 is None

    # If the log does not contain P1 time, slicing it by time is not supported.
    with pytest.raises(IndexError):
        index[1.0:]
    with pytest.raises(IndexError):
        index.get_time_range(start=1.0)
    with pytest.raises(IndexError):
        index[TimeRange(start=2.0, absolute=True)]
    with pytest.raises(IndexError):
        index[TimeRange(start=2.0, absolute=False)]

    # However, if you don't set start or stop, setting hint should still work.
    sliced_index = index.get_time_range(hint='include_nans')
    assert (sliced_index.message_index == [e[3] for e in raw_data]).all()


def test_empty_index():
    index = FileIndex()
    assert len(index) == 0
    assert len(index.time) == 0


def test_builder(tmpdir):
    builder = FileIndexBuilder()
    for entry in RAW_DATA:
        builder.append(p1_time=entry[0], message_type=entry[1], offset_bytes=entry[2])

    assert len(builder) == len(RAW_DATA)

    index = builder.to_index()
    assert len(index) == len(RAW_DATA)

    index_path = tmpdir.join('index.p1i')
    index.save(index_path, None)
    assert os.path.exists(index_path)
    assert os.path.getsize(index_path) > 0


@pytest.fixture
def data_path(tmpdir):
    prefix = tmpdir.join('my_data')

    # Construct an binary data file and a corresponding index.
    data_path = prefix + '.p1log'
    index_path = prefix + '.p1i'

    builder = FileIndexBuilder()
    encoder = FusionEngineEncoder()

    with open(data_path, 'wb') as f:
        for entry in RAW_DATA:
            builder.append(p1_time=entry[0], message_type=entry[1], offset_bytes=f.tell())

            cls = message_type_to_class[entry[1]]
            message = cls()
            if entry[0] is not None and hasattr(message, 'p1_time'):
                message.p1_time = entry[0]
            f.write(encoder.encode_message(message))

    builder.save(index_path, data_path)

    return data_path


def test_validate_good(data_path):
    index_path = FileIndex.get_path(data_path)
    index = FileIndex(index_path=index_path, data_path=data_path)
    assert len(index) == len(RAW_DATA)


def test_validate_index_empty(data_path):
    index_path = FileIndex.get_path(data_path)

    # Clear the index file.
    with open(index_path, 'wb'):
        pass

    with pytest.raises(ValueError):
        index = FileIndex(index_path=index_path, data_path=data_path)


def test_validate_data_file_empty(data_path):
    index_path = FileIndex.get_path(data_path)

    # Clear the data file.
    with open(data_path, 'wb'):
        pass

    with pytest.raises(ValueError):
        index = FileIndex(index_path=index_path, data_path=data_path)


def test_validate_index_too_small(data_path):
    index_path = FileIndex.get_path(data_path)

    # Strip one entry from the index file.
    file_size = os.path.getsize(index_path)
    with open(index_path, 'wb') as f:
        f.truncate(file_size - FileIndex._RAW_DTYPE.itemsize)

    with pytest.raises(ValueError):
        index = FileIndex(index_path=index_path, data_path=data_path)


def test_validate_data_too_small(data_path):
    index_path = FileIndex.get_path(data_path)

    # Strip one entry from the index file.
    file_size = os.path.getsize(data_path)
    with open(data_path, 'wb') as f:
        f.truncate(file_size - 10)

    with pytest.raises(ValueError):
        index = FileIndex(index_path=index_path, data_path=data_path)


def test_validate_data_too_large(data_path):
    index_path = FileIndex.get_path(data_path)

    # Strip one entry from the index file.
    file_size = os.path.getsize(data_path)
    with open(data_path, 'ab') as f:
        f.write(b'abcd')

    with pytest.raises(ValueError):
        index = FileIndex(index_path=index_path, data_path=data_path)
