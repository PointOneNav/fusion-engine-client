from enum import EnumMeta, IntEnum as IntEnumBase

from aenum import extend_enum


class DynamicEnumMeta(EnumMeta):
    UNRECOGNIZED_PREFIX = '_U'

    def __call__(cls, value, *args, **kwargs):
        raise_on_unrecognized = kwargs.pop('raise_on_unrecognized', True)

        # If the user passed in a string, redirect the request: (Foo('bar') -> Foo.BAR). Normally, enums use [] for
        # strings and () for integers, but that can lead to confusion.
        if isinstance(value, str):
            name = value
            try:
                result = cls[name]
                if raise_on_unrecognized and result.name.startswith(cls.UNRECOGNIZED_PREFIX):
                    raise KeyError("Unrecognized enum name '%s'." % name)
                else:
                    return result
            except KeyError as e:
                if raise_on_unrecognized:
                    raise e from None
                else:
                    used_values = {int(v) for v in cls}
                    unused_value = min(min(used_values), 0) - 1
                    extend_enum(cls, name, unused_value)
                    return cls[name]
        else:
            try:
                result = super().__call__(value, *args, **kwargs)
                if raise_on_unrecognized and result.name.startswith(cls.UNRECOGNIZED_PREFIX):
                    raise ValueError("Unrecognized enum value %d." % int(result))
                else:
                    return result
            except ValueError as e:
                # If the user specified an integer value that is not recognized, add a new hidden enum value:
                #   6 --> MyEnum._UNRECOGNIZED_6 = 6
                if raise_on_unrecognized:
                    raise e from None
                else:
                    extend_enum(cls, f'{cls.UNRECOGNIZED_PREFIX}_{value}', value)
                    return super().__call__(value, *args, **kwargs)

    def __getitem__(cls, value):
        if isinstance(value, str):
            # Try to lookup by whatever value the user supplied: (Foo['BAR'] -> Foo.BAR)
            try:
                return super().__getitem__(value)
            # For convenience, also try converting to uppercase: (Foo['bar'] -> Foo.BAR)
            except KeyError:
                return super().__getitem__(value.upper())
        else:
            # See if `value` is actually an integer integer: (Foo['bar'] -> Foo.BAR)
            #
            # If it is not, the cls() call will raise an exception. We do this for convenience so that the user can use
            # the [] operator for strings and integers, instead of needing to use [] for strings and () for integers.
            #
            # If `value` is already an enum, it'll pass through: (Foo.BAR -> Foo.BAR)
            return cls(value)

    def __iter__(cls):
        return (enum for enum in super().__iter__() if not enum.name.startswith(cls.UNRECOGNIZED_PREFIX))

    def __len__(cls):
        return len(list(iter(cls)))


class IntEnum(IntEnumBase, metaclass=DynamicEnumMeta):
    def __str__(self):
        # The default str() for the built-in Enum class is ClassName.VALUE. For our purposes, we don't really need the
        # leading class name prefix, so we remove it. For example:
        #
        #   class Foo(IntEnum):
        #       BAR = 1
        #
        #   print(Foo.BAR)   # Prints "BAR", not "Foo.BAR"
        if self.name.startswith(IntEnum.UNRECOGNIZED_PREFIX):
            return "(Unrecognized)"
        else:
            return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__}.{str(self)}: {int(self)}>'

    def to_string(self, include_value=True):
        if include_value:
            return '%s (%d)' % (str(self), int(self))
        else:
            return str(self)
