import numpy as np
import pytest
import struct

from fusion_engine_client.messages import MessagePayload, MessageType


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
