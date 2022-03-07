import os

import numpy as np

from fusion_engine_client.analysis.file_index import FileIndex, FileIndexBuilder
from fusion_engine_client.messages import MessageType, Timestamp

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
    index = FileIndex(RAW_DATA)
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


def test_type_slice():
    index = FileIndex(RAW_DATA)

    pose_index = index[MessageType.POSE]
    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()

    pose_index = index[(MessageType.POSE, MessageType.GNSS_INFO)]
    raw = [e for e in RAW_DATA if e[1] == MessageType.POSE or e[1] == MessageType.GNSS_INFO]
    assert len(pose_index) == len(raw)
    assert (pose_index.offset == [e[2] for e in raw]).all()


def test_index_slice():
    index = FileIndex(RAW_DATA)

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
