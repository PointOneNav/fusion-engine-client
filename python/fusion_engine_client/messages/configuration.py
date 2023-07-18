import re
from typing import Any, Iterable, NamedTuple, Optional, List, Union, Tuple

import construct
from construct import (Struct, Padding, this, Flag, Bytes, Array,
                       Float32l, Float64l, Int64ul, Int32ul, Int16ul, Int8ul, Int64sl, Int32sl, Int16sl, Int8sl, PaddedString)

from ..utils.construct_utils import NamedTupleAdapter, AutoEnum, construct_message_to_string
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
    HEADING_BIAS = 23
    ENABLED_GNSS_SYSTEMS = 50
    ENABLED_GNSS_FREQUENCY_BANDS = 51
    LEAP_SECOND = 52
    GPS_WEEK_ROLLOVER = 53
    IONOSPHERE_CONFIG = 54
    TROPOSPHERE_CONFIG = 55
    INTERFACE_CONFIG = 200
    UART1_BAUD = 256
    UART2_BAUD = 257
    UART1_OUTPUT_DIAGNOSTICS_MESSAGES = 258
    UART2_OUTPUT_DIAGNOSTICS_MESSAGES = 259
    ENABLE_WATCHDOG_TIMER = 300
    USER_DEVICE_ID = 301
    LBAND_PARAMETERS = 1024


class InterfaceConfigType(IntEnum):
  INVALID = 0
  OUTPUT_DIAGNOSTICS_MESSAGES = 1
  BAUD_RATE = 2
  REMOTE_ADDRESS = 3
  PORT = 4


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
    WEBSOCKET_SERVER = 7,
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


class IonoDelayModel(IntEnum):
    AUTO = 0
    OFF = 1
    KLOBUCHAR = 2


class TropoDelayModel(IntEnum):
    AUTO = 0
    OFF = 1
    SAASTAMOINEN = 2


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

    class InterfaceConfigClass(ConfigClass):
        """!
        @brief Abstract base class for accessing configuration types.
        """
        @classmethod
        def GetType(cls) -> ConfigType:
            return ConfigType.INTERFACE_CONFIG

        @classmethod
        def GetSubtype(cls) -> InterfaceConfigType:
            raise ValueError('Accessing `GetSubtype()` of base class')

    def __init__(self):
        # Gets populated with the mappings from ConfigType to constructs.
        self.CONFIG_MAP = {}
        self.INTERFACE_CONFIG_MAP = {}

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

    def create_interface_config_class(self, config_subtype, construct_class):
        """!
        @brief Decorator for generating InterfaceConfigClass children.

        @copydoc _ConfigClassGenerator
        """
        def inner(config_class):
            # Make the decorated class a child of ConfigClass. Add the GetType method.
            class InnerClass(config_class, self.InterfaceConfigClass):
                @classmethod
                def GetSubtype(cls) -> InterfaceConfigType:
                    return config_subtype
            InnerClass.__name__ = config_class.__name__

            # Register the construct with the MessageType.
            self.INTERFACE_CONFIG_MAP[config_subtype] = NamedTupleAdapter(InnerClass, construct_class)

            return InnerClass
        return inner

    class Point3F(NamedTuple):
        """!
        @brief 3D coordinate specifier, stored as 32-bit float values.
        """
        x: float = math.nan
        y: float = math.nan
        z: float = math.nan

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
        value: int = 0

    # Construct to serialize different sized IntegerVal types.
    UInt64Construct = Struct(
        "value" / Int64ul,
    )

    UInt32Construct = Struct(
        "value" / Int32ul,
    )

    UInt16Construct = Struct(
        "value" / Int16ul,
    )

    UInt8Construct = Struct(
        "value" / Int8ul,
    )

    Int64Construct = Struct(
        "value" / Int64sl,
    )

    Int32Construct = Struct(
        "value" / Int32sl,
    )

    Int16Construct = Struct(
        "value" / Int16sl,
    )

    Int8Construct = Struct(
        "value" / Int8sl,
    )

    class BoolVal(NamedTuple):
        """!
        @brief Bool value specifier.
        """
        value: bool = False

    # Construct to serialize 8 bit boolean types.
    BoolConstruct = Struct(
        "value" / Flag,
    )

    class StringVal(NamedTuple):
        """!
        @brief String value specifier.
        """
        value: str = ""

    @staticmethod
    def StringConstruct(max_len):
        return Struct(
            "value" / PaddedString(max_len, 'utf8'),
        )

    class SatelliteTypeMaskVal(IntegerVal):
        """!
        @brief Bitmask specifying enabled @ref SatelliteType%s.
        """
        def __new__(cls, *args, **kwargs):
            # Check if the user specified a single SatelliteType or a list of values, and convert to a mask.
            if len(args) == 1:
                # SatelliteTypeMaskVal(SatelliteType.GPS)
                # SatelliteTypeMaskVal('GPS')
                if isinstance(args[0], SatelliteType) or isinstance(args[0], str):
                    args = (SatelliteTypeMask.to_bit_mask(args),)
                # SatelliteTypeMaskVal([SatelliteType.GPS, SatelliteType.GALILEO])
                # SatelliteTypeMaskVal(['GPS', 'GALILEO'])
                elif isinstance(args[0], Iterable):
                    args = (SatelliteTypeMask.to_bit_mask(args[0])),
                # SatelliteTypeMaskVal(bit_mask)
                else:
                    pass
            # Check if the user specified one or more SatelliteTypes values, and convert to a mask:
            #   SatelliteTypeMaskVal(SatelliteType.GPS, SatelliteType.GALILEO)
            #   SatelliteTypeMaskVal('GPS', 'GALILEO')
            elif len(args) > 1:
                args = (SatelliteTypeMask.to_bit_mask(args),)

            return super().__new__(cls, *args, **kwargs)

        def __repr__(self):
            return f'{self.__class__.__name__}(value=0x{self.value:02x} ' \
                   f'({SatelliteTypeMask.bit_mask_to_string(self.value)}))'

    class FrequencyBandMaskVal(IntegerVal):
        """!
        @brief Bitmask specifying enabled @ref FrequencyBand%s.
        """
        def __new__(cls, *args, **kwargs):
            # Check if the user specified a single FrequencyBand or a list of values, and convert to a mask.
            if len(args) == 1:
                # FrequencyBandMaskVal(FrequencyBand.L1)
                # FrequencyBandMaskVal('L1')
                if isinstance(args[0], FrequencyBand) or isinstance(args[0], str):
                    args = (FrequencyBandMask.to_bit_mask(args),)
                # FrequencyBandMaskVal([FrequencyBand.L1, FrequencyBand.L5])
                # FrequencyBandMaskVal(['L1', 'L5'])
                elif isinstance(args[0], Iterable):
                    args = (FrequencyBandMask.to_bit_mask(args[0])),
                # FrequencyBandMaskVal(bit_mask)
                else:
                    pass
            # Check if the user specified one or more FrequencyBands values, and convert to a mask:
            #   FrequencyBandMaskVal(FrequencyBand.L1, FrequencyBand.L5)
            #   FrequencyBandMaskVal('L1', 'L5')
            elif len(args) > 1:
                args = (FrequencyBandMask.to_bit_mask(args),)

            return super().__new__(cls, *args, **kwargs)

        def __repr__(self):
            return f'{self.__class__.__name__}(value=0x{self.value:02x} ' \
                   f'({FrequencyBandMask.bit_mask_to_string(self.value)}))'

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
        wheelbase_m: float = math.nan
        ## The distance between the two front wheels (in meters).
        front_track_width_m: float = math.nan
        ## The distance between the two rear wheels (in meters).
        rear_track_width_m: float = math.nan

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

    class HeadingBias(NamedTuple):
        """!
        @brief Horizontal and vertical heading bias configuration settings.
        """
        horizontal_bias_deg: float = math.nan
        vertical_bias_deg: float = math.nan


    HeadingBiasConstruct = Struct(
        "horizontal_bias_deg" / Float32l,
        "vertical_bias_deg" / Float32l,
    )

    class IonosphereConfig(NamedTuple):
        """!
        @brief Ionospheric delay model configuration.
        """
        ## The ionospheric delay model to use.
        iono_delay_model: IonoDelayModel = IonoDelayModel.AUTO

    IonosphereConfigConstruct = Struct(
        "iono_delay_model" / AutoEnum(Int8ul, IonoDelayModel),
        Padding(3),
    )

    class TroposphereConfig(NamedTuple):
        """!
        @brief Tropospheric delay model configuration.
        """
        ## The tropospheric delay model to use.
        tropo_delay_model: TropoDelayModel = TropoDelayModel.AUTO

    TroposphereConfigConstruct = Struct(
        "tropo_delay_model" / AutoEnum(Int8ul, TropoDelayModel),
        Padding(3),
    )

    class LBandConfig(NamedTuple):
        """!
        @brief Configuration of the L-band demodulator parameters.
        """
        ## The center frequency of the L-band beam (Hz).
        center_frequency_hz: float

        ## The size of the signal acquisition search space (in Hz) around the center
        ## frequency.
        ##
        ## For example, a value of 6000 will search +/- 3 kHz around the center
        ## frequency.
        search_window_hz: float
        ## Service ID of the provider.
        pmp_service_id: int
        ## Data rate of the provider (bps).
        pmp_data_rate_bps: int
        ## Unique word of the provider.
        pmp_unique_word: int

    LBandConfigConstruct = Struct(
        "center_frequency_hz" / Float32l,
        "search_window_hz" / Float32l,
        "pmp_service_id" / Int32ul,
        "pmp_data_rate_bps" / Int16ul,
        Padding(2),
        "pmp_unique_word" / Int32ul,
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
class GNSSLeverArmConfig(_conf_gen.Point3F):
    """!
    @brief The location of the GNSS antenna with respect to the vehicle body frame (in meters).
    """
    pass

# Alias for convenience.
GnssLeverArmConfig = GNSSLeverArmConfig


@_conf_gen.create_config_class(ConfigType.OUTPUT_LEVER_ARM, _conf_gen.Point3FConstruct)
class OutputLeverArmConfig(_conf_gen.Point3F):
    """!
    @brief The location of the desired output location with respect to the vehicle body frame (in meters).
    """
    pass


@_conf_gen.create_config_class(ConfigType.ENABLED_GNSS_SYSTEMS, _conf_gen.UInt32Construct)
class EnabledGNSSSystemsConfig(_conf_gen.SatelliteTypeMaskVal):
    """!
    @brief A bitmask indicating which GNSS constellations are enabled.
    """
    pass


@_conf_gen.create_config_class(ConfigType.ENABLED_GNSS_FREQUENCY_BANDS, _conf_gen.UInt32Construct)
class EnabledGNSSFrequencyBandsConfig(_conf_gen.FrequencyBandMaskVal):
    """!
    @brief A bitmask indicating which GNSS frequency bands are enabled.
    """
    pass


@_conf_gen.create_config_class(ConfigType.LEAP_SECOND, _conf_gen.Int32Construct)
class LeapSecondConfig(_conf_gen.IntegerVal):
    """!
    @brief Specify a UTC leap second count override value to use for all UTC time conversions.

    Setting this value will disable all internal leap second sources, including data received from the GNSS almanac
    decoded from available signals.

    Set to -1 to disable leap second override and re-enable internal leap second handling.
    """
    def __new__(cls, value: int = -1):
        return super().__new__(cls, value)


@_conf_gen.create_config_class(ConfigType.GPS_WEEK_ROLLOVER, _conf_gen.Int32Construct)
class GPSWeekRolloverConfig(_conf_gen.IntegerVal):
    """!
    @brief Specify a GPS legacy week rollover count override to use when converting all legacy 10-bit GPS week numbers

    Setting this value will disable all internal week rollover sources, including data received from modern GPS
    navigation messages (CNAV, CNAV2) or non-GPS constellations.

    Set to -1 to disable week rollover override and re-enable internal handling.
    """
    def __new__(cls, value: int = -1):
        return super().__new__(cls, value)


@_conf_gen.create_config_class(ConfigType.IONOSPHERE_CONFIG, _conf_gen.IonosphereConfigConstruct)
class IonosphereConfig(_conf_gen.IonosphereConfig):
    """!
    @brief Ionospheric delay model configuration.
    """
    pass


@_conf_gen.create_config_class(ConfigType.TROPOSPHERE_CONFIG, _conf_gen.TroposphereConfigConstruct)
class TroposphereConfig(_conf_gen.TroposphereConfig):
    """!
    @brief Tropospheric delay model configuration.
    """
    pass


@_conf_gen.create_config_class(ConfigType.LBAND_PARAMETERS, _conf_gen.LBandConfigConstruct)
class LBandConfig(_conf_gen.LBandConfig):
    """!
    @brief Configuration of the L-band demodulator parameters.
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


@_conf_gen.create_config_class(ConfigType.USER_DEVICE_ID, _conf_gen.StringConstruct(32))
class UserDeviceID(_conf_gen.StringVal):
    """!
    @brief A string for identifying a device.
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


@_conf_gen.create_config_class(ConfigType.HEADING_BIAS, _conf_gen.HeadingBiasConstruct)
class HeadingBias(_conf_gen.HeadingBias):
    """!
    @brief Horizontal and vertical heading bias.
    """
    pass

@_conf_gen.create_interface_config_class(InterfaceConfigType.BAUD_RATE, _conf_gen.UInt32Construct)
class InterfaceBaudRateConfig(_conf_gen.IntegerVal):
    """!
    @brief Interface baud configuration settings.
    """
    pass


@_conf_gen.create_interface_config_class(InterfaceConfigType.OUTPUT_DIAGNOSTICS_MESSAGES, _conf_gen.BoolConstruct)
class InterfaceDiagnosticMessagesEnabled(_conf_gen.BoolVal):
    """!
    @brief Enable/disable output of diagnostic data on this interface.
    """
    pass


@_conf_gen.create_config_class(ConfigType.INVALID, _conf_gen.EmptyConstruct)
class InvalidConfig(_conf_gen.Empty):
    """!
    @brief Placeholder for empty invalid configuration messages.
    """
    pass


class InterfaceID(NamedTuple):
    type: TransportType = TransportType.INVALID
    index: int = 0


_InterfaceIDConstructRaw = Struct(
    "type" / AutoEnum(Int8ul, TransportType),
    "index" / Int8ul,
    Padding(2)
)
_InterfaceIDConstruct = NamedTupleAdapter(InterfaceID, _InterfaceIDConstructRaw)


class InterfaceConfigSubmessage(NamedTuple):
    interface: InterfaceID = InterfaceID()
    subtype: InterfaceConfigType = InterfaceConfigType.INVALID


_InterfaceConfigSubmessageConstructRaw = Struct(
    "interface" / _InterfaceIDConstruct,
    "subtype" / AutoEnum(Int8ul, InterfaceConfigType),
    Padding(3)
)
_InterfaceConfigSubmessageConstruct = NamedTupleAdapter(InterfaceConfigSubmessage, _InterfaceConfigSubmessageConstructRaw)


def _interface_submessage_packer(config_object, interface: Optional[InterfaceID]) -> Optional[InterfaceConfigSubmessage]:
    if isinstance(config_object, _conf_gen.InterfaceConfigClass):
        config_subtype = config_object.GetSubtype()
    elif isinstance(config_object, InterfaceConfigType):
        config_subtype = config_object
    else:
        if interface is not None:
            raise TypeError(
                f'Since an interface is set, the config_object member ({str(config_object)}) must be set to a class decorated '
                'with create_interface_config_class.')
        else:
            return None

    if interface is None:
        raise ValueError(f'To serialize InterfaceConfigClass, an interface must be provided.')
    else:
        return InterfaceConfigSubmessage(interface, config_subtype)


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
    # Flag to restore the config_type back to its default value.
    #
    # When set, the config_length_bytes should be 0 and no data should be
    # included.
    FLAG_REVERT_TO_DEFAULT = 0x02

    SetConfigMessageConstruct = Struct(
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "flags" / Int8ul,
        Padding(1),
        "config_change_length_bytes" / Int32ul,
        "config_change_data" / Bytes(this.config_change_length_bytes),
    )

    def __init__(self, config_object: Optional[_conf_gen.ConfigClass]
                 = None, flags=0x0, interface: Optional[InterfaceID] = None):
        self.config_object = config_object
        self.flags = flags
        self.interface = interface
        # Check that the parameters are consistent on whether this is a interface submessage.
        _interface_submessage_packer(self.config_object, self.interface)

    def pack(self, buffer: Optional[bytes] = None, offset: int = 0, return_buffer: bool = True) -> Tuple[bytes, int]:
        if not isinstance(self.config_object, _conf_gen.ConfigClass):
            raise TypeError(f'The config_object member ({str(self.config_object)}) must be set to a class decorated '
                            'with create_config_class.')

        config_type = self.config_object.GetType()

        submessage = _interface_submessage_packer(self.config_object, self.interface)

        if submessage:
            data = _InterfaceConfigSubmessageConstruct.build(submessage)
            construct_obj = _conf_gen.INTERFACE_CONFIG_MAP[submessage.subtype]
        else:
            data = bytes()
            construct_obj = _conf_gen.CONFIG_MAP[config_type]

        if not (self.flags & self.FLAG_REVERT_TO_DEFAULT):
            data += construct_obj.build(self.config_object)

        values = {
            'config_type': config_type,
            'flags': self.flags,
            'config_change_data': data,
            'config_change_length_bytes': len(data)
        }
        packed_data = self.SetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.SetConfigMessageConstruct.parse(buffer[offset:])

        config_change_data = parsed.config_change_data
        if parsed.config_type == ConfigType.INTERFACE_CONFIG:
            header_data = config_change_data[:_InterfaceConfigSubmessageConstruct.sizeof()]
            config_change_data = config_change_data[_InterfaceConfigSubmessageConstruct.sizeof():]
            interface_header = _InterfaceConfigSubmessageConstruct.parse(header_data)
            subtype = interface_header.subtype
            self.interface = interface_header.interface
            construct_obj = _conf_gen.INTERFACE_CONFIG_MAP[subtype]
        else:
            construct_obj = _conf_gen.CONFIG_MAP[parsed.config_type]

        if parsed.flags & self.FLAG_REVERT_TO_DEFAULT:
            self.config_object = construct_obj.tuple_cls()
        else:
            self.config_object = construct_obj.parse(config_change_data)
        self.flags = parsed.flags
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', flags=0x{self.flags:02X}, type={self.config_object.GetType()}'
        if self.config_object.GetType() == ConfigType.INTERFACE_CONFIG:
            result += f', interface={self.interface}, subtype={self.config_object.GetSubtype()}'
        result += ']'
        return result

    def __str__(self):
        fields=['config_object', 'flags']
        if self.interface is not None:
            fields.append('interface')
        return construct_message_to_string(
            message=self, construct=self.SetConfigMessageConstruct,
            title=f'Set Config Command',
            fields=fields,
            value_to_string={'flags': lambda x: '0x%X' % x})

    def calcsize(self) -> int:
        return len(self.pack())


class GetConfigMessage(MessagePayload):
    """!
    @brief Query the value of a user configuration parameter.
    """
    MESSAGE_TYPE = MessageType.GET_CONFIG
    MESSAGE_VERSION = 1

    GetConfigMessageConstruct = Struct(
        "config_type" / AutoEnum(Int16ul, ConfigType),
        "request_source" / AutoEnum(Int8ul, ConfigurationSource),
        Padding(1),
        'interface_header' / construct.If(this.config_type == ConfigType.INTERFACE_CONFIG, _InterfaceConfigSubmessageConstruct)
    )

    def __validate_interface_header(self):
        if self.interface_header:
            if self.config_type != ConfigType.INVALID and self.config_type != ConfigType.INTERFACE_CONFIG:
                raise ValueError(f"Can't specify both a config_type {str(self.config_type)} and an interface_header.")
            else:
                self.config_type = ConfigType.INTERFACE_CONFIG
        elif self.config_type == ConfigType.INTERFACE_CONFIG:
            raise ValueError(f"config_type is INTERFACE_CONFIG without specifying an interface_header.")

    def __init__(self,
                 config_type: Union[ConfigType, _ConfigClassGenerator.ConfigClass] = ConfigType.INVALID,
                 request_source: ConfigurationSource = ConfigurationSource.ACTIVE, interface_header: Optional[InterfaceConfigSubmessage]=None):
        self.request_source = request_source

        if isinstance(config_type, ConfigType):
            self.config_type = config_type
        else:
            self.config_type = config_type.GetType()

        self.interface_header = interface_header

        self.__validate_interface_header()

    def pack(self, buffer: Optional[bytes] = None, offset: int = 0, return_buffer: bool = True) -> Tuple[bytes, int]:
        self.__validate_interface_header()
        values = dict(self.__dict__)
        packed_data = self.GetConfigMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.GetConfigMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', source={self.request_source}, type={self.config_type}'
        if self.interface_header:
            result += f', interface_header={self.interface_header}'
        result += ']'
        return result

    def __str__(self):
        fields=['request_source', 'config_type']
        if self.interface_header is not None:
            fields.append('interface_header')
        return construct_message_to_string(
            message=self, construct=self.GetConfigMessageConstruct,
            title=f'Get Config Command',
            fields=fields)

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.SaveConfigMessageConstruct.parse(buffer[offset:])
        self.action = parsed.action
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', action={self.action}]'
        return result

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.SaveConfigMessageConstruct,
                                           title=f'Save Config Command')

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
        self.interface: Optional[InterfaceID] = None

        # This field is intended for internal use, and may not reflect self.config_object.
        self._config_type: ConfigType = None

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if not isinstance(self.config_object, _conf_gen.ConfigClass):
            raise TypeError(f'The config_object member ({str(self.config_object)}) must be set to a class decorated '
                            'with create_config_class.')

        values = dict(self.__dict__)
        config_type = self.config_object.GetType()

        submessage = _interface_submessage_packer(self.config_object, self.interface)

        if submessage:
            data = _InterfaceConfigSubmessageConstruct.build(submessage)
            construct_obj = _conf_gen.INTERFACE_CONFIG_MAP[submessage.subtype]
        else:
            data = bytes()
            construct_obj = _conf_gen.CONFIG_MAP[config_type]

        data += construct_obj.build(self.config_object)
        values.update({
            'config_type': config_type,
            'config_data': data,
            'config_length_bytes': len(data)
        })
        packed_data = self.ConfigResponseMessageConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.ConfigResponseMessageConstruct.parse(buffer[offset:])

        self._config_type = parsed.config_type

        self.config_source = parsed.config_source
        self.response = parsed.response
        self.flags = parsed.flags

        config_data = parsed.config_data
        if parsed.config_type == ConfigType.INTERFACE_CONFIG:
            header_data = config_data[:_InterfaceConfigSubmessageConstruct.sizeof()]
            config_data = config_data[_InterfaceConfigSubmessageConstruct.sizeof():]
            interface_header = _InterfaceConfigSubmessageConstruct.parse(header_data)
            subtype = interface_header.subtype
            self.interface = interface_header.interface
            construct_obj = _conf_gen.INTERFACE_CONFIG_MAP[subtype]
        else:
            self.interface = None
            construct_obj = _conf_gen.CONFIG_MAP[parsed.config_type]

        if parsed.config_length_bytes > 0:
            self.config_object = construct_obj.parse(config_data)
        else:
            self.config_object = None

        return parsed._io.tell()

    def __getattr__(self, item):
        if item == 'config_type':
            if self.config_object is None:
                return self._config_type
            else:
                return self.config_object.GetType()
        else:
            return super().__getattr__(item)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', response={self.response}, source={self.config_source}, type={self.config_type}]'
        return result

    def __str__(self):
        fields = ['flags', 'config_source', 'response', 'config_type', 'config_object']
        if self.interface is not None:
            fields.append('interface')
        return construct_message_to_string(
            message=self, construct=self.ConfigResponseMessageConstruct,
            title=f'Config Data',
            fields=['flags', 'config_source', 'response', 'config_type', 'config_object'],
            value_to_string={'flags': lambda x: '0x%X' % x})

    def calcsize(self) -> int:
        return len(self.pack())


################################################################################
# Input/Output Stream Control
################################################################################


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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.SetMessageRateConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', interface={self.output_interface}, flags=0x{self.flags:02X}, protocol={self.protocol}, ' \
                  f'message_id={get_message_type_string(protocol=self.protocol, message_id=self.message_id)}, ' \
                  f'rate={self.rate}]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.SetMessageRateConstruct,
            title=f'Set Message Output Rate Command',
            fields=['output_interface', 'protocol', 'message_id', 'rate', 'flags'],
            value_to_string={
                'message_id': lambda x: get_message_type_string(protocol=self.protocol, message_id=x),
                'flags': lambda x: '0x%X' % x
            })

    @classmethod
    def calcsize(cls) -> int:
        return cls.SetMessageRateConstruct.sizeof()


class GetMessageRate(MessagePayload):
    """!
    @brief Get the configured output rate for the requested message type on  the specified interface.
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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.GetMessageRateConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', interface={self.output_interface}, source={self.request_source}, protocol={self.protocol}, ' \
                  f'message_id={get_message_type_string(protocol=self.protocol, message_id=self.message_id)}]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.GetMessageRateConstruct,
            title=f'Get Message Output Rate Command',
            fields=['output_interface', 'protocol', 'request_source', 'message_id'],
            value_to_string={
                'message_id': lambda x: get_message_type_string(protocol=self.protocol, message_id=x)
            })

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
        return f'RateResponseEntry(protocol={ProtocolType(self.protocol).to_string()}), ' \
               f'flags=0x{self.flags:X}, ' \
               f'message_id={get_message_type_string(self.protocol, self.message_id)}, ' \
               f'configured_rate={MessageRate(self.configured_rate).to_string()}, ' \
               f'effective_rate={MessageRate(self.effective_rate).to_string()})'


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
        self.rates: List[RateResponseEntry] = []

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        values['num_rates'] = len(self.rates)
        packed_data = self.MessageRateResponseConstruct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.MessageRateResponseConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', response={self.response}, interface={self.output_interface}, source={self.config_source}, ' \
                  f'num_entries={len(self.rates)}]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.MessageRateResponseConstruct,
            title=f'Message Output Rate Response',
            fields=['config_source', 'response', 'output_interface', 'num_rates', 'rates'])

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.ImportDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', type={self.data_type}, source={self.source}, version={self.data_version}, ' \
                  f'size={len(self.data)} B]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.ImportDataMessageConstruct,
            title=f'Import Data Command ({str(self.data_type)}, {len(self.data)} B)',
            fields=['source', 'data_version'])

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.ExportDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', type={self.data_type}, source={self.source}]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.ExportDataMessageConstruct,
            title=f'Export Data Command ({str(self.data_type)})',
            fields=['source'])

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.PlatformStorageDataMessageConstruct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        return parsed._io.tell()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', response={self.response}, type={self.data_type}, source={self.source}, ' \
                  f'version={self.data_version}, size={len(self.data)} B]'
        return result

    def __str__(self):
        return construct_message_to_string(
            message=self, construct=self.PlatformStorageDataMessageConstruct,
            title=f'Platform Storage Data ({str(self.data_type)}, {len(self.data)} B)',
            fields=['response', 'source', 'data_version'])

    def calcsize(self) -> int:
        return len(self.pack())
