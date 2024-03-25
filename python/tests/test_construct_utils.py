import math

from construct import Struct, Float32l, Int16sl, Int16ul, Int16ub, Int8ul
import numpy as np

from fusion_engine_client.utils.construct_utils import FixedPointAdapter, NumpyAdapter


def test_fixed_point_int():
    # Integer value, no fractional part.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl)
    )

    data = {'value': 10}
    expected_bytes = b'\xA0\x00'

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    assert parsed == data

    data = {'value': 160}
    expected_bytes = b'\x00\x0A'

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    assert parsed == data


def test_fixed_point_no_round():
    # Fractional part, no round-off.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl)
    )

    data = {'value': 10.0625}
    expected_bytes = b'\xA1\x00'

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    assert parsed == data

    data = {'value': 160.0625}
    expected_bytes = b'\x01\x0A'

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    assert parsed == data


def test_fixed_point_round():
    # Fractional part with round-off.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl)
    )

    data = {'value': 10.07}
    expected_bytes = b'\xA1\x00'

    bytes = construct.build(data)
    assert bytes == expected_bytes

    expected_data = {'value': 10.0625}
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data


def test_fixed_point_invalid():
    # Invalid not enabled.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl, invalid=None)
    )

    expected_data = {'value': 32767 * (2 ** -4)}
    expected_bytes = b'\xFF\x7F'
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data

    expected_data = {'value': -32768 * (2 ** -4)}
    expected_bytes = b'\x00\x80'
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data

    # Invalid max positive.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl, invalid=0x7FFF)
    )

    expected_bytes = b'\xFF\x7F'
    parsed = construct.parse(expected_bytes)
    assert math.isnan(parsed.value)

    expected_data = {'value': -32768 * (2 ** -4)}
    expected_bytes = b'\x00\x80'
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data

    # Invalid max negative.
    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl, invalid=0x8000)
    )

    expected_data = {'value': 32767 * (2 ** -4)}
    expected_bytes = b'\xFF\x7F'
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data

    expected_bytes = b'\x00\x80'
    parsed = construct.parse(expected_bytes)
    assert math.isnan(parsed.value)

    construct = Struct(
        "value" / FixedPointAdapter(2 ** -4, Int16sl, invalid=-0x8000)
    )

    expected_data = {'value': 32767 * (2 ** -4)}
    expected_bytes = b'\xFF\x7F'
    parsed = construct.parse(expected_bytes)
    assert parsed == expected_data

    expected_bytes = b'\x00\x80'
    parsed = construct.parse(expected_bytes)
    assert math.isnan(parsed.value)


def test_numpy_float():
    construct = Struct(
        "float64" / NumpyAdapter(shape=(3,)),
        "float32" / NumpyAdapter(shape=(3,), construct_type=Float32l),
        "float64_2x3" / NumpyAdapter(shape=(2, 3)),
    )

    data = {
        'float64': [1.0, 1.1, 1.2],
        'float32': np.array([1.0, 1.1, 1.2]),
        'float64_2x3': np.array(([1.0, 1.1, 1.2], [2.0, 2.1, 2.2])),
    }

    bytes64_1_0 = b'\x00\x00\x00\x00\x00\x00\xF0\x3F'
    bytes64_1_1 = b'\x9A\x99\x99\x99\x99\x99\xF1\x3F'
    bytes64_1_2 = b'\x33\x33\x33\x33\x33\x33\xF3\x3F'
    bytes64_2_0 = b'\x00\x00\x00\x00\x00\x00\x00\x40'
    bytes64_2_1 = b'\xCD\xCC\xCC\xCC\xCC\xCC\x00\x40'
    bytes64_2_2 = b'\x9A\x99\x99\x99\x99\x99\x01\x40'
    bytes32_1_0 = b'\x00\x00\x80\x3F'
    bytes32_1_1 = b'\xCD\xCC\x8C\x3F'
    bytes32_1_2 = b'\x9A\x99\x99\x3F'
    expected_bytes = \
        (bytes64_1_0 + bytes64_1_1 + bytes64_1_2) + \
        (bytes32_1_0 + bytes32_1_1 + bytes32_1_2) + \
        (bytes64_1_0 + bytes64_1_1 + bytes64_1_2 +
         bytes64_2_0 + bytes64_2_1 + bytes64_2_2)

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    for key, expected_value in data.items():
        assert np.allclose(expected_value, parsed[key], equal_nan=True), \
            f"'{key}' values did not match:\n\nExpected:\n{repr(expected_value)}\n\nGot:\n{repr(parsed[key])}"


def test_numpy_int():
    construct = Struct(
        "int16" / NumpyAdapter(shape=(3,), construct_type=Int16sl),
        "uint16" / NumpyAdapter(shape=(3,), construct_type=Int16ul),
        "uint16be" / NumpyAdapter(shape=(3,), construct_type=Int16ub),
        "uint8" / NumpyAdapter(shape=(3,), construct_type=Int8ul),
        "uint16_2x3" / NumpyAdapter(shape=(2, 3), construct_type=Int16ul),
    )

    data = {
        'int16': [-1, 2, 3],
        'uint16': np.array([1, 2, 3], dtype=int),
        'uint16be': np.array([1, 2, 3], dtype=int),
        'uint8': [1, 2, 3],
        'uint16_2x3': np.array(([1, 2, 3], [4, 5, 6]), dtype=int),
    }

    bytes16_1 = b'\x01\x00'
    bytes16_2 = b'\x02\x00'
    bytes16_3 = b'\x03\x00'
    bytes16_4 = b'\x04\x00'
    bytes16_5 = b'\x05\x00'
    bytes16_6 = b'\x06\x00'
    bytes16_n1 = b'\xFF\xFF'
    bytes16be_1 = b'\x00\x01'
    bytes16be_2 = b'\x00\x02'
    bytes16be_3 = b'\x00\x03'
    bytes8_1 = b'\x01'
    bytes8_2 = b'\x02'
    bytes8_3 = b'\x03'
    expected_bytes = \
        (bytes16_n1 + bytes16_2 + bytes16_3) + \
        (bytes16_1 + bytes16_2 + bytes16_3) + \
        (bytes16be_1 + bytes16be_2 + bytes16be_3) + \
        (bytes8_1 + bytes8_2 + bytes8_3) + \
        (bytes16_1 + bytes16_2 + bytes16_3 +
         bytes16_4 + bytes16_5 + bytes16_6)

    bytes = construct.build(data)
    assert bytes == expected_bytes

    parsed = construct.parse(expected_bytes)
    for key, expected_value in data.items():
        assert np.allclose(expected_value, parsed[key], equal_nan=True), \
            f"'{key}' values did not match:\n\nExpected:\n{repr(expected_value)}\n\nGot:\n{repr(parsed[key])}"
