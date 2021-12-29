from construct import Adapter, Enum


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

    def _decode(self, obj, context, path):
        val = self.cls()
        val.__dict__.update(obj)
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

    def __init__(self, enum_cls, *args):
        """!
        @brief Create an adapter for (de)serializing Enums.

        @param enum_cls The Enum to adapt.
        """
        super().__init__(*args)
        self.enum_cls = enum_cls

    def _decode(self, obj, context, path):
        return self.enum_cls(int(obj))

    def _encode(self, obj, context, path):
        return obj


def AutoEnum(construct_cls, enum_cls):
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
    return EnumAdapter(enum_cls, Enum(construct_cls, enum_cls))
