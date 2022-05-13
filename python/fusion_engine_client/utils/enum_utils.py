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
        return super().__str__().replace(self.__class__.__name__ + '.', '')
