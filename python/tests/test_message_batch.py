import numpy as np
import pytest

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder, MessageBatch, MixedLogReader
from fusion_engine_client.utils.time_range import TimeRange


def _make_wrapper(system_time_sec, data_type, data):
    message = InputDataWrapperMessage()
    message.system_time_ns = int(round(system_time_sec * 1e9))
    message.data_type = data_type
    message.data = data
    return message


def _make_pose(p1_time_sec):
    message = PoseMessage()
    message.p1_time = Timestamp(p1_time_sec)
    return message


@pytest.fixture
def data_path(tmpdir):
    """Write a log mixing pose output, wrapped input of two types and two source IDs, and non-FusionEngine bytes."""
    encoder = FusionEngineEncoder()
    entries = [
        (_make_pose(1.0), 0),
        (_make_wrapper(100.00, InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'first'), 0),
        b'not a message',
        (_make_wrapper(100.01, InputDataType.M_TYPE_RTCM3_POLARIS, b'other type'), 1),
        (_make_pose(2.0), 0),
        (_make_wrapper(100.50, InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'second record'), 0),
        (_make_pose(3.0), 1),
        (_make_wrapper(103.00, InputDataType.M_TYPE_EXTERNAL_UNFRAMED_GNSS, b'third'), 1),
    ]
    path = tmpdir.join('test_file.p1log')
    with open(path, 'wb') as f:
        for entry in entries:
            if isinstance(entry, bytes):
                f.write(entry)
            else:
                message, source_id = entry
                f.write(encoder.encode_message(message, source_identifier=source_id))
    return str(path)


def _read_iterator(path, **kwargs):
    reader = MixedLogReader(path, return_header=True, return_payload=False, return_bytes=True, return_offset=True,
                            **kwargs)
    return list(reader)


# Check that a batch contains the same messages, headers, and bytes as the iterator returns.
def test_matches_iterator(data_path):
    expected = _read_iterator(data_path)
    batch = MixedLogReader(data_path).read_batch()

    assert len(batch) == len(expected) == 7
    assert list(batch.offset) == [offset for _, _, offset in expected]
    assert list(batch.message_type) == [header.message_type for header, _, _ in expected]
    assert list(batch.sequence_number) == [header.sequence_number for header, _, _ in expected]
    assert list(batch.source_identifier) == [header.source_identifier for header, _, _ in expected]
    assert list(batch.size_bytes) == [len(data) for _, data, _ in expected]
    for i, (header, data, _) in enumerate(expected):
        assert bytes(batch.get_bytes(i)) == bytes(data)
        assert bytes(batch.get_payload(i)) == bytes(data[MessageHeader.calcsize():])


# Check that the batch honors the message type, source ID, time range, and max bytes filters like the iterator.
@pytest.mark.parametrize('kwargs', [
    {'message_types': [InputDataWrapperMessage]},
    {'message_types': [PoseMessage], 'invert_message_types': True},
    {'source_ids': [1]},
    {'time_range': TimeRange(start=1.5, end=2.5, absolute=True)},
])
def test_filters(data_path, kwargs):
    expected = _read_iterator(data_path, **kwargs)
    batch = MixedLogReader(data_path, **kwargs).read_batch()
    assert list(batch.offset) == [offset for _, _, offset in expected]


def test_max_bytes(data_path):
    # Let the reader index the whole file, then limit the read to the first 3 messages.
    expected = _read_iterator(data_path)
    _, data, offset = expected[2]
    max_bytes = offset + len(data)

    reader = MixedLogReader(data_path)
    reader.set_max_bytes(max_bytes)
    batch = reader.read_batch()
    assert list(batch.offset) == [offset for _, _, offset in expected[:3]]


# Check that read_batch() does not move the iterator.
def test_iterator_position_unchanged(data_path):
    reader = MixedLogReader(data_path)
    first = reader.read_next()
    reader.read_batch()
    second = reader.read_next()
    assert first[0].sequence_number + 1 == second[0].sequence_number


# Check that unpacking a batch with other message types, or a class without unpack_array(), is an error.
def test_unpack_array_errors(data_path):
    batch = MixedLogReader(data_path).read_batch()
    with pytest.raises(ValueError):
        batch.unpack_array(InputDataWrapperMessage)

    poses = batch[batch.message_type == MessageType.POSE]
    with pytest.raises(NotImplementedError):
        poses.unpack_array(PoseMessage)


# Check that a filter matching nothing produces an empty batch.
def test_empty(data_path):
    batch = MixedLogReader(data_path, message_types=[EventNotificationMessage]).read_batch()
    assert len(batch) == 0
    assert isinstance(batch, MessageBatch)
