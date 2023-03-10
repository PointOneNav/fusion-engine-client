from enum import IntEnum as IntEnumBase


class IntEnum(IntEnumBase):
    def __str__(self):
        # The default str() for the built-in Enum class is ClassName.VALUE. For our purposes, we don't really need the
        # leading class name prefix, so we remove it. For example:
        #
        #   class Foo(IntEnum):
        #       BAR = 1
        #
        #   print(Foo.BAR)   # Prints "BAR", not "Foo.BAR"
        return self.name

    def to_string(self, include_value=False):
        if include_value:
            return '%s (%d)' % (str(self), int(self))
        else:
            return str(self)

    @classmethod
    def static_to_string(cls, value, include_value=False, raise_on_unrecognized=False):
        try:
            if isinstance(value, str):
                # Convert a string name to an enum instance (e.g., 'BAR' -> Foo.BAR).
                type = cls[value.upper()]
            else:
                # Convert an int to an enum instance. If `type` is already an enum, it'll pass through.
                type = cls(value)

            return cls(type).to_string(include_value=include_value)
        except (KeyError, ValueError) as e:
            if raise_on_unrecognized:
                raise e
            else:
                if include_value:
                    return '<Unrecognized> (%d)' % int(value)
                else:
                    return '<Unrecognized>'
