from construct import Adapter


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
