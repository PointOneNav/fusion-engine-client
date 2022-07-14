import struct

import numpy as np

from .defs import *
from ..utils.enum_utils import IntEnum


class SystemTimeSource(IntEnum):
    """!
    @brief The source of a @ref point_one::fusion_engine::messages::Timestamp used to represent the time of
           applicability of an incoming sensor measurement.
    """
    ## Timestamp not valid.
    INVALID = 0
    ## Message timestamped in P1 time.
    P1_TIME = 1
    ## Message timestamped in system time, generated when received by the device.
    TIMESTAMPED_ON_RECEPTION = 2
    ## Message timestamp was generated from a monotonic clock of an external system.
    SENDER_SYSTEM_TIME = 3


class MeasurementTimestamps(object):
    """!
    @brief The time of applicability for an incoming sensor measurement.

    By convention this will be the first member of any measurement definition intended to be externally sent by the user
    to the device. On most platforms, incoming sensor measurements are timestamped by the device when they arrive. On
    some platforms, incoming sensor measurements may be timestamped externally by the user prior to arrival.
    """
    _STRUCT = struct.Struct('<B3x')

    def __init__(self):
        self.measurement_time = Timestamp()
        self.measurement_time_source = SystemTimeSource.INVALID
        self.gps_time = Timestamp()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.measurement_time.pack(buffer, offset, return_buffer=False)
        self._STRUCT.pack_into(buffer, offset, int(self.measurement_time_source))
        offset += self._STRUCT.size
        offset += self.gps_time.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.measurement_time.unpack(buffer, offset)
        (measurement_time_source_int,) = self._STRUCT.unpack_from(buffer, offset)
        offset += self._STRUCT.size
        offset += self.gps_time.unpack(buffer, offset)

        self.measurement_time_source = SystemTimeSource(measurement_time_source_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + cls._STRUCT.size

    def __str__(self):
        string = f'Measurement time: {str(self.measurement_time)} (source: {str(self.measurement_time_source)})\n'
        string += f'GPS time: {str(self.gps_time)}'
        return string

    @classmethod
    def to_numpy(cls, messages):
        source = np.array([int(m.measurement_time_source) for m in messages], dtype=int)
        measurement_time = np.array([float(m.p1_time) for m in messages])

        result = {
            'source': source,
            'measurement_time': measurement_time,
        }

        idx = source == SystemTimeSource.P1_TIME
        if np.any(idx):
            p1_time = np.full_like(source, np.nan)
            p1_time[idx] = measurement_time[idx]
            result['p1_time'] = p1_time

        idx = source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION
        if np.any(idx):
            system_time = np.full_like(source, np.nan)
            system_time[idx] = measurement_time[idx]
            result['system_time'] = system_time

        return result


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
    """
    MESSAGE_TYPE = MessageType.WHEEL_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<4f B 3x')

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

        ## The transmission gear currently in use (if available).
        self.gear = GearType.UNKNOWN

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
            int(self.gear))

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
         gear_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Speed Measurement @ {str(self.p1_time)}
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
    """
    MESSAGE_TYPE = MessageType.VEHICLE_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<f B 3x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.timestamps = MeasurementTimestamps()

        ## The current vehicle speed estimate (in m/s).
        self.vehicle_speed_mps = np.nan

        ## The transmission gear currently in use (if available).
        self.gear = GearType.UNKNOWN

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.timestamps.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.vehicle_speed_mps,
            int(self.gear))

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.timestamps.unpack(buffer, offset)

        (self.vehicle_speed_mps,
         gear_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementTimestamps.calcsize() + cls._STRUCT.size

    def __repr__(self):
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Speed Measurement @ {str(self.p1_time)}
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

        ## The transmission gear currently in use (if available).
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
        return '%s @ %s' % (self.MESSAGE_TYPE.name, self.p1_time)

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Tick Measurement @ {str(self.p1_time)}
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
