import numpy as np
import pytest
import struct

import numpy as np

from fusion_engine_client.messages import MessagePayload, MessageType, Timestamp


def test_pack_primitives():
    s = struct.Struct('<fff')
    data = (1, 2, 3)
    expected_buffer = s.pack(*data)

    buffer = bytearray(s.size)
    assert MessagePayload.pack_values(s, buffer, 0, *data) == s.size
    assert buffer == expected_buffer


def test_pack_explicit_flatten():
    s = struct.Struct('<fff')
    data = np.array((1, 2, 3))
    expected_buffer = s.pack(*data)

    buffer = bytearray(s.size)
    assert MessagePayload.pack_values(s, buffer, 0, *data) == s.size
    assert buffer == expected_buffer


def test_pack_implicit_flatten():
    s = struct.Struct('<fff')
    data = np.array((1, 2, 3))
    expected_buffer = s.pack(*data)

    buffer = bytearray(s.size)
    assert MessagePayload.pack_values(s, buffer, 0, data) == s.size
    assert buffer == expected_buffer


def test_pack_nested():
    s = struct.Struct('<fff')
    data = (1, np.array((2, 3)))
    expected_buffer = s.pack(data[0], *data[1])

    buffer = bytearray(s.size)
    assert MessagePayload.pack_values(s, buffer, 0, *data) == s.size
    assert buffer == expected_buffer


def test_unpack():
    s = struct.Struct('<fff')
    data = np.array((1, 2, 3))
    buffer = s.pack(*data)

    unpacked_data = np.ndarray((3,))
    assert MessagePayload.unpack_values(s, buffer, 0, unpacked_data) == s.size
    assert (unpacked_data == data).all()


def test_message_type_to_string():
    expected = 'VERSION_INFO (13003)'
    assert MessageType.get_type_string(MessageType.VERSION_INFO) == expected
    assert MessageType.get_type_string(13003) == expected
    assert MessageType.get_type_string('VERSION_INFO') == expected
    assert MessageType.get_type_string('version_info') == expected

    assert MessageType.get_type_string(MessageType.VERSION_INFO, include_value=False) == 'VERSION_INFO'
    assert MessageType.get_type_string(MessageType.VERSION_INFO, include_value=False) == 'VERSION_INFO'

    assert MessageType.get_type_string(3) == 'UNKNOWN (3)'
    assert MessageType.get_type_string(3, include_value=False) == 'UNKNOWN'
    with pytest.raises(ValueError):
        MessageType.get_type_string(3, raise_on_unrecognized=True)
    with pytest.raises(KeyError):
        MessageType.get_type_string('foo', raise_on_unrecognized=True)

    value = int(MessageType.RESERVED) + 12
    expected = 'RESERVED (%d)' % value
    assert MessageType.get_type_string(value) == expected
    assert MessageType.get_type_string(value, raise_on_unrecognized=True) == expected


def test_find_message_types():
    # Case insensitive.
    assert MessagePayload.find_matching_message_types('posemessage') == {MessageType.POSE}
    assert MessagePayload.find_matching_message_types('PoseMessage') == {MessageType.POSE}

    # Exact matches, excluding "Message" or "Measurement" suffix, return a single type, even if multiple could fit
    # (e.g., 'pose' does not match PoseAux but 'pos' does).
    assert MessagePayload.find_matching_message_types('pose') == {MessageType.POSE}
    assert MessagePayload.find_matching_message_types('poseaux') == {MessageType.POSE_AUX}

    # Allow lists of patterns and comma-separated patterns.
    assert MessagePayload.find_matching_message_types(['pose']) == {MessageType.POSE}
    assert MessagePayload.find_matching_message_types(['pose', 'poseaux']) == {MessageType.POSE, MessageType.POSE_AUX}
    assert MessagePayload.find_matching_message_types(['pose,poseaux']) == {MessageType.POSE, MessageType.POSE_AUX}

    # Use wildcards to match multiple types.
    assert MessagePayload.find_matching_message_types(['pose*']) == {MessageType.POSE, MessageType.POSE_AUX}
    assert MessagePayload.find_matching_message_types(['*pose*']) == {MessageType.POSE, MessageType.POSE_AUX,
                                                                      MessageType.ROS_POSE}
    assert MessagePayload.find_matching_message_types(['pose*', 'gnssi*']) == {MessageType.POSE, MessageType.POSE_AUX,
                                                                               MessageType.GNSS_INFO}
    assert MessagePayload.find_matching_message_types(['pose*,gnssi*']) == {MessageType.POSE, MessageType.POSE_AUX,
                                                                               MessageType.GNSS_INFO}

    # Return classes instead of MessageType enums.
    assert MessagePayload.find_matching_message_types('pose', return_class=True) == \
           {MessagePayload.message_type_to_class[MessageType.POSE]}

    # No matches return empty set.
    assert MessagePayload.find_matching_message_types('doesntexist') == set()

    # Multiple matches without a * raise an exception.
    with pytest.raises(ValueError):
        MessagePayload.find_matching_message_types(['pos'])


class DummyMessage(MessagePayload):
    MESSAGE_TYPE = MessageType.INVALID
    MESSAGE_VERSION = 0

    def __init__(self, p1_time=None, lla_deg=None, scalar=None, custom=None):
        self.p1_time = Timestamp() if p1_time is None else p1_time
        self.lla_deg = np.full((3,), np.nan) if lla_deg is None else lla_deg
        self.scalar = 0 if scalar is None else scalar
        self.custom = 0 if custom is None else custom

    @classmethod
    def to_numpy_custom(cls, messages):
        return cls._message_to_numpy(messages,
                                     value_to_array={'custom': lambda values: np.array([v * 1.01 for v in values])})


def test_message_to_numpy():
    messages = [
        DummyMessage(p1_time=Timestamp(3), lla_deg=np.array((1, 2, 3)), scalar=6, custom=10),
        DummyMessage(p1_time=Timestamp(), scalar=np.nan, custom=11),
        DummyMessage(p1_time=Timestamp(5), scalar=np.nan, custom=12),
    ]

    expected_result = {
        'p1_time': np.array((3, np.nan, 5)),
        'lla_deg': np.array(((1, 2, 3), (np.nan, np.nan, np.nan), (np.nan, np.nan, np.nan))).T,
        'scalar': np.array((6, np.nan, np.nan)),
        'custom': np.array((10, 11, 12)),
    }

    # Test default to_numpy() implementation, inherited from MessagePayload.
    result = DummyMessage.to_numpy(messages)
    assert result.keys() == expected_result.keys()
    for key, expected_value in expected_result.items():
        assert np.allclose(expected_value, result[key], equal_nan=True), \
            f"'{key}' values did not match:\n\nExpected:\n{repr(expected_value)}\n\nGot:\n{repr(result[key])}"

    # Test a custom to_numpy() implementation.
    expected_result['custom'] =np.array((10.10, 11.11, 12.12))
    result = DummyMessage.to_numpy_custom(messages)
    assert result.keys() == expected_result.keys()
    for key, expected_value in expected_result.items():
        assert np.allclose(expected_value, result[key], equal_nan=True), \
            f"'{key}' values did not match:\n\nExpected:\n{repr(expected_value)}\n\nGot:\n{repr(result[key])}"
