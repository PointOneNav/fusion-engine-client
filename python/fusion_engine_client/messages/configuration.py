import re
from typing import NamedTuple, Optional, List

from construct import (Struct, Float32l, Int32ul, Int16ul, Int8ul, Padding, this, Flag, Bytes, Array)

from ..utils.construct_utils import NamedTupleAdapter, AutoEnum
from ..utils.enum_utils import IntEnum
from .defs import *


################################################################################
# Device Configuration Support
################################################################################


class ConfigurationSource(IntEnum):
    ACTIVE = 0
    SAVED = 1


class ConfigType(IntEnum):
    INVALID = 0
    DEVICE_LEVER_ARM = 16
    DEVICE_COARSE_ORIENTATION = 17
    GNSS_LEVER_ARM = 18
    OUTPUT_LEVER_ARM = 19
    VEHICLE_DETAILS = 20
    WHEEL_CONFIG = 21
    HARDWARE_TICK_CONFIG = 22
    UART1_BAUD = 256
    UART2_BAUD = 257
    UART1_OUTPUT_DIAGNOSTICS_MESSAGES = 258
    UART2_OUTPUT_DIAGNOSTICS_MESSAGES = 259
    ENABLE_WATCHDOG_TIMER = 300


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


class VehicleModel(IntEnum):
    UNKNOWN_VEHICLE = 0,
    DATASPEED_CD4 = 1,
    ## In general, all J1939 vehicles support a subset of the J1939 standard and
    ## may be set to vehicle model `J1939`. Their 29-bit CAN IDs may differ
    ## based on how the platform assigns message priorities and source
    ## addresses, but the underlying program group number (PGN) and message
    ## contents will be consistent.
    ##
    ## For most vehicles, it is not necessary to specify and particular make and
    ## model.
    J1939 = 2,

    LEXUS_CT200H = 20,

    KIA_SORENTO = 40,
    KIA_SPORTAGE = 41,

    AUDI_Q7 = 60,
    AUDI_A8L = 61,

    TESLA_MODEL_X = 80,
    TESLA_MODEL_3 = 81,

    HYUNDAI_ELANTRA = 100,

    PEUGEOT_206 = 120,

    MAN_TGX = 140,

    FACTION = 160,

    LINCOLN_MKZ = 180,

    BMW_7 = 200


class WheelSensorType(IntEnum):
    NONE = 0,
    TICK_RATE = 1,
    TICKS = 2,
    WHEEL_SPEED = 3,
    VEHICLE_SPEED = 4,
    VEHICLE_TICKS = 5


class AppliedSpeedType(IntEnum):
    NONE = 0,
    REAR_WHEELS = 1,
    FRONT_WHEELS = 2,
    FRONT_AND_REAR_WHEELS = 3,
    VEHICLE_BODY = 4


class SteeringType(IntEnum):
    UNKNOWN = 0,
    FRONT = 1,
    FRONT_AND_REAR = 2


class TickMode(IntEnum):
    OFF = 0,
    RISING_EDGE = 1,
    FALLING_EDGE = 2


class TickDirection(IntEnum):
    OFF = 0,
    FORWARD_ACTIVE_HIGH = 1,
    FORWARD_ACTIVE_LOW = 2


class TransportType(IntEnum):
    INVALID = 0,
    SERIAL = 1,
    FILE = 2,
    TCP_CLIENT = 3,
    TCP_SERVER = 4,
    UDP_CLIENT = 5,
    UDP_SERVER = 6,
    ## Set/get the configuration for the interface on which the command was received.
    CURRENT = 254,
    ## Set/get the configuration for the all I/O interfaces.
    ALL = 255,


class UpdateAction(IntEnum):
    REPLACE = 0


class ProtocolType(IntEnum):
    INVALID = 0
    FUSION_ENGINE = 1
    NMEA = 2
    RTCM = 3
    ALL = 255


class MessageRate(IntEnum):
    OFF = 0
    ON_CHANGE = 1
    MAX_RATE = 1
    INTERVAL_10_MS = 2
    INTERVAL_20_MS = 3
    INTERVAL_40_MS = 4
    INTERVAL_50_MS = 5
    INTERVAL_100_MS = 6
    INTERVAL_200_MS = 7
    INTERVAL_500_MS = 8
    INTERVAL_1_S = 9
    INTERVAL_2_S = 10
    INTERVAL_5_S = 11
    INTERVAL_10_S = 12
    INTERVAL_30_S = 13
    INTERVAL_60_S = 14
    DEFAULT = 255


ALL_MESSAGES_ID = 0xFFFF


class NmeaMessageType(IntEnum):
    INVALID = 0

    GGA = 1
    GLL = 2
    GSA = 3
    GSV = 4
    RMC = 5
    VTG = 6

    P1CALSTATUS = 1000
    P1MSG = 1001

    PQTMVERNO = 1200
    PQTMVER = 1201
    PQTMGNSS = 1202
    PQTMVERNO_SUB = 1203
    PQTMVER_SUB = 1204
    PQTMTXT = 1205


def get_message_type_string(protocol: ProtocolType, message_id: int):
    if message_id == ALL_MESSAGES_ID:
        return 'ALL (%d)' % message_id
    else:
        enum = None
        try:
            if protocol == ProtocolType.NMEA:
                enum = NmeaMessageType(message_id)
            elif protocol == ProtocolType.FUSION_ENGINE:
                enum = MessageType(message_id)
        except ValueError:
            pass

        if enum is None:
            return str(message_id)
        else:
            return '%s (%d)' % (str(enum), int(enum))


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

    class BoolVal(NamedTuple):
        """!
        @brief Bool value specifier.
        """
        value: bool

    # Construct to serialize 8 bit boolean types.
    BoolConstruct = Struct(
        "value" / Flag,
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

    class VehicleDetails(NamedTuple):
        """!
        @brief Information including vehicle model and dimensions.
        """
        vehicle_model: VehicleModel = VehicleModel.UNKNOWN_VEHICLE
        ## The distance between the front axle and rear axle (in meters).
        wheelbase_m: float = 0
        ## The distance between the two front wheels (in meters).
        front_track_width_m: float = 0
        ## The distance between the two rear wheels (in meters).
        rear_track_width_m: float = 0

    VehicleDetailsConstruct = Struct(
        "vehicle_model" / AutoEnum(Int16ul, VehicleModel),
        Padding(10),
        "wheelbase_m" / Float32l,
        "front_track_width_m" / Float32l,
        "rear_track_width_m" / Float32l,
    )

    class WheelConfig(NamedTuple):
        """!
        @brief Vehicle/wheel speed measurement configuration settings.

        See:
        - @ref WheelSpeedMeasurement
        - @ref VehicleSpeedMeasurement
        - @ref WheelTickMeasurement
        - @ref VehicleTickMeasurement
        """
        ## The type of vehicle/wheel speed measurements produced by the vehicle.
        wheel_sensor_type: WheelSensorType = WheelSensorType.NONE
        ## The type of vehicle/wheel speed measurements to be applied to the navigation solution.
        applied_speed_type: AppliedSpeedType = AppliedSpeedType.REAR_WHEELS
        ## Indication of which of the vehicle's wheels are steered.
        steering_type: SteeringType = SteeringType.UNKNOWN
        ## The nominal rate at which wheel speed measurements will be provided (in seconds).
        wheel_update_interval_sec: float = math.nan
        ## The nominal rate at which wheel tick measurements will be provided (in seconds).
        wheel_tick_output_interval_sec: float = math.nan
        ## Ratio between angle of the steering wheel and the angle of the wheels on the ground.
        steering_ratio: float = math.nan
        ## The scale factor to convert from wheel encoder ticks to distance (in meters/tick).
        wheel_ticks_to_m: float = math.nan
        ## The maximum value (inclusive) before the wheel tick measurement will roll over.
        wheel_tick_max_value: int = 0
        ## `True` if the reported wheel tick measurements should be interpreted as signed integers, or `False` if they
        ## should be interpreted as unsigned integers.
        wheel_ticks_signed: bool = False
        ## `True` if the wheel tick measurements increase by a positive amount when driving forward or backward.
        ## `False` if wheel tick measurements decrease when driving backward.
        wheel_ticks_always_increase: bool = True

    WheelConfigConstruct = Struct(
        "wheel_sensor_type" / AutoEnum(Int8ul, WheelSensorType),
        "applied_speed_type" / AutoEnum(Int8ul, AppliedSpeedType),
        "steering_type" / AutoEnum(Int8ul, SteeringType),
        Padding(1),
        "wheel_update_interval_sec" / Float32l,
        "wheel_tick_output_interval_sec" / Float32l,
        "steering_ratio" / Float32l,
        "wheel_ticks_to_m" / Float32l,
        "wheel_tick_max_value" / Int32ul,
        "wheel_ticks_signed" / Flag,
        "wheel_ticks_always_increase" / Flag,
        Padding(2),
    )

    class HardwareTickConfig(NamedTuple):
        """!
        @brief Hardware wheel encoder configuration settings.

        See @ref VehicleTickMeasurement.
        """
        ##
        # If enabled -- tick mode is not OFF -- the device will accumulate ticks received on the I/O pin, and use them
        # as an indication of vehicle speed. If enabled, you must also specify @ref wheel_ticks_to_m to indicate the
        # mapping of wheel tick encoder angle to tire circumference. All other wheel tick-related parameters such as
        # tick capture rate, rollover value, etc. will be set internally.
        tick_mode: TickMode = TickMode.OFF

        ##
        # When direction is OFF, the incoming ticks will be treated as unsigned, meaning the tick count will continue
        # to increase in either direction of travel. If direction is not OFF, a second direction I/O pin will be used
        # to indicate the direction of travel and the accumulated tick count will increase/decrease accordingly.
        tick_direction: TickDirection = TickDirection.OFF

        ## The scale factor to convert from wheel encoder ticks to distance (in meters/tick).
        wheel_ticks_to_m: float = math.nan

    HardwareTickConfigConstruct = Struct(
        "tick_mode" / AutoEnum(Int8ul, TickMode),
        "tick_direction" / AutoEnum(Int8ul, TickDirection),
        Padding(2),
        "wheel_ticks_to_m" / Float32l,
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


@_conf_gen.create_config_class(ConfigType.UART1_BAUD, _conf_gen.UInt32Construct)
class Uart1BaudConfig(_conf_gen.IntegerVal):
    """!
    @brief The UART1 serial baud rate (in bits/second).
    """
    pass


@_conf_gen.create_config_class(ConfigType.UART2_BAUD, _conf_gen.UInt32Construct)
class Uart2BaudConfig(_conf_gen.IntegerVal):
    """!
    @brief The UART2 serial baud rate (in bits/second).
    """
    pass


@_conf_gen.create_config_class(ConfigType.UART1_OUTPUT_DIAGNOSTICS_MESSAGES, _conf_gen.BoolConstruct)
class Uart1DiagnosticMessagesEnabled(_conf_gen.BoolVal):
    """!
    @brief Whether to output the diagnostic message set on UART1.
    """
    pass


@_conf_gen.create_config_class(ConfigType.UART2_OUTPUT_DIAGNOSTICS_MESSAGES, _conf_gen.BoolConstruct)
class Uart2DiagnosticMessagesEnabled(_conf_gen.BoolVal):
    """!
    @brief Whether to output the diagnostic message set on UART2.
    """
    pass


@_conf_gen.create_config_class(ConfigType.ENABLE_WATCHDOG_TIMER, _conf_gen.BoolConstruct)
class WatchdogTimerEnabled(_conf_gen.BoolVal):
    """!
    @brief Enable watchdog timer to restart device after fatal errors.
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


@_conf_gen.create_config_class(ConfigType.VEHICLE_DETAILS, _conf_gen.VehicleDetailsConstruct)
class VehicleDetailsConfig(_conf_gen.VehicleDetails):
    """!
    @brief Information including vehicle model and dimensions.
    """
    pass


@_conf_gen.create_config_class(ConfigType.WHEEL_CONFIG, _conf_gen.WheelConfigConstruct)
class WheelConfig(_conf_gen.WheelConfig):
    """!
    @brief Information pertaining to wheel speeds.
    """
    pass


@_conf_gen.create_config_class(ConfigType.HARDWARE_TICK_CONFIG, _conf_gen.HardwareTickConfigConstruct)
class HardwareTickConfig(_conf_gen.HardwareTickConfig):
    """!
    @brief Tick configuration settings.
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

    # Flag to immediately save the config after applying this setting.
    FLAG_APPLY_AND_SAVE = 0x01

    SetConfigMessageConstruct = Struct(
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "flags" / Int8ul,
        Padding(1),
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Bytes(this.config_change_length_bytes),
    )

    def __init__(self, config_object: Optional[_conf_gen.ConfigClass] = None, flags=0x0):
        self.config_object = config_object
        self.flags = flags

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if not isinstance(self.config_object, _conf_gen.ConfigClass):
            raise TypeError(f'The config_object member ({str(self.config_object)}) must be set to a class decorated '
                            'with create_config_class.')
        config_type = self.config_object.GetType()
        construct_obj = _conf_gen.CONFIG_MAP[config_type]
        data = construct_obj.build(self.config_object)
        values = {
            'config_type': config_type,
            'flags': self.flags,
            'config_change_data': data,
            'config_change_length_bytes': len(data)
        }
        packed_data = self.SetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SetConfigMessageConstruct.parse(buffer[offset:])
        self.config_object = _conf_gen.CONFIG_MAP[parsed.config_type].parse(parsed.config_change_data)
        self.flags = parsed.flags
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

    # Flag to indicate the active value for this configuration parameter differs from the value saved to persistent
    # memory.
    FLAG_ACTIVE_DIFFERS_FROM_SAVED = 0x1

    ConfigResponseMessageConstruct = Struct(
        "config_source" / AutoEnum(Int8ul, ConfigurationSource),
        "flags" / Int8ul,
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "response" / AutoEnum(Int8ul, Response),
        Padding(3),
        "config_length_bytes" / Int32ul,
        "config_data" / Bytes(this.config_length_bytes),
    )

    def __init__(self):
        self.config_source = ConfigurationSource.ACTIVE
        self.response = Response.OK
        self.flags = 0
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
        fields = ['flags', 'config_source', 'response', 'config_object']
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


_InterfaceIDConstructRaw = Struct(
    "type" / AutoEnum(Int8ul, TransportType),
    "index" / Int8ul,
    Padding(2)
)
_InterfaceIDConstruct = NamedTupleAdapter(InterfaceID, _InterfaceIDConstructRaw)


class SetMessageRate(MessagePayload):
    """!
    @brief Set the output rate for the requested message type on the specified interface.
    """
    MESSAGE_TYPE = MessageType.SET_MESSAGE_RATE
    MESSAGE_VERSION = 0

    # Flag to immediately save the config after applying this setting.
    FLAG_APPLY_AND_SAVE = 0x01
    # Flag to apply bulk interval changes to all messages instead of just enabled messages.
    FLAG_INCLUDE_DISABLED_MESSAGES = 0x02

    SetMessageRateConstruct = Struct(
        "output_interface" / _InterfaceIDConstruct,
        "protocol" / AutoEnum(Int8ul, ProtocolType),
        "flags" / Int8ul,
        "message_id" / Int16ul,
        "rate" / AutoEnum(Int8ul, MessageRate),
        Padding(3),
    )

    def __init__(self,
                 output_interface: Optional[InterfaceID] = None,
                 protocol: ProtocolType = ProtocolType.INVALID,
                 message_id: Optional[int] = None,
                 rate: MessageRate = MessageRate.OFF,
                 flags: int = 0x0):
        if output_interface is None:
            self.output_interface = InterfaceID(type=TransportType.CURRENT)
        else:
            self.output_interface = output_interface

        self.protocol = protocol
        self.rate = rate
        self.flags = flags

        if message_id is None:
            self.message_id = ALL_MESSAGES_ID
        else:
            self.message_id = message_id

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.SetMessageRateConstruct.build(self.__dict__)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.SetMessageRateConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['output_interface', 'protocol', 'message_id', 'rate', 'flags']
        string = f'Set Message Output Rate Command\n'
        for field in fields:
            if field == 'message_id':
                val = get_message_type_string(self.protocol, self.message_id)
            else:
                val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.SetMessageRateConstruct.sizeof()


class GetMessageRate(MessagePayload):
    """!
    @brief Get the configured output rate for the he requested message type on  the specified interface.
    """
    MESSAGE_TYPE = MessageType.GET_MESSAGE_RATE
    MESSAGE_VERSION = 0

    GetMessageRateConstruct = Struct(
        "output_interface" / _InterfaceIDConstruct,
        "protocol" / AutoEnum(Int8ul, ProtocolType),
        "request_source" / AutoEnum(Int8ul, ConfigurationSource),
        "message_id" / Int16ul,
    )

    def __init__(self,
                 output_interface: Optional[InterfaceID] = None,
                 protocol: ProtocolType = ProtocolType.ALL,
                 request_source: ConfigurationSource = ConfigurationSource.ACTIVE,
                 message_id: Optional[int] = None):
        if output_interface is None:
            self.output_interface = InterfaceID(type=TransportType.CURRENT)
        else:
            self.output_interface = output_interface

        self.protocol = protocol
        self.request_source = request_source

        if message_id is None:
            self.message_id = ALL_MESSAGES_ID
        else:
            self.message_id = message_id

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        packed_data = self.GetMessageRateConstruct.build(self.__dict__)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.GetMessageRateConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['output_interface', 'protocol', 'request_source', 'message_id']
        string = f'Get Message Output Rate Command\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            string += f'  {field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return cls.GetMessageRateConstruct.sizeof()


class RateResponseEntry(NamedTuple):
    protocol: ProtocolType = ProtocolType.INVALID
    flags: int = 0
    message_id: int = 0
    configured_rate: MessageRate = MessageRate.OFF
    effective_rate: MessageRate = MessageRate.OFF

    __parent_str__ = object.__str__

    def __str__(self):
        return f'RateResponseEntry(protocol={self.protocol.to_string(True)}), flags={self.flags}, ' \
               f'message_id={get_message_type_string(self.protocol, self.message_id)}, ' \
               f'configured_rate={self.configured_rate.to_string(True)}, ' \
               f'effective_rate={self.effective_rate.to_string(True)})'


_RateResponseEntryConstructRaw = Struct(
    "protocol" / AutoEnum(Int8ul, ProtocolType),
    "flags" / Int8ul,
    "message_id" / Int16ul,
    "configured_rate" / AutoEnum(Int8ul, MessageRate),
    "effective_rate" / AutoEnum(Int8ul, MessageRate),
    Padding(2)
)
_RateResponseEntryConstruct = NamedTupleAdapter(RateResponseEntry, _RateResponseEntryConstructRaw)


class MessageRateResponse(MessagePayload):
    """!
    @brief Response to a @ref GetMessageRate request.
    """
    MESSAGE_TYPE = MessageType.MESSAGE_RATE_RESPONSE
    MESSAGE_VERSION = 1

    # Flag to indicate the active value for a message rate differs from the value saved to persistent memory.
    FLAG_ACTIVE_DIFFERS_FROM_SAVED = 0x1

    MessageRateResponseConstruct = Struct(
        "config_source" / AutoEnum(Int8ul, ConfigurationSource),
        "response" / AutoEnum(Int8ul, Response),
        "num_rates" / Int16ul,
        "output_interface" / _InterfaceIDConstruct,
        "rates" / Array(this.num_rates, _RateResponseEntryConstruct),
    )

    def __init__(self):
        self.config_source = ConfigurationSource.ACTIVE
        self.response = Response.OK
        self.output_interface = InterfaceID(TransportType.INVALID, 0)
        self.protocol = ProtocolType.INVALID
        self.rates: List[RateResponseEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['num_rates'] = len(self.rates)
        packed_data = self.MessageRateResponseConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.MessageRateResponseConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = [
            'config_source',
            'response',
            'output_interface',
            'num_rates',
            'rates']
        string = f'Message Output Rate Response\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = re.sub(r'ListContainer\((.+)\)', r'\1', val)
            val = re.sub(r'<TransportType\.(.+): [0-9]+>', r'\1', val)
            string += f'  {field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class DataVersion(NamedTuple):
    major: int
    minor: int


_DataVersionConstructRaw = Struct(
    Padding(1),
    "major" / Int8ul,
    "minor" / Int16ul,
)
_DataVersionConstruct = NamedTupleAdapter(DataVersion, _DataVersionConstructRaw)


class DataType(IntEnum):
    CALIBRATION_STATE = 0
    CRASH_LOG = 1
    FILTER_STATE = 2
    USER_CONFIG = 3
    INVALID = 255


class ImportDataMessage(MessagePayload):
    """!
    @brief Import data from the host to the device.
    """
    MESSAGE_TYPE = MessageType.IMPORT_DATA
    MESSAGE_VERSION = 0

    ImportDataMessageConstruct = Struct(
        "data_type" / AutoEnum(Int8ul, DataType),
        "source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(2),
        "data_version" / _DataVersionConstruct,
        Padding(4),
        "data_length_bytes" / Int32ul,
        "data" / Bytes(this.data_length_bytes),
    )

    def __init__(
            self,
            data_type=DataType.INVALID,
            data_version=DataVersion(0, 0),
            data=None,
            source=ConfigurationSource.ACTIVE):
        self.data_version = data_version
        self.data_type = data_type
        self.source = source
        self.data = bytes() if data is None else data

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['data_length_bytes'] = len(self.data)
        packed_data = self.ImportDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ImportDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['source', 'data_version']
        string = f'Import Data Command ({str(self.data_type)}, {len(self.data)} B)\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())


class ExportDataMessage(MessagePayload):
    """!
    @brief Export data from the device.
    """
    MESSAGE_TYPE = MessageType.EXPORT_DATA
    MESSAGE_VERSION = 0

    ExportDataMessageConstruct = Struct(
        "data_type" / AutoEnum(Int8ul, DataType),
        "source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(3),
    )

    def __init__(self, data_type=DataType.INVALID, source=ConfigurationSource.ACTIVE):
        self.data_type = data_type
        self.source = source

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.ExportDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.ExportDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['source']
        string = f'Export data command ({str(self.data_type)})\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    @classmethod
    def calcsize(cls) -> int:
        return ExportDataMessage.ExportDataMessageConstruct.sizeof()


class PlatformStorageDataMessage(MessagePayload):
    """!
    @brief Device storage data response.
    """
    MESSAGE_TYPE = MessageType.PLATFORM_STORAGE_DATA
    MESSAGE_VERSION = 2

    PlatformStorageDataMessageConstruct = Struct(
        "data_type" / AutoEnum(Int8ul, DataType),
        "response" / AutoEnum(Int8ul, Response),
        "source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(1),
        "data_version" / _DataVersionConstruct,
        "data_length_bytes" / Int32ul,
        "data" / Bytes(this.data_length_bytes),
    )

    def __init__(self):
        self.data_version = DataVersion(0, 0)
        self.data_type = DataType.INVALID
        self.response = Response.DATA_CORRUPTED
        self.source = ConfigurationSource.ACTIVE
        self.data = bytes()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['data_length_bytes'] = len(self.data)
        packed_data = self.PlatformStorageDataMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        parsed = self.PlatformStorageDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __str__(self):
        fields = ['response', 'source', 'data_version']
        string = f'Platform Storage Data ({str(self.data_type)}, {len(self.data)} B)\n'
        for field in fields:
            val = str(self.__dict__[field]).replace('Container:', '')
            val = val.replace('  ', '\t')
            string += f'\t{field}: {val}\n'
        return string.rstrip()

    def calcsize(self) -> int:
        return len(self.pack())
