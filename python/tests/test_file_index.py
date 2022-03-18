import os

import numpy as np
import pytest

from fusion_engine_client.analysis.file_index import FileIndex, FileIndexBuilder
from fusion_engine_client.messages import MessageType, Timestamp, message_type_to_class
from fusion_engine_client.parsers import FusionEngineEncoder

RAW_DATA = [
    (None, MessageType.VERSION_INFO, 0),
    (Timestamp(1.0), MessageType.POSE, 10),
    (Timestamp(2.0), MessageType.POSE, 20),
    (Timestamp(2.0), MessageType.GNSS_INFO, 30),
    (None, MessageType.VERSION_INFO, 40),
    (Timestamp(3.0), MessageType.POSE, 50),
    (Timestamp(4.0), MessageType.POSE, 60),
]


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

    raw = [e for e in RAW_DATA if e[1] == MessageType.VERSION_INFO]
    idx = index.type == MessageType.VERSION_INFO
    assert _test_time(index.time[idx], raw)
    assert (index.offset[idx] == [e[2] for e in raw]).all()


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

    pose_index = index[(MessageType.POSE, MessageType.GNSS_INFO)]
    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE or e[1] == MessageType.GNSS_INFO]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()


def test_index_slice():
    index = FileIndex(data=RAW_DATA)

    # Access a single element.
    sliced_index = index[3]
    raw = [RAW_DATA[3]]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access to the end.
    sliced_index = index[3:]
    raw = RAW_DATA[3:]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access from the beginning.
    sliced_index = index[:3]
    raw = RAW_DATA[:3]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access a range.
    sliced_index = index[2:4]
    raw = RAW_DATA[2:4]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access individual indices.
    sliced_index = index[(2, 3, 5)]
    raw = [RAW_DATA[i] for i in (2, 3, 5)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()


def test_time_slice():
    def _lower_bound(time):
        return next(i for i, e in enumerate(RAW_DATA) if (e[0] is not None and e[0] >= time))

    index = FileIndex(data=RAW_DATA)

    # Access to the end.
    sliced_index = index[2.0:]
    raw = RAW_DATA[_lower_bound(2.0):]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access from the beginning.
    sliced_index = index[:3.0]
    raw = RAW_DATA[:_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access a range.
    sliced_index = index[2.0:3.0]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()

    # Access by Timestamp.
    sliced_index = index[Timestamp(2.0):Timestamp(3.0)]
    raw = RAW_DATA[_lower_bound(2.0):_lower_bound(3.0)]
    assert _test_time(sliced_index.time, raw)
    assert (sliced_index.offset == [e[2] for e in raw]).all()


def test_empty_index():
    index = FileIndex()
    assert len(index) == 0
    assert index.time is None


def test_builder(tmpdir):
    builder = FileIndexBuilder()
    for entry in RAW_DATA:
        builder.append(p1_time=entry[0], message_type=entry[1], offset_bytes=entry[2])

    assert len(builder) == len(RAW_DATA)

    index = builder.to_index()
    assert len(index) == len(RAW_DATA)

    index_path = tmpdir.join('index.p1i')
    index.save(index_path)
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

    builder.save(index_path)

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
