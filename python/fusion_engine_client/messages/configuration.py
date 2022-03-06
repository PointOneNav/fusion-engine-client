import re
from typing import NamedTuple, Optional, List

from construct import (Struct, Float32l, Int32ul, Int16ul, Int8ul, Padding, this, Flag, Bytes, Array, Adapter)

from ..utils.construct_utils import NamedTupleAdapter, AutoEnum
from .defs import *


################################################################################
# Device Configuration Support
################################################################################


class ConfigurationSource(IntEnum):
    ACTIVE = 0
    SAVED = 1

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


class ConfigType(IntEnum):
    INVALID = 0
    DEVICE_LEVER_ARM = 16
    DEVICE_COARSE_ORIENTATION = 17
    GNSS_LEVER_ARM = 18
    OUTPUT_LEVER_ARM = 19
    UART0_BAUD = 256
    UART1_BAUD = 257

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


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

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


class TransportType(IntEnum):
    INVALID = 0,
    SERIAL = 1,
    FILE = 2,
    TCP_CLIENT = 3,
    TCP_SERVER = 4,
    UDP_CLIENT = 5,
    UDP_SERVER = 6,
    ## This is used for requesting the configuration for all interfaces.
    ALL = 255,

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


class UpdateAction(IntEnum):
    REPLACE = 0

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


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

    The `config_object` should be set to a `ConfigClass` instance for the configuration parameter to update.

    Usage examples:
    ```{.py}
    # A message for setting the device UART1 baud rate to 9600.
    set_config = SetConfigMessage(Uart1BaudConfig(9600))

    # A message for setting the device lever arm to [1.1, 0, 1.2].
    set_config = SetConfigMessage(DeviceLeverArmConfig(1.1, 0, 1.2))

    # A message for setting the device coarse orientation to the default values.
    set_config = SetConfigMessage(DeviceCourseOrientationConfig())
    ```
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

    def __init__(self,
                 config_type: ConfigType = ConfigType.INVALID,
                 request_source: ConfigurationSource = ConfigurationSource.ACTIVE):
        self.request_source = config_type
        self.config_type = request_source

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

    def __str__(self):
        return super().__str__().replace(self.__class__.__name__ + '.', '')


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

    def __init__(self, action: SaveAction = SaveAction.SAVE):
        self.action = action

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


class ConfigResponseMessage(MessagePayload):
    """!
    @brief Response to a @ref GetConfigMessage request.
    """
    MESSAGE_TYPE = MessageType.CONFIG_RESPONSE
    MESSAGE_VERSION = 0

    ConfigResponseMessageConstruct = Struct(
        "config_source" / AutoEnum(Int8ul, ConfigurationSource),
        "active_differs_from_saved" / Flag,
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "response" / AutoEnum(Int8ul, Response),
        Padding(3),
        "config_length_bytes" / Int32ul,
        "config_data" / Bytes(this.config_length_bytes),
    )

    def __init__(self):
        self.config_source = ConfigurationSource.ACTIVE
        self.response = Response.OK
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
        packed_data = self.ConfigResponseMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ConfigResponseMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        self.config_object = _conf_gen.CONFIG_MAP[parsed.config_type].parse(parsed.config_data)
        return parsed._io.tell()

    def __str__(self):
        fields = ['active_differs_from_saved', 'config_source', 'response', 'config_object']
        string = f'Config Data\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


################################################################################
# Input/Output Stream Control
################################################################################


class InterfaceID(NamedTuple):
    type: TransportType = TransportType.INVALID
    index: int = 0


class OutputInterfaceConfig(NamedTuple):
    output_interface: InterfaceID = InterfaceID()
    stream_indices: List[int] = []


_InterfaceIDConstructRaw = Struct(
    "type" / AutoEnum(Int8ul, TransportType),
    "index" / Int8ul,
    Padding(2)
)
_InterfaceIDConstruct = NamedTupleAdapter(InterfaceID, _InterfaceIDConstructRaw)


class _OutputInterfaceConfigConstruct(Adapter):
    """!
    Adapter to handle setting `num_streams` implicitly.
    """

    def __init__(self):
        super().__init__(Struct(
            "output_interface" / _InterfaceIDConstruct,
            "num_streams" / Int8ul,
            Padding(3),
            "stream_indices" / Array(this.num_streams, Int8ul),
        ))

    def _decode(self, obj, context, path):
        return OutputInterfaceConfig(obj.output_interface, obj.stream_indices)

    def _encode(self, obj, context, path):
        return {
            "output_interface": obj.output_interface,
            "num_streams": len(obj.stream_indices),
            "stream_indices": obj.stream_indices
        }


class SetOutputInterfaceConfigMessage(MessagePayload):
    """!
    @brief Configure the set of output streams enabled for a given output interface.

    An example usage:
    ```{.py}
    # Set the device Serial 0 to output stream 1 and 2 messages.
    set_out_streams = SetOutputInterfaceConfigMessage()
    set_out_streams.output_interface_config =
        OutputInterfaceConfig(InterfaceID(TransportType.SERIAL, 0), [1, 2])
    message = fe_encoder.encode_message(set_out_streams)
    serial_out.write(message)
    ```
    """
    MESSAGE_TYPE = MessageType.SET_OUTPUT_INTERFACE_CONFIG
    MESSAGE_VERSION = 0

    SetOutputInterfaceConfigMessageConstruct = Struct(
        "update_action" / AutoEnum(Int8ul, UpdateAction),
        Padding(3),
        "output_interface_config" / _OutputInterfaceConfigConstruct(),
    )

    def __init__(self,
                 output_interface_config: OutputInterfaceConfig = None,
                 update_action: UpdateAction = UpdateAction.REPLACE):
        self.update_action = UpdateAction.REPLACE
        if output_interface_config is None:
            self.output_interface_config = OutputInterfaceConfig()
        else:
            self.output_interface_config = output_interface_config

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.SetOutputInterfaceConfigMessageConstruct.build(self.__dict__)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SetOutputInterfaceConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['update_action', 'output_interface_config']
        string = f'Set Output Interface Streams Config Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class GetOutputInterfaceConfigMessage(MessagePayload):
    """!
    @brief Query the set of message streams configured to be output by the device on a specified interface.

    If the `type in `output_interface` is @ref TransportType.ALL then request the configuration for all interfaces.
    """
    MESSAGE_TYPE = MessageType.GET_OUTPUT_INTERFACE_CONFIG
    MESSAGE_VERSION = 0

    GetOutputInterfaceConfigMessageConstruct = Struct(
        "request_source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(3),
        "output_interface" / _InterfaceIDConstruct,
    )

    def __init__(self,
                 output_interface: InterfaceID = None,
                 request_source: ConfigurationSource = ConfigurationSource.ACTIVE):
        self.request_source = request_source
        if output_interface is None:
            self.output_interface = InterfaceID(TransportType.ALL, 0)
        else:
            self.output_interface = output_interface

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.GetOutputInterfaceConfigMessageConstruct.build(self.__dict__)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.GetOutputInterfaceConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['request_source', 'output_interface']
        string = f'Get Output Interface Streams Config\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.GetOutputInterfaceConfigMessageConstruct.sizeof()


class OutputInterfaceConfigResponseMessage(MessagePayload):
    """!
    @brief Response to a @ref GetOutputInterfaceConfigMessage request.
    """
    MESSAGE_TYPE = MessageType.OUTPUT_INTERFACE_CONFIG_RESPONSE
    MESSAGE_VERSION = 0

    OutputInterfaceConfigResponseMessageConstruct = Struct(
        "config_source" / AutoEnum(Int8ul, ConfigurationSource),
        "response" / AutoEnum(Int8ul, Response),
        "active_differs_from_saved" / Flag,
        "number_of_interfaces" / Int8ul,
        "output_interface_data" / Array(this.number_of_interfaces, _OutputInterfaceConfigConstruct()),
    )

    def __init__(self):
        self.config_source = ConfigurationSource.ACTIVE
        self.response = Response.OK
        self.active_differs_from_saved = False
        self.output_interface_data: List[OutputInterfaceConfig] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['number_of_interfaces'] = len(self.output_interface_data)
        packed_data = self.OutputInterfaceConfigResponseMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.OutputInterfaceConfigResponseMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['active_differs_from_saved', 'config_source', 'response', 'output_interface_data']
        string = f'Output Interface Streams Config Response\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = re.sub(r'ListContainer\((.+)\)', r'\1', val)
            val = re.sub(r'<TransportType\.(.+): [0-9]+>', r'\1', val)
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
