import numpy as np
import pytest
import struct

from fusion_engine_client.messages import MessagePayload


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
