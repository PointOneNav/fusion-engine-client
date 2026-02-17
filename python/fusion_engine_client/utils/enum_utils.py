from enum import EnumMeta, IntEnum as IntEnumBase
import functools
import inspect
import re
from typing import List, Set, Union

from aenum import extend_enum


class DynamicEnumMeta(EnumMeta):
    UNRECOGNIZED_PREFIX = '_U'

    def __new__(cls, name, bases, dict):
        # Add is_recognized() to the definition for the class using this metaclass.
        def is_unrecognized(self):
            return self.name.startswith(cls.UNRECOGNIZED_PREFIX)
        dict['is_unrecognized'] = is_unrecognized
        enum_class = super().__new__(cls, name, bases, dict)
        return enum_class

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

    def from_string(self, name, case_insensitive=False):
        if case_insensitive:
            # Convert the memebr lookup to lowercase to perform a case-insensitive search: (Foo['bar'] -> Foo.bar)
            member_map = {k.lower(): v for k, v in self._member_map_.items()}
            return member_map[name.lower()]
        else:
            # Try to lookup by whatever value the user supplied: (Foo['BAR'] -> Foo.BAR)
            try:
                return super().__getitem__(name)
            # For convenience, also try converting to uppercase: (Foo['bar'] -> Foo.BAR)
            except KeyError:
                return super().__getitem__(name.upper())

    def __getitem__(cls, value):
        if isinstance(value, str):
            return cls.from_string(value, case_insensitive=False)
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
        if self.is_unrecognized():
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

    @classmethod
    def find_matching_values(cls, pattern: Union[int, str, List[int], List[str]], raise_on_unrecognized: bool = False,
                             prefix: str = None, print_func=None) -> Set['IntEnum']:
        """!
        @brief Find one or more enum values that match the specified pattern(s).

        Examples:
        ```py
        class MyType(IntEnum):
            THING_A = 1
            THING_B = 2

        MyType.find_matching_values('thing_abc')  # {MyType.THING_ABC}
        MyType.find_matching_values('THING_ABC')  # {MyType.THING_ABC}
        MyType.find_matching_values('THING_A')  # {MyType.THING_ABC}
        MyType.find_matching_values('thing')  # ValueError - multiple possible matches
        MyType.find_matching_values('thing*')  # {MyType.THING_DEF, MyType.THING_DEF}
        MyType.find_matching_values('thing_abc,thing_def')  # {MyType.THING_ABC, MyType.THING_DEF}
        MyType.find_matching_values(['thing_abc', 'thing_def'])  # {MyType.THING_ABC, MyType.THING_DEF}
        MyType.find_matching_values(1)  # {MyType.THING_ABC}
        MyType.find_matching_values([1, 2])  # {MyType.THING_ABC, MyType.THING_DEF}
        MyType.find_matching_values(3)  # {MyType._U_3}
        ```

        @param pattern A `list` or a comma-separated string containing one or more search patterns. Patterns may match
               part or all of an enum name. Patterns may include wildcards (`*`) to match multiple enums. If no
               wildcards are specified and multiple enums match, a single result will be returned if there is an exact
               match (e.g., `thing_a` will match to `MyType.THING_ABC`, not `MyType.THING_DEF`). All matches are
               case-insensitive.
        @param raise_on_unrecognized If `True`, raise an exception for any unrecognized integer values. Unrecognized
               values will automatically create new enum entries by default.
        @param prefix If specified, prepend the prefix to all string values if they do not already start with it.

        @return A set containing the matching enum values.
        """
        # Convert to a list of strings for consistency.
        if isinstance(pattern, int):
            patterns = [f'{pattern}']
        elif isinstance(pattern, str):
            patterns = [pattern]
        else:
            if len(pattern) > 0 and isinstance(pattern[0], int):
                patterns = [f'{p}' for p in pattern]
            else:
                patterns = pattern

        # Split and flatten comma-separated lists of names/patterns:
        #   ['VersionInfoMessage', 'PoseMessage,GNSS*'] ->
        #   ['VersionInfoMessage', 'PoseMessage', 'GNSS*']
        requested_types = [p.strip() for entry in patterns for p in entry.split(',')]

        # Now find matches to each pattern.
        result = set()
        for pattern in requested_types:
            # Check if pattern is the message integer value.
            try:
                if pattern.lower().startswith('0x'):
                    int_val = int(pattern, base=16)
                else:
                    int_val = int(pattern)
                enum_val = cls(int_val, raise_on_unrecognized=raise_on_unrecognized)
                result.add(enum_val)
                if str(enum_val) == '(Unrecognized)' and print_func:
                    print_func(f"{pattern} is an unknown {cls.__name__} value.")
            except:
                if prefix is not None and not pattern.startswith(prefix):
                    pattern = f'{prefix}{pattern}'

                allow_multiple = '*' in pattern
                re_pattern = pattern.replace('*', '.*')
                # if pattern[0] != '^':
                #     re_pattern = r'.*' + re_pattern
                # if pattern[-1] != '$':
                #     re_pattern += '.*'

                # Check for matches.
                matched_types = [v for k, v in cls._member_map_.items()
                                if re.match(re_pattern, k, flags=re.IGNORECASE)]
                if len(matched_types) == 0 and print_func:
                    print_func("No message types matching pattern '%s'." % pattern)
                    continue

                # If there are too many matches, fail.
                if len(matched_types) > 1 and not allow_multiple:
                    raise ValueError("Pattern '%s' matches multiple message types:%s\n\nAdd a wildcard (%s*) to display "
                                     "all matching types." %
                                     (pattern, ''.join(['\n  %s' % c for c in cls._member_map_.keys()]), pattern))
                # Otherwise, update the set of message types.
                else:
                    result.update(matched_types)

        return result


def enum_bitmask(enum_type, offset=0, define_bits=True, predicate=None):
    """!
    @brief Create a bitmask class definition corresponding with an existing class derived from `IntEnum`.

    ```py
    class MyEnum(IntEnum):
        A = 1
        B = 2

    @enum_bitmask(MyEnum)
    class MyMask: pass
    ```

    The `MyMask` definition above is the equivalent of:

    ```py
    class MyMask(IntEnum):
        A = (1 << 1)
        B = (1 << 2)

        @classmethod
        def to_bitmask(cls, values): ...

        @classmethod
        def to_values(cls, mask): ...

        @classmethod
        def to_string(cls, mask): ...
    ```

    @param enum_type The enum to which the mask class corresponds.
    @param offset An offset to apply to all enum values such that `mask = (1 << (enum - offset))`
    @param define_bits If `True`, define mask bit member variables for each value defined in the enum (e.g., `A` and `B`
           above). Otherwise, do not define any member variables for the class, only attach the helper methods.
    @param predicate An optional function to be called for each candidate enum value. Only values for which the
           predicate returns `True` will be included.
    """
    if predicate is None:
        predicate = lambda x: True

    def _wrapper(base_cls):
        # Define a wrapper class that inherits from both the base class and IntEnum, and adds the additional bitmask
        # helper functions.
        @functools.wraps(base_cls, updated=())
        class WrappedCls(base_cls, IntEnum):
            @classmethod
            def to_bitmask(cls, values: List[Union[enum_type, str]]) -> int:
                """!
                @brief Convert a list of enum values or string names to a bitmask.

                @param values A list of one or more enum values or string names.

                @return The corresponding integer bitmask.
                """
                mask = 0
                for value in values:
                    if isinstance(value, str):
                        mask |= getattr(cls, value.upper())
                    else:
                        mask |= (1 << (int(value) - cls._enum_offset))
                return mask

            @classmethod
            def to_values(cls, mask: int) -> List[enum_type]:
                """!
                @brief Decode a bitmask into a list of enum values.

                @param mask The bitmask to be decoded.

                @return A list of enum values for each bit set in the mask.
                """
                values = []
                for value in cls._enum_values:
                    if (mask & (1 << (int(value) - cls._enum_offset))) != 0:
                        values.append(value)
                return values

            @classmethod
            def to_string(cls, mask: int) -> str:
                """!
                @brief Decode a bitmask into a human-readable string.

                @param mask The bitmask to be decoded.

                @return A comma-separated string listing the names of the enum value for each bit set in the mask.
                """
                values = cls.to_values(mask)
                return ', '.join(str(s) for s in values)

        # Note that these are used in the functions above, but must be defined here, _not_ under the `class WrappedCls:`
        # definition above, so IntEnum doesn't try to interpret them.
        WrappedCls._enum_offset = offset
        WrappedCls._enum_values = [v for v in enum_type if predicate(v)]

        # List elements returned by getmembers() for _all_ IntEnum so we can skip them in the loops below when looking
        # for enum values to be added.
        class Dummy(IntEnum):
            pass
        internals = [e[0] for e in inspect.getmembers(Dummy)]

        def _is_enum_entry(entry):
            return entry[0] not in internals and not entry[0].startswith('_')

        # If the user defined any additional enum values in the template base class, remove them from the base and add
        # them back using extend_enum() so they are usable enum values. For example:
        #   @enum_bitmask(MyEnum)
        #   class MyMask:
        #       ALL = 0xFF
        for entry in inspect.getmembers(base_cls):
            if _is_enum_entry(entry):
                delattr(base_cls, entry[0])
                extend_enum(WrappedCls, entry[0], int(entry[1]))

        # Now define additional enum values for each bit:
        #   A = (1 << MyEnum.A)
        if define_bits:
            for entry in inspect.getmembers(enum_type):
                if _is_enum_entry(entry) and predicate(entry[1]):
                    extend_enum(WrappedCls, entry[0], (1 << (int(entry[1]) - WrappedCls._enum_offset)))

        return WrappedCls
    return _wrapper
