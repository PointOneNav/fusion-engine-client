from typing import NamedTuple, Optional

from construct import (Struct, Float32l, Int32ul, Int16ul, Int8ul, Padding, this, Flag, Bytes)

from ..utils.construct_utils import NamedTupleAdapter, AutoEnum
from .defs import *


class ConfigurationSource(IntEnum):
    ACTIVE = 0
    SAVED = 1


class ConfigType(IntEnum):
    INVALID = 0
    DEVICE_LEVER_ARM = 16
    DEVICE_COARSE_ORIENTATION = 17
    GNSS_LEVER_ARM = 18
    OUTPUT_LEVER_ARM = 19
    UART0_BAUD = 256
    UART1_BAUD = 257


class Direction(IntEnum):
    ## Aligned with vehicle +x axis.
    FORWARD = 0,
    ## Aligned with vehicle -x axis.
    BACKWARD = 1,
    ## Aligned with vehicle +y axis.
    LEFT = 2,
    ## Aligned with vehicle -y axis.
    RIGHT = 3,
    ## Aligned with vehicle +z axis.
    UP = 4,
    ## Aligned with vehicle -z axis.
    DOWN = 5,
    ## Error value.
    INVALID = 255


class _ConfigClassGenerator:
    """!
    @brief Internal class for generating `ConfigClass` children.

    These classes consist of 3 pieces:
    - The `ConfigType` associated with the class.
    - An accessor class. This is the class that's used to get/set the values for the config object.
    - A serialization class. This is the class that (de)serializes the data for the config object.

    To generate a ConfigClass:
    - Declared as a child of `NamedTuple`. The `NamedTuple` defines the fields.
    - Add a `create_config_class` decorator that takes the `ConfigType` and serialization Construct associated with the
      class.

    For example:
    ```{.py}
        _gen = _ConfigClassGenerator()

        class _FooData(NamedTuple):
            x: int

        _FooConstruct = Struct(
            "x" / Int32ul
        )

        @_gen.create_config_class(ConfigType.BAR, _FooConstruct)
        class Bar(_FooData): pass
    ```
    Would create a new `ConfigClass` Bar. Messages with ConfigType.BAR will attempt to (de)serialize to Bar. This
    serialization is defined by _FooConstruct. The user accessible fields are defined in _FooData.
    """
    class ConfigClass:
        """!
        @brief Abstract base class for accessing configuration types.
        """
        @classmethod
        def GetType(cls) -> ConfigType:
            raise ValueError('Accessing `GetType()` of base class')

    def __init__(self):
        # Gets populated with the mappings from ConfigType to constructs.
        self.CONFIG_MAP = {}

    def create_config_class(self, config_type, construct_class):
        """!
        @brief Decorator for generating ConfigClass children.

        @copydoc _ConfigClassGenerator
        """
        def inner(config_class):
            # Make the decorated class a child of ConfigClass. Add the GetType method.
            class InnerClass(config_class, self.ConfigClass):
                @classmethod
                def GetType(cls) -> ConfigType:
                    return config_type
            InnerClass.__name__ = config_class.__name__

            # Register the construct with the MessageType.
            self.CONFIG_MAP[config_type] = NamedTupleAdapter(InnerClass, construct_class)

            return InnerClass
        return inner

    class Point3F(NamedTuple):
        """!
        @brief 3D coordinate specifier, stored as 32-bit float values.
        """
        x: float = 0
        y: float = 0
        z: float = 0

    # Construct to serialize Point3F.
    Point3FConstruct = Struct(
        "x" / Float32l,
        "y" / Float32l,
        "z" / Float32l,
    )

    class IntegerVal(NamedTuple):
        """!
        @brief Integer value specifier.
        """
        value: int

    # Construct to serialize 32 bit IntegerVal types.
    UInt32Construct = Struct(
        "value" / Int32ul,
    )

    class CoarseOrientation(NamedTuple):
        """!
        @brief The orientation of a device with respect to the vehicle body axes.
        """
        ## The direction of the device +x axis relative to the vehicle body axes.
        x_direction: Direction = Direction.FORWARD
        ## The direction of the device +z axis relative to the vehicle body axes.
        z_direction: Direction = Direction.UP

    CoarseOrientationConstruct = Struct(
        "x_direction" / AutoEnum(Int8ul, Direction),
        "z_direction" / AutoEnum(Int8ul, Direction),
        Padding(2),
    )

    class Empty(NamedTuple):
        """!
        @brief Dummy specifier for empty config.
        """
        pass

    # Empty construct
    EmptyConstruct = Struct()


_conf_gen = _ConfigClassGenerator()


@_conf_gen.create_config_class(ConfigType.DEVICE_LEVER_ARM, _conf_gen.Point3FConstruct)
class DeviceLeverArmConfig(_conf_gen.Point3F):
    """!
    @brief The location of the device IMU with respect to the vehicle body frame (in meters).
    """
    pass

@_conf_gen.create_config_class(ConfigType.GNSS_LEVER_ARM, _conf_gen.Point3FConstruct)
class GnssLeverArmConfig(_conf_gen.Point3F):
    """!
    @brief The location of the GNSS antenna with respect to the vehicle body frame (in meters).
    """
    pass

@_conf_gen.create_config_class(ConfigType.OUTPUT_LEVER_ARM, _conf_gen.Point3FConstruct)
class OutputLeverArmConfig(_conf_gen.Point3F):
    """!
    @brief The location of the desired output location with respect to the vehicle body frame (in meters).
    """
    pass

@_conf_gen.create_config_class(ConfigType.UART0_BAUD, _conf_gen.UInt32Construct)
class Uart0BaudConfig(_conf_gen.IntegerVal):
    """!
    @brief The UART0 serial baud rate (in bits/second).
    """
    pass

@_conf_gen.create_config_class(ConfigType.UART1_BAUD, _conf_gen.UInt32Construct)
class Uart1BaudConfig(_conf_gen.IntegerVal):
    """!
    @brief The UART1 serial baud rate (in bits/second).
    """
    pass

@_conf_gen.create_config_class(ConfigType.DEVICE_COARSE_ORIENTATION, _conf_gen.CoarseOrientationConstruct)
class DeviceCourseOrientationConfig(_conf_gen.CoarseOrientation):
    """!
    @brief The orientation of a device with respect to the vehicle body axes.

    A device's orientation is defined by specifying how the +x and +z axes of its
    IMU are aligned with the vehicle body axes. For example, in a car:
    - `forward,up`: device +x = vehicle +x, device +z = vehicle +z (i.e.,
      IMU pointed towards the front of the vehicle).
    - `left,up`: device +x = vehicle +y, device +z = vehicle +z (i.e., IMU
      pointed towards the left side of the vehicle)
    - `up,backward`: device +x = vehicle +z, device +z = vehicle -x (i.e.,
      IMU pointed vertically upward, with the top of the IMU pointed towards the
      trunk)
    """
    pass

@_conf_gen.create_config_class(ConfigType.INVALID, _conf_gen.EmptyConstruct)
class InvalidConfig(_conf_gen.Empty):
    """!
    @brief Placeholder for empty invalid configuration messages.
    """
    pass


class SetConfigMessage(MessagePayload):
    """!
    @brief Set a user configuration parameter.
    """
    MESSAGE_TYPE = MessageType.SET_CONFIG
    MESSAGE_VERSION = 0

    SetConfigMessageConstruct = Struct(
        "config_type" / AutoEnum(Int16ul, ConfigType),
        Padding(2),
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Bytes(this.config_change_length_bytes),
    )

    def __init__(self, config_object: Optional[_conf_gen.ConfigClass] = None):
        self.config_object = config_object

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if not isinstance(self.config_object, _conf_gen.ConfigClass):
            raise TypeError(f'The config_object member ({str(self.config_object)}) must be set to a class decorated '
                             'with create_config_class.')
        config_type = self.config_object.GetType()
        construct_obj = _conf_gen.CONFIG_MAP[config_type]
        data = construct_obj.build(self.config_object)
        values = {
            'config_type': config_type,
            'config_change_data': data,
            'config_change_length_bytes': len(data)
        }
        packed_data = self.SetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SetConfigMessageConstruct.parse(buffer[offset:])
        self.config_object = _conf_gen.CONFIG_MAP[parsed.config_type].parse(parsed.config_change_data)
        return parsed._io.tell()

    def __str__(self):
        fields = ['config_object']
        string = f'Set Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class GetConfigMessage(MessagePayload):
    """!
    @brief Query the value of a user configuration parameter.
    """
    MESSAGE_TYPE = MessageType.GET_CONFIG
    MESSAGE_VERSION = 0

    GetConfigMessageConstruct = Struct(
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "request_source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(1),
    )

    def __init__(self):
        self.request_source = ConfigurationSource.ACTIVE
        self.config_type = ConfigType.INVALID

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.GetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.GetConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['request_source', 'config_type']
        string = f'Get Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.GetConfigMessageConstruct.sizeof()


class SaveAction(IntEnum):
    SAVE = 0
    REVERT_TO_SAVED = 1
    REVERT_TO_DEFAULT = 2


class SaveConfigMessage(MessagePayload):
    """!
    @brief Save or reload configuration settings.
    """
    MESSAGE_TYPE = MessageType.SAVE_CONFIG
    MESSAGE_VERSION = 0

    SaveConfigMessageConstruct = Struct(
        "action" / AutoEnum(Int8ul, SaveAction),
        Padding(3)
    )

    def __init__(self):
        self.action = SaveAction.SAVE

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.SaveConfigMessageConstruct.build({"action": self.action})
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SaveConfigMessageConstruct.parse(buffer[offset:])
        self.action = parsed.action
        return parsed._io.tell()

    def __str__(self):
        fields = ['action']
        string = f'Save Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.SaveConfigMessageConstruct.sizeof()


class ConfigDataMessage(MessagePayload):
    """!
    @brief Response to a @ref GetConfigMessage request.
    """
    MESSAGE_TYPE = MessageType.CONFIG_DATA
    MESSAGE_VERSION = 0

    ConfigDataMessageConstruct = Struct(
        "config_source" / AutoEnum(Int8ul, ConfigurationSource),
        "active_differs_from_saved" / Flag,
        "config_type" / AutoEnum(Int16ul, ConfigType),
        Padding(4),
        "config_length_bytes" / Int32ul,
        "config_data" / Bytes(this.config_length_bytes),
    )

    def __init__(self):
        self.config_source = ConfigurationSource.ACTIVE
        self.active_differs_from_saved = False
        self.config_object: _conf_gen.ConfigClass = None

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if not isinstance(self.config_object, _conf_gen.ConfigClass):
            raise TypeError(f'The config_object member ({str(self.config_object)}) must be set to a class decorated '
                             'with create_config_class.')
        values = dict(self.__dict__)
        config_type = self.config_object.GetType()
        construct_obj = _conf_gen.CONFIG_MAP[config_type]
        data = construct_obj.build(self.config_object)
        values.update({
            'config_type': config_type,
            'config_data': data,
            'config_length_bytes': len(data)
        })
        packed_data = self.ConfigDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ConfigDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        self.config_object = _conf_gen.CONFIG_MAP[parsed.config_type].parse(parsed.config_data)
        return parsed._io.tell()

    def __str__(self):
        fields = ['active_differs_from_saved', 'config_source', 'config_object']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
