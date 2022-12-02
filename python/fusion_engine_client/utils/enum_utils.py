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
