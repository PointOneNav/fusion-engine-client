import struct
from typing import Sequence

import numpy as np

from .defs import *
from ..utils.enum_utils import IntEnum


class IMUMeasurement(MessagePayload):
    """!
    @brief IMU sensor measurement data.
    """
    MESSAGE_TYPE = MessageType.IMU_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<3d 3d 3d 3d')

    def __init__(self):
        self.p1_time = Timestamp()

        self.accel_mps2 = np.full((3,), np.nan)
        self.accel_std_mps2 = np.full((3,), np.nan)

        self.gyro_rps = np.full((3,), np.nan)
        self.gyro_std_rps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.accel_mps2,
            self.accel_std_mps2,
            self.gyro_rps,
            self.gyro_std_rps)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.p1_time.unpack(buffer, offset)

        offset += self.unpack_values(
            self._STRUCT, buffer, offset,
            self.accel_mps2,
            self.accel_std_mps2,
            self.gyro_rps,
            self.gyro_std_rps)

        return offset - initial_offset

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        return 'IMU Measurement @ %s' % str(self.p1_time)

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'accel_mps2': np.array([m.accel_mps2 for m in messages]).T,
            'accel_std_mps2': np.array([m.accel_std_mps2 for m in messages]).T,
            'gyro_rps': np.array([m.gyro_rps for m in messages]).T,
            'gyro_std_rps': np.array([m.gyro_std_rps for m in messages]).T,
        }
        return result

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + cls._STRUCT.size


class GearType(IntEnum):
  UNKNOWN = 0 ##< The transmission gear is not known, or does not map to a supported GearType.
  FORWARD = 1 ##< The vehicle is in a forward gear.
  REVERSE = 2 ##< The vehicle is in reverse.
  PARK = 3 ##< The vehicle is parked.
  NEUTRAL = 4 ##< The vehicle is in neutral.


class WheelSpeedMeasurement(MessagePayload):
    """!
    @brief Differential wheel speed measurement.

    This message may be used to convey the speed of each individual wheel on the
    vehicle. The number and type of wheels expected varies by vehicle. To use
    wheel speed data, you must first configure the device by issuing a @ref
    SetConfigMessage message containing a @ref WheelConfig payload describing the
    vehicle sensor configuration.

    Some platforms may support an additional, optional voltage signal used to
    indicate direction of motion. Alternatively, when receiving CAN data from a
    vehicle, direction may be conveyed explicitly in a CAN message, or may be
    indicated based on the current transmission gear setting.
    """
    MESSAGE_TYPE = MessageType.WHEEL_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<4f B ? 2x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        ## The front left wheel speed (in m/s). Set to NAN if not available.
        self.front_left_speed_mps = np.nan

        ## The front right wheel speed (in m/s). Set to NAN if not available.
        self.front_right_speed_mps = np.nan

        ## The rear left wheel speed (in m/s). Set to NAN if not available.
        self.rear_left_speed_mps = np.nan

        ## The rear right wheel speed (in m/s). Set to NAN if not available.
        self.rear_right_speed_mps = np.nan

        ##
        # The transmission gear currently in use, or direction of motion, if available.
        #
        # Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle direction information is available
        # externally.
        self.gear = GearType.UNKNOWN

        ##
        # `true` if the wheel speeds are signed (positive forward, negative reverse), or `false` if the values are
        # unsigned (positive in both directions).
        self.is_signed = True

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.timestamps.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.front_left_speed_mps,
            self.front_right_speed_mps,
            self.rear_left_speed_mps,
            self.rear_right_speed_mps,
            int(self.gear),
            self.is_signed)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)

        (self.front_left_speed_mps,
         self.front_right_speed_mps,
         self.rear_left_speed_mps,
         self.rear_right_speed_mps,
         gear_int,
         self.is_signed) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.timestamps.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Speed Measurement @ {str(self.timestamps.p1_time)}
  {str(self.timestamps).replace(newline, '  ' + newline)}
  Gear: {str(self.gear)}
  Front left: {self.front_left_speed_mps:.2f} m/s
  Front right: {self.front_right_speed_mps:.2f} m/s
  Rear left: {self.rear_left_speed_mps:.2f} m/s
  Rear right: {self.rear_right_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'front_left_speed_mps': np.array([m.front_left_speed_mps for m in messages]),
            'front_right_speed_mps': np.array([m.front_right_speed_mps for m in messages]),
            'rear_left_speed_mps': np.array([m.rear_left_speed_mps for m in messages]),
            'rear_right_speed_mps': np.array([m.rear_right_speed_mps for m in messages]),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementTimestamps.to_numpy([m.timestamps for m in messages]))
        return result


class VehicleSpeedMeasurement(MessagePayload):
    """!
    @brief Vehicle body speed measurement.

    This message may be used to convey the along-track speed of the vehicle
    (forward/backward). To use vehicle speed data, you must first configure the
    device by issuing a @ref SetConfigMessage message containing a @ref
    WheelConfig payload describing the vehicle sensor configuration.

    Some platforms may support an additional, optional voltage signal used to
    indicate direction of motion. Alternatively, when receiving CAN data from a
    vehicle, direction may be conveyed explicitly in a CAN message, or may be
    indicated based on the current transmission gear setting.
    """
    MESSAGE_TYPE = MessageType.VEHICLE_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<f B ? 2x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        ## The current vehicle speed estimate (in m/s).
        self.vehicle_speed_mps = np.nan

        ##
        # The transmission gear currently in use, or direction of motion, if available.
        #
        # Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle direction information is available
        # externally.
        self.gear = GearType.UNKNOWN

        ##
        # `true` if the wheel speeds are signed (positive forward, negative reverse), or `false` if the values are
        # unsigned (positive in both directions).
        self.is_signed = True

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.timestamps.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.vehicle_speed_mps,
            int(self.gear),
            self.is_signed)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)

        (self.vehicle_speed_mps,
         gear_int,
         self.is_signed) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.timestamps.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Speed Measurement @ {str(self.timestamps.p1_time)}
  {str(self.timestamps).replace(newline, '  ' + newline)}
  Gear: {str(self.gear)}
  Speed: {self.vehicle_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'vehicle_speed_mps': np.array([m.vehicle_speed_mps for m in messages]),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementTimestamps.to_numpy([m.timestamps for m in messages]))
        return result


class WheelTickMeasurement(MessagePayload):
    """!
    @brief Differential wheel encoder tick measurement.

    This message may be used to convey a one or more wheel encoder tick counts
    received either by software (e.g., vehicle CAN bus), or captured in hardware
    from external voltage pulses. The number and type of wheels expected, and the
    interpretation of the tick count values, varies by vehicle. To use wheel
    encoder data, you ust first configure the device by issuing a @ref
    SetConfigMessage message containing a @ref WheelConfig payload describing the
    vehicle sensor configuration.

    Some platforms may support an additional, optional voltage signal used to
    indicate direction of motion. Alternatively, when receiving CAN data from a
    vehicle, direction may be conveyed explicitly in a CAN message, or may be
    indicated based on the current transmission gear setting.
    """
    MESSAGE_TYPE = MessageType.WHEEL_TICK_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<4I B 3x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        ## The front left wheel tick count.
        self.front_left_wheel_ticks = 0

        ## The front right wheel tick count.
        self.front_right_wheel_ticks = 0

        ## The rear left wheel tick count.
        self.rear_left_wheel_ticks = 0

        ## The rear right wheel tick count.
        self.rear_right_wheel_ticks = 0

        ##
        # The transmission gear currently in use, or direction of motion, if available.
        #
        # Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle direction information is available
        # externally.
        self.gear = GearType.UNKNOWN

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.timestamps.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.front_left_wheel_ticks,
            self.front_right_wheel_ticks,
            self.rear_left_wheel_ticks,
            self.rear_right_wheel_ticks,
            int(self.gear))

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)

        (self.front_left_wheel_ticks,
         self.front_right_wheel_ticks,
         self.rear_left_wheel_ticks,
         self.rear_right_wheel_ticks,
         gear_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.timestamps.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Tick Measurement @ {str(self.timestamps.p1_time)}
  {str(self.timestamps).replace(newline, '  ' + newline)}
  Gear: {str(self.gear)}
  Front left: {self.front_left_wheel_ticks}
  Front right: {self.front_right_wheel_ticks}
  Rear left: {self.rear_left_wheel_ticks}
  Rear right: {self.rear_right_wheel_ticks}"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'front_left_wheel_ticks': np.array([m.front_left_wheel_ticks for m in messages], dtype=int),
            'front_right_wheel_ticks': np.array([m.front_right_wheel_ticks for m in messages], dtype=int),
            'rear_left_wheel_ticks': np.array([m.rear_left_wheel_ticks for m in messages], dtype=int),
            'rear_right_wheel_ticks': np.array([m.rear_right_wheel_ticks for m in messages], dtype=int),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementTimestamps.to_numpy([m.timestamps for m in messages]))
        return result


class VehicleTickMeasurement(MessagePayload):
    """!
    @brief Singular wheel encoder tick measurement, representing vehicle body speed.

    This message may be used to convey a one or more wheel encoder tick counts
    received either by software (e.g., vehicle CAN bus), or captured in hardware
    from external voltage pulses. The number and type of wheels expected, and the
    interpretation of the tick count values, varies by vehicle. To use wheel
    encoder data, you ust first configure the device by issuing a @ref
    SetConfigMessage message containing a @ref WheelConfig payload describing the
    vehicle sensor configuration.

    Some platforms may support an additional, optional voltage signal used to
    indicate direction of motion. Alternatively, when receiving CAN data from a
    vehicle, direction may be conveyed explicitly in a CAN message, or may be
    indicated based on the current transmission gear setting.
    """
    MESSAGE_TYPE = MessageType.VEHICLE_TICK_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<I B 3x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        ## The current encoder tick count. The interpretation of these ticks is defined outside of this message.
        self.tick_count = 0

        ##
        # The transmission gear currently in use, or direction of motion, if available.
        #
        # Set to @ref GearType::FORWARD or @ref GearType::REVERSE where vehicle direction information is available
        # externally.
        self.gear = GearType.UNKNOWN

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.timestamps.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.tick_count,
            int(self.gear))

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)

        (self.tick_count,
         gear_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.timestamps.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Tick Measurement @ {str(self.timestamps.p1_time)}
  {str(self.timestamps).replace(newline, '  ' + newline)}
  Gear: {str(self.gear)}
  Ticks: {self.tick_count}"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'tick_count': np.array([m.tick_count for m in messages], dtype=int),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementTimestamps.to_numpy([m.timestamps for m in messages]))
        return result


class HeadingMeasurement(MessagePayload):
    """!
     @brief The heading angle (in degrees) with respect to true north,
            pointing from the primary antenna to the secondary antenna.
     @ingroup solution_messages

     @note
     All data is timestamped using the P1 Time values, which is a monotonic
     timestamp referenced to the start of the device. Corresponding messages (@ref
     PoseMessage, @ref GNSSSatelliteMessage, etc.) may be associated using
     their @ref timestamps.
    """
    MESSAGE_TYPE = MessageType.HEADING_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<B3xL3f3fff')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        # The type of this position solution.
        self.solution_type = SolutionType.Invalid
        # A bitmask of flags associated with the solution
        self.flags = 0
        # The ID of the differential base station, if used.
        ##
        # The relative position (in meters), resolved in the local ENU frame.
        #
        # @note
        # If a differential solution to the base station is not available, these
        # values will be `NAN`.
        ##
        self.relative_position_enu_m = np.full((3,), np.nan)
        ##
        # The position standard deviation (in meters), resolved with respect to the
        # local ENU tangent plane: east, north, up.
        #
        # @note
        # If a differential solution to the base station is not available, these
        # values will be `NAN`.
        ##
        self.position_std_enu_m = np.full((3,), np.nan)

        ##
        # The heading between the primary device antenna and the secondary (in degrees) with
        # respect to true north.
        #
        # @note
        # Reported in the range [0, 360).
        #
        ##
        self.heading_true_north_deg = np.nan

        ##
        # The estmated distance between primary and secondary antennas (in meters)
        #
        ##
        self.baseline_distance_m = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        initial_offset = offset
        if (buffer is None):
            buffer = bytearray(self.calcsize())
        buffer = self.timestamps.pack(buffer)
        offset += self.timestamps.calcsize()
        self._STRUCT.pack_into(buffer, offset,
            self.solution_type,
            self.flags,
            self.relative_position_enu_m[0],
            self.relative_position_enu_m[1],
            self.relative_position_enu_m[2],
            self.position_std_enu_m[0],
            self.position_std_enu_m[1],
            self.position_std_enu_m[2],
            self.heading_true_north_deg,
            self.baseline_distance_m)
        offset += self._STRUCT.size
        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)
        (solution_type_int,
            self.flags,
            self.relative_position_enu_m[0],
            self.relative_position_enu_m[1],
            self.relative_position_enu_m[2],
            self.position_std_enu_m[0],
            self.position_std_enu_m[1],
            self.position_std_enu_m[2],
            self.heading_true_north_deg,
            self.baseline_distance_m) = self._STRUCT.unpack_from(buffer, offset)
        offset += self._STRUCT.size
        self.solution_type = SolutionType(solution_type_int)
        return offset - initial_offset

    def __str__(self):
        return f"""\
HeadingMeasurement @ {str(self.timestamps.p1_time)}
  Solution Type: {str(self.solution_type)}
  Relative position (ENU) (m): {self.relative_position_enu_m[0]:.2f}, {self.relative_position_enu_m[1]:.2f}, {self.relative_position_enu_m[2]:.2f}
  Position std (ENU) (m): {self.position_std_enu_m[0]:.2f}, {self.position_std_enu_m[1]:.2f}, {self.position_std_enu_m[2]:.2f}
  Heading (deg): {self.heading_true_north_deg:.2f}
  Baseline distance (m): {self.baseline_distance_m:.2f}"""

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size + MeasurementTimestamps.calcsize()

    @classmethod
    def to_numpy(cls, messages: Sequence['HeadingMeasurement']):
        result = {
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
            'flags': np.array([int(m.flags) for m in messages], dtype=int),
            'relative_position_enu_m': np.array([m.relative_position_enu_m for m in messages]).T,
            'position_std_enu_m': np.array([m.position_std_enu_m for m in messages]).T,
            'heading_true_north_deg': np.array([float(m.heading_true_north_deg) for m in messages]),
            'baseline_distance_m': np.array([float(m.baseline_distance_m) for m in messages]),
        }
        result.update(MeasurementTimestamps.to_numpy([m.timestamps for m in messages]))
        return result
