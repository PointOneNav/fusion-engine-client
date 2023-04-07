import math

from construct import Struct, Int16sl

from fusion_engine_client.utils.construct_utils import FixedPointAdapter


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
