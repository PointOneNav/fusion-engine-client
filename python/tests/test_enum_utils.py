import pytest

from fusion_engine_client.utils.enum_utils import IntEnum, enum_bitmask


@pytest.fixture
def Enum():
    class TestEnum(IntEnum):
        A = 1
        B = 2
    return TestEnum


def test_str(Enum):
    assert str(Enum.A) == 'A'


def test_repr(Enum):
    assert repr(Enum.A) == '<TestEnum.A: 1>'


def test_to_string(Enum):
    assert Enum.A.to_string(include_value=True) == 'A (1)'
    assert Enum.A.to_string(include_value=False) == 'A'


def test_getitem(Enum):
    assert Enum['A'] == Enum.A
    # Not natively supported by Enum - we added these for convenience.
    assert Enum['a'] == Enum.A
    assert Enum[Enum.A] == Enum.A
    assert Enum[1] == Enum.A


def test_call(Enum):
    assert Enum(Enum.A) == Enum.A
    assert Enum(1) == Enum.A
    # Not natively supported by Enum - we added these for convenience.
    assert Enum('A') == Enum.A
    assert Enum('a') == Enum.A


def test_iter(Enum):
    assert list(Enum) == [Enum.A, Enum.B]
    assert len(Enum) == 2


def test_unrecognized(Enum):
    with pytest.raises(ValueError):
        Enum(8, raise_on_unrecognized=True)
        Enum(9, raise_on_unrecognized=True)

    value = Enum(10, raise_on_unrecognized=False)
    assert int(value) == 10
    assert str(value) == '(Unrecognized)'
    assert repr(value) == '<TestEnum.(Unrecognized): 10>'
    assert value == 10

    with pytest.raises(ValueError):
        Enum(10, raise_on_unrecognized=True)

    # Unrecognized values are not included in the iter() or len() output.
    assert list(Enum) == [Enum.A, Enum.B]
    assert len(Enum) == 2

    with pytest.raises(KeyError):
        assert Enum['Q']
        assert Enum('Q', raise_on_unrecognized=True)

    value = Enum('Q', raise_on_unrecognized=False)
    assert int(value) == -1
    assert Enum['Q'] == -1

    value = Enum('W', raise_on_unrecognized=False)
    assert int(value) == -2


def test_bitmask_decorator(Enum):
    @enum_bitmask(Enum)
    class EnumMask: pass
    expected_values = [Enum.A, Enum.B]
    expected_mask = (1 << int(Enum.A)) | (1 << int(Enum.B))
    assert EnumMask.to_bitmask(expected_values) == expected_mask
    assert EnumMask.to_values(expected_mask) == expected_values
    assert EnumMask.to_string(expected_mask) == 'A, B'


def test_bitmask_decorator_extended(Enum):
    @enum_bitmask(Enum)
    class EnumMask:
        ALL = 0xFF

    expected_values = [Enum.A, Enum.B]
    expected_mask = (1 << int(Enum.A)) | (1 << int(Enum.B))
    assert EnumMask.to_bitmask(expected_values) == expected_mask
    assert EnumMask.to_values(expected_mask) == expected_values
    assert EnumMask.to_string(expected_mask) == 'A, B'

    assert EnumMask.to_values(0xFF) == expected_values
    assert EnumMask[0xFF] == EnumMask.ALL


def test_bitmask_decorator_offset(Enum):
    @enum_bitmask(Enum, offset=1)
    class EnumMask: pass
    assert EnumMask.B == (1 << (Enum.B - 1))

    expected_values = [Enum.A, Enum.B]
    expected_mask = (1 << (int(Enum.A) - 1)) | (1 << (int(Enum.B) - 1))
    assert EnumMask.to_bitmask(expected_values) == expected_mask
    assert EnumMask.to_values(expected_mask) == expected_values
    assert EnumMask.to_string(expected_mask) == 'A, B'


def test_bitmask_decorator_predicate(Enum):
    @enum_bitmask(Enum, predicate=lambda x: str(x) == 'A')
    class EnumMask: pass
    assert hasattr(EnumMask, 'A')
    assert not hasattr(EnumMask, 'B')
