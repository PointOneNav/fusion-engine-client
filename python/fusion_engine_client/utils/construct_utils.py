import math
import re
from typing import Optional

from construct import Adapter, Enum, Struct

from .enum_utils import IntEnum


class FixedPointAdapter(Adapter):
    def __init__(self, scale, *args, invalid=None):
        super().__init__(*args)
        self.scale = scale
        self.invalid = invalid

        is_signed = self.subcon.fmtstr.islower()
        if self.invalid is not None and is_signed:
            max_negative_mag = 2 ** (self.subcon.sizeof() * 8 - 1)
            if self.invalid == max_negative_mag:
                self.invalid = -self.invalid

    def _decode(self, obj, context, path):
        if obj == self.invalid:
            return math.nan
        else:
            return float(obj * self.scale)

    def _encode(self, obj, context, path):
        if math.isnan(obj) and self.invalid is not None:
            return self.invalid
        else:
            return int(round(obj / self.scale))


class NamedTupleAdapter(Adapter):
    """!
    @brief Adapter for automatically converting between construct streams and
           NamedTuples with corresponding fields.

    Usage Example:
    ```{.py}
        class VersionTuple(NamedTuple):
            major: int
            minor: int

        VersionRawConstruct = Struct(
            "major" / Int8ul,
            "minor" / Int16ul,
        )

        VersionConstruct = NamedTupleAdapter(VersionTuple, VersionRawConstruct)
        UserConfigConstruct = Struct(
            "version" / VersionConstruct,
            "thing2" / Int32ul,
        )
        UserConfigConstruct.build({'version': VersionTuple(2, 3), 'thing2': 4})
    ```
    """

    def __init__(self, tuple_cls, *args):
        """!
        @brief Create an adapter for (de)serializing NamedTuples.

        @param tuple_cls The NamedTuple to adapt.
        """
        super().__init__(*args)
        self.tuple_cls = tuple_cls

    def make_default(self):
        return self.tuple_cls()

    def _decode(self, obj, context, path):
        # skip _io member
        return self.tuple_cls(*list(obj.values())[1:])

    def _encode(self, obj, context, path):
        return obj._asdict()


class ClassAdapter(Adapter):
    """!
    @brief Adapter for automatically converting between construct streams and
           a class with corresponding fields.

    Usage Example:
    ```{.py}
        class VersionClass:
            def __init__(self, major=0, minor=0):
                self.major = major
                self.minor = minor

        VersionRawConstruct = Struct(
            "major" / Int8ul,
            "minor" / Int16ul,
        )

        VersionConstruct = ClassAdapter(VersionClass, VersionRawConstruct)
        UserConfigConstruct = Struct(
            "version" / VersionConstruct,
            "thing2" / Int32ul,
        )
        UserConfigConstruct.build({'version': VersionClass(2, 3), 'thing2': 4})
    ```
    """

    def __init__(self, cls, *args):
        """!
        @brief Create an adapter for (de)serializing a class.

        @param cls The class to adapt.
        """
        super().__init__(*args)
        self.cls = cls

    def make_default(self):
        return self.cls()

    def _decode(self, obj, context, path):
        val = self.cls()
        val.__dict__.update(obj)
        del val.__dict__['_io']
        return val

    def _encode(self, obj, context, path):
        return obj.__dict__


class EnumAdapter(Adapter):
    """!
    @brief Adapter for automatically converting between construct Enum and
           python Enums.

    Usage Example:
    ```{.py}
        class ConfigType(IntEnum):
            FOO = 0
            BAR = 1

        ConfigConstruct = EnumAdapter(ConfigType, Enum(Int32ul, ConfigType))

        UserConfigConstruct = Struct(
            "config_type" / ConfigConstruct,
        )

        data = UserConfigConstruct.build({'config_type': ConfigType.ACTIVE})
        assert ConfigType.ACTIVE == UserConfigConstruct.parse(data).config_type
    ```
    """

    def __init__(self, enum_cls, *args, **kwargs):
        """!
        @brief Create an adapter for (de)serializing Enums.

        @param enum_cls The Enum to adapt.
        """
        super().__init__(*args)
        self.enum_cls = enum_cls
        self.raise_on_unrecognized = kwargs.get('raise_on_unrecognized', True)

    def make_default(self):
        return self.enum_cls('UNKNOWN', raise_on_unrecognized=self.raise_on_unrecognized)

    def _decode(self, obj, context, path):
        return self.enum_cls(int(obj), raise_on_unrecognized=self.raise_on_unrecognized)

    def _encode(self, obj, context, path):
        return obj


def AutoEnum(construct_cls, enum_cls, raise_on_unrecognized: bool = False):
    """!
    @brief Wrapper for @ref EnumAdapter to make its arguments simpler.

    Usage Example:
    ```{.py}
        class ConfigType(IntEnum):
            FOO = 0
            BAR = 1

        UserConfigConstruct = Struct(
            "config_type" / AutoEnum(Int32ul, ConfigType),
        )

        data = UserConfigConstruct.build({'config_type': ConfigType.ACTIVE})
        assert ConfigType.ACTIVE == UserConfigConstruct.parse(data).config_type
    ```
    """
    return EnumAdapter(enum_cls, Enum(construct_cls, enum_cls), raise_on_unrecognized=raise_on_unrecognized)


def construct_message_to_string(message: object, construct: Optional[Struct] = None, title: Optional[str] = None,
                                fields: Optional[list] = None, value_to_string: Optional[dict] = None) -> str:
    """!
    @brief Generate a string representation of a message class serialized using the `construct` library.

    By default, all members of the `message` object will be displayed using their default `str()` representation. If
    desired, you may specify an alternate function in `value_to_string` to use to convert the value to a string
    representation. For example, to display integer field `bar` in hex instead of decimal:

    ```py
    >>> construct_message_to_string(my_message, value_to_string={'bar': lambda x: '0x%X' % x})
    MyMessage
      foo: 14
      bar: 0xE
    ```

    Any enum values serialized using an @ref EnumAdapter will automatically use their enum class's `to_string()`
    method (if defined) to generate a string representing the value. For instance, for a field `data` using the
    `ConfigType` @ref IntEnum value shown in the @ref AutoEnum() documentation, the resulting string would be either
    `data: BAR (1)` for recognized values, or `data: <Unrecognized> (3)` for unrecognized values. Enum fields listed in
    `value_to_string` will use the user-specified function instead.

    @param message The message instance.
    @param construct The `construct.Struct` instance used to serialize `message`. If omitted, the class is assumed to
           have a `Struct` member named `Construct`. If that member does not exist, `to_string()` support for enum
           values will be disabled and the default `repr()` result will be returned.
    @param title A title to be displayed for the message. If omitted, defaults to the message class name.
    @param fields An optional list of member variable names to be displayed. If omitted, all class members will be
           shown. This can also be used to define the sorting order used to display members. By default, members will be
           sorted alphabetically.
    @param value_to_string A dictionary listing alternate string conversion functions to be called for specific fields.

    @return A string describing the `message` instance.
    """
    if construct is None:
        construct = getattr(message.__class__, 'Construct', None)

    if title is None:
        title = message.__class__.__name__

    if fields is None:
        fields = sorted(message.__dict__.keys())

    if value_to_string is None:
        value_to_string = {}

    def _get_enum_class(subcon) -> Optional[IntEnum]:
        if subcon is None:
            return None
        if isinstance(subcon, EnumAdapter):
            return subcon.enum_cls
        else:
            return _get_enum_class(getattr(subcon, 'subcon', None))

    def _generic_value_to_string(value):
        result = str(value).replace('Container:', '')
        result = re.sub(r'ListContainer\((.+)\)', r'\1', result)
        result = re.sub(r'<TransportType\.(.+): [0-9]+>', r'\1', result)
        return result

    if construct is not None:
        for subcon in construct.subcons:
            if subcon.name is not None and subcon.name not in value_to_string:
                enum_cls = _get_enum_class(subcon)
                if enum_cls is not None:
                    to_string = getattr(enum_cls, 'to_string', repr)
                    value_to_string[subcon.name] = to_string

    string = f'{title}\n'
    newline = '\n'
    for field in fields:
        value = getattr(message, field)
        to_string_func = value_to_string.get(field, _generic_value_to_string)
        string += f'  {field}: {to_string_func(value).replace(newline, newline + "    ")}\n'
    return string.rstrip()
