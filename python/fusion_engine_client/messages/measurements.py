import struct
from typing import Sequence

from construct import Array, Struct, Padding, Float32l, Int16sl, Int32sl
import numpy as np

from .defs import *
from ..utils.construct_utils import FixedPointAdapter, construct_message_to_string
from ..utils.enum_utils import IntEnum

################################################################################
# IMU Measurements
################################################################################

class IMUInput(MessagePayload):
    """!
    @brief IMU sensor measurement input.
    """
    MESSAGE_TYPE = MessageType.IMU_INPUT
    MESSAGE_VERSION = 0

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        Padding(6),
        "temperature_degc" / FixedPointAdapter(2 ** -7, Int16sl, invalid=0x7FFF),
        "accel_mps2" / Array(3, FixedPointAdapter(2 ** -16, Int32sl, invalid=0x7FFFFFFF)),
        "gyro_rps" / Array(3, FixedPointAdapter(2 ** -20, Int32sl, invalid=0x7FFFFFFF)),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.temperature_degc = np.nan
        self.accel_mps2 = np.full((3,), np.nan)
        self.gyro_rps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']

        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'accel_mps2': np.array([m.accel_mps2 for m in messages]).T,
            'gyro_rps': np.array([m.gyro_rps for m in messages]).T,
            'temperature_degc': np.array([m.temperature_degc for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        else:
            return super().__getattr__(item)

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.Construct, title='IMU Input',
                                           fields=['details', 'accel_mps2', 'gyro_rps', 'temperature_degc'])

class IMUOutput(MessagePayload):
    """!
    @brief IMU sensor measurement data.
    """
    MESSAGE_TYPE = MessageType.IMU_OUTPUT
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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
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
        return 'IMU Output @ %s' % str(self.p1_time)

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'accel_mps2': np.array([m.accel_mps2 for m in messages]).T,
            'accel_std_mps2': np.array([m.accel_std_mps2 for m in messages]).T,
            'gyro_rps': np.array([m.gyro_rps for m in messages]).T,
            'gyro_std_rps': np.array([m.gyro_std_rps for m in messages]).T,
        }

        # For convenience and consistency with raw measurement messages, we artificially create the following fields
        # from MeasurementDetails:
        result['measurement_time_source'] = np.full_like(result['p1_time'], SystemTimeSource.P1_TIME)
        result['measurement_time'] = result['p1_time']  # No need to copy, reference is fine here.

        return result

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp.calcsize() + cls._STRUCT.size


class RawIMUOutput(MessagePayload):
    """!
    @brief Raw (uncorrected) IMU sensor measurement output.
    """
    MESSAGE_TYPE = MessageType.RAW_IMU_OUTPUT
    MESSAGE_VERSION = 0

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        Padding(6),
        "temperature_degc" / FixedPointAdapter(2 ** -7, Int16sl, invalid=0x7FFF),
        "accel_mps2" / Array(3, FixedPointAdapter(2 ** -16, Int32sl, invalid=0x7FFFFFFF)),
        "gyro_rps" / Array(3, FixedPointAdapter(2 ** -20, Int32sl, invalid=0x7FFFFFFF)),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.temperature_degc = np.nan
        self.accel_mps2 = np.full((3,), np.nan)
        self.gyro_rps = np.full((3,), np.nan)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']

        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'accel_mps2': np.array([m.accel_mps2 for m in messages]).T,
            'gyro_rps': np.array([m.gyro_rps for m in messages]).T,
            'temperature_degc': np.array([m.temperature_degc for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        else:
            return super().__getattr__(item)

    def __str__(self):
        return construct_message_to_string(message=self, construct=self.Construct, title='Raw IMU Output',
                                           fields=['details', 'accel_mps2', 'gyro_rps', 'temperature_degc'])

################################################################################
# Different Wheel Speed Measurements
################################################################################


class GearType(IntEnum):
  UNKNOWN = 0 ##< The transmission gear is not known, or does not map to a supported GearType.
  FORWARD = 1 ##< The vehicle is in a forward gear.
  REVERSE = 2 ##< The vehicle is in reverse.
  PARK = 3 ##< The vehicle is parked.
  NEUTRAL = 4 ##< The vehicle is in neutral.


class WheelSpeedInput(MessagePayload):
    """!
    @brief Differential wheel speed measurement input.
    """
    MESSAGE_TYPE = MessageType.WHEEL_SPEED_INPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        "front_left_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "front_right_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "rear_left_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "rear_right_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(2),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.gear = GearType.UNKNOWN
        self.flags = 0x0

        self.front_left_speed_mps = np.nan
        self.front_right_speed_mps = np.nan
        self.rear_left_speed_mps = np.nan
        self.rear_right_speed_mps = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']

        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed=[{self.front_left_speed_mps:.1f}, {self.front_right_speed_mps:.1f}, ' \
                  f'{self.rear_left_speed_mps:.1f}, {self.rear_right_speed_mps:.1f}] m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Speed Input @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Front left: {self.front_left_speed_mps:.2f} m/s
  Front right: {self.front_right_speed_mps:.2f} m/s
  Rear left: {self.rear_left_speed_mps:.2f} m/s
  Rear right: {self.rear_right_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'front_left_speed_mps': np.array([m.front_left_speed_mps for m in messages]),
            'front_right_speed_mps': np.array([m.front_right_speed_mps for m in messages]),
            'rear_left_speed_mps': np.array([m.rear_left_speed_mps for m in messages]),
            'rear_right_speed_mps': np.array([m.rear_right_speed_mps for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class WheelSpeedOutput(MessagePayload):
    """!
    @brief Differential wheel speed output with calibration and corrections applied.
    """
    MESSAGE_TYPE = MessageType.WHEEL_SPEED_OUTPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "data_source" / AutoEnum(Int8ul, SensorDataSource),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(1),
        "front_left_speed_mps" / Float32l,
        "front_right_speed_mps" / Float32l,
        "rear_left_speed_mps" / Float32l,
        "rear_right_speed_mps" / Float32l,
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.data_source = SensorDataSource.UNKNOWN
        self.gear = GearType.UNKNOWN
        self.flags = 0x0

        self.front_left_speed_mps = np.nan
        self.front_right_speed_mps = np.nan
        self.rear_left_speed_mps = np.nan
        self.rear_right_speed_mps = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed=[{self.front_left_speed_mps:.1f}, {self.front_right_speed_mps:.1f}, ' \
                  f'{self.rear_left_speed_mps:.1f}, {self.rear_right_speed_mps:.1f}] m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Speed Output @ {str(self.p1_time)}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Front left: {self.front_left_speed_mps:.2f} m/s
  Front right: {self.front_right_speed_mps:.2f} m/s
  Rear left: {self.rear_left_speed_mps:.2f} m/s
  Rear right: {self.rear_right_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'data_source': np.array([m.gear for m in messages], dtype=int),
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'front_left_speed_mps': np.array([m.front_left_speed_mps for m in messages]),
            'front_right_speed_mps': np.array([m.front_right_speed_mps for m in messages]),
            'rear_left_speed_mps': np.array([m.rear_left_speed_mps for m in messages]),
            'rear_right_speed_mps': np.array([m.rear_right_speed_mps for m in messages]),
        }

        # For convenience and consistency with raw measurement messages, we artificially create the following fields
        # from MeasurementDetails:
        result['measurement_time_source'] = np.full_like(result['p1_time'], SystemTimeSource.P1_TIME)
        result['measurement_time'] = result['p1_time']  # No need to copy, reference is fine here.

        return result


class RawWheelSpeedOutput(MessagePayload):
    """!
    @brief Raw (uncorrected) dfferential wheel speed measurement output
    """
    MESSAGE_TYPE = MessageType.RAW_WHEEL_SPEED_OUTPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        "front_left_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "front_right_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "rear_left_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "rear_right_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(2),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.gear = GearType.UNKNOWN
        self.flags = 0x0

        self.front_left_speed_mps = np.nan
        self.front_right_speed_mps = np.nan
        self.rear_left_speed_mps = np.nan
        self.rear_right_speed_mps = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']

        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed=[{self.front_left_speed_mps:.1f}, {self.front_right_speed_mps:.1f}, ' \
                  f'{self.rear_left_speed_mps:.1f}, {self.rear_right_speed_mps:.1f}] m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Raw Wheel Speed Output @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Front left: {self.front_left_speed_mps:.2f} m/s
  Front right: {self.front_right_speed_mps:.2f} m/s
  Rear left: {self.rear_left_speed_mps:.2f} m/s
  Rear right: {self.rear_right_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'front_left_speed_mps': np.array([m.front_left_speed_mps for m in messages]),
            'front_right_speed_mps': np.array([m.front_right_speed_mps for m in messages]),
            'rear_left_speed_mps': np.array([m.rear_left_speed_mps for m in messages]),
            'rear_right_speed_mps': np.array([m.rear_right_speed_mps for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result

################################################################################
# Vehicle Speed Measurements
################################################################################


class VehicleSpeedInput(MessagePayload):
    """!
    @brief Vehicle body speed measurement input.
    """
    MESSAGE_TYPE = MessageType.VEHICLE_SPEED_INPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        "vehicle_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(2),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.gear = GearType.UNKNOWN
        self.flags = 0x0
        self.vehicle_speed = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']

        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed={self.vehicle_speed_mps:.1f} m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Speed Input @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Speed: {self.vehicle_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'vehicle_speed_mps': np.array([m.vehicle_speed_mps for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class VehicleSpeedOutput(MessagePayload):
    """!
    @brief Vehicle body speed measurement output with calibration and corrections applied.
    """
    MESSAGE_TYPE = MessageType.VEHICLE_SPEED_OUTPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "p1_time" / TimestampConstruct,
        "data_source" / AutoEnum(Int8ul, SensorDataSource),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(1),
        "vehicle_speed_mps" / Float32l,
    )

    def __init__(self):
        self.p1_time = Timestamp()
        self.data_source = SensorDataSource.UNKNOWN
        self.gear = GearType.UNKNOWN
        self.flags = 0x0

        self.vehicle_speed_mps = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed={self.vehicle_speed_mps:.1f} m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Speed Output @ {str(self.p1_time)}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Speed: {self.vehicle_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'p1_time': np.array([float(m.p1_time) for m in messages]),
            'data_source': np.array([m.gear for m in messages], dtype=int),
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'vehicle_speed_mps': np.array([m.vehicle_speed_mps for m in messages]),
        }

        # For convenience and consistency with raw measurement messages, we artificially create the following fields
        # from MeasurementDetails:
        result['measurement_time_source'] = np.full_like(result['p1_time'], SystemTimeSource.P1_TIME)
        result['measurement_time'] = result['p1_time']  # No need to copy, reference is fine here.

        return result


class RawVehicleSpeedOutput(MessagePayload):
    """!
    @brief Raw (uncorrected) vehicle body speed measurement output.
    """
    MESSAGE_TYPE = MessageType.RAW_VEHICLE_SPEED_OUTPUT
    MESSAGE_VERSION = 0

    FLAG_SIGNED = 0x1

    Construct = Struct(
        "details" / MeasurementDetailsConstruct,
        "vehicle_speed_mps" / FixedPointAdapter(2 ** -10, Int32sl, invalid=0x7FFFFFFF),
        "gear" / AutoEnum(Int8ul, GearType),
        "flags" / Int8ul,
        Padding(2),
    )

    def __init__(self):
        self.details = MeasurementDetails()
        self.gear = GearType.UNKNOWN
        self.flags = 0x0
        self.vehicle_speed = np.nan

    def is_signed(self) -> bool:
        return (self.flags & self.FLAG_SIGNED) != 0

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        values = dict(self.__dict__)
        packed_data = self.Construct.build(values)
        return PackedDataToBuffer(packed_data, buffer, offset, return_buffer)

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        parsed = self.Construct.parse(buffer[offset:])
        self.__dict__.update(parsed)
        del self.__dict__['_io']
        return parsed._io.tell()

    @classmethod
    def calcsize(cls) -> int:
        return cls.Construct.sizeof()

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        elif item == 'is_signed':
            return self.is_signed()
        else:
            return super().__getattr__(item)

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', gear={self.gear}, speed={self.vehicle_speed_mps:.1f} m/s]'
        return result

    def __str__(self):
        newline = '\n'
        return f"""\
Raw Vehicle Speed Output @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {self.gear.to_string(include_value=True)}
  Type: {'signed' if self.is_signed() else 'unsigned'}
  Speed: {self.vehicle_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'gear': np.array([m.gear for m in messages], dtype=int),
            'is_signed': np.array([m.is_signed() for m in messages], dtype=bool),
            'vehicle_speed_mps': np.array([m.vehicle_speed_mps for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result

################################################################################
# Wheel Tick Measurements
################################################################################


class WheelTickInput(MessagePayload):
    """!
    @brief Differential wheel encoder tick input.
    """
    MESSAGE_TYPE = MessageType.WHEEL_TICK_INPUT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<4I B 3x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

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

        offset += self.details.pack(buffer, offset, return_buffer=False)

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)
        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

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
        return MeasurementDetails.calcsize() + cls._STRUCT.size

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Tick Input @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {GearType(self.gear).to_string()}
  Front left: {self.front_left_wheel_ticks}
  Front right: {self.front_right_wheel_ticks}
  Rear left: {self.rear_left_wheel_ticks}
  Rear right: {self.rear_right_wheel_ticks}"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'front_left_wheel_ticks': np.array([m.front_left_wheel_ticks for m in messages], dtype=np.uint32),
            'front_right_wheel_ticks': np.array([m.front_right_wheel_ticks for m in messages], dtype=np.uint32),
            'rear_left_wheel_ticks': np.array([m.rear_left_wheel_ticks for m in messages], dtype=np.uint32),
            'rear_right_wheel_ticks': np.array([m.rear_right_wheel_ticks for m in messages], dtype=np.uint32),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class RawWheelTickOutput(WheelTickInput):
    MESSAGE_TYPE = MessageType.RAW_WHEEL_TICK_OUTPUT
    MESSAGE_VERSION = 0

    def __str__(self):
        return super().__str__().replace('Wheel Tick Input', 'Raw Wheel Tick Output')

################################################################################
# Vehicle Tick Measurements
################################################################################


class VehicleTickInput(MessagePayload):
    """!
    @brief Singular wheel encoder tick input, representing vehicle body speed.
    """
    MESSAGE_TYPE = MessageType.VEHICLE_TICK_INPUT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<I B 3x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

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

        offset += self.details.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.tick_count,
            int(self.gear))

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)
        # Disregard any user-specified P1 timestamps in input data.
        self.details.p1_time = Timestamp()

        (self.tick_count,
         gear_int) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementDetails.calcsize() + cls._STRUCT.size

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        else:
            return super().__getattr__(item)

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Tick Input @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {GearType(self.gear).to_string()}
  Ticks: {self.tick_count}"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'tick_count': np.array([m.tick_count for m in messages], dtype=np.uint32),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class RawVehicleTickOutput(VehicleTickInput):
    MESSAGE_TYPE = MessageType.RAW_VEHICLE_TICK_OUTPUT
    MESSAGE_VERSION = 0

    def __str__(self):
        return super().__str__().replace('Vehicle Tick Input', 'Raw Vehicle Tick Output')

################################################################################
# Deprecated Speed Measurement Definitions
################################################################################


class DeprecatedWheelSpeedMeasurement(MessagePayload):
    """!
    @brief (Deprecated) Differential wheel speed measurement.
    """
    MESSAGE_TYPE = MessageType.DEPRECATED_WHEEL_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<4f B ? 2x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

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

        offset += self.details.pack(buffer, offset, return_buffer=False)

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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)

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
        return MeasurementDetails.calcsize() + cls._STRUCT.size

    def __getattr__(self, item):
        if item == 'p1_time':
            return self.details.p1_time
        else:
            return super().__getattr__(item)

    def __str__(self):
        newline = '\n'
        return f"""\
Wheel Speed Measurement @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {GearType(self.gear).to_string()}
  Type: {'signed' if self.is_signed else 'unsigned'}
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
            'is_signed': np.array([m.is_signed for m in messages], dtype=int),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class DeprecatedVehicleSpeedMeasurement(MessagePayload):
    """!
    @brief (Deprecated) Vehicle body speed measurement.
    """
    MESSAGE_TYPE = MessageType.DEPRECATED_VEHICLE_SPEED_MEASUREMENT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<f B ? 2x')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

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

        offset += self.details.pack(buffer, offset, return_buffer=False)

        offset += self.pack_values(
            self._STRUCT, buffer, offset,
            self.vehicle_speed_mps,
            int(self.gear),
            self.is_signed)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)

        (self.vehicle_speed_mps,
         gear_int,
         self.is_signed) = \
            self._STRUCT.unpack_from(buffer=buffer, offset=offset)
        offset += self._STRUCT.size

        self.gear = GearType(gear_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return MeasurementDetails.calcsize() + cls._STRUCT.size

    def __str__(self):
        newline = '\n'
        return f"""\
Vehicle Speed Measurement @ {str(self.details.p1_time)}
  {str(self.details).replace(newline, newline + '  ')}
  Gear: {GearType(self.gear).to_string()}
  Type: {'signed' if self.is_signed else 'unsigned'}
  Speed: {self.vehicle_speed_mps:.2f} m/s"""

    @classmethod
    def to_numpy(cls, messages):
        result = {
            'vehicle_speed_mps': np.array([m.vehicle_speed_mps for m in messages]),
            'is_signed': np.array([m.is_signed for m in messages], dtype=bool),
            'gear': np.array([m.gear for m in messages], dtype=int),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result

################################################################################
# Heading Sensor Definitions
################################################################################


class HeadingOutput(MessagePayload):
    """!
     @brief Corrected heading sensor measurement output.
    """
    MESSAGE_TYPE = MessageType.HEADING_OUTPUT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<B3xL3ff')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

        ## Set to @ref SolutionType::RTKFixed when heading is available, or @ref SolutionType::Invalid otherwise.
        self.solution_type = SolutionType.Invalid
        ## A bitmask of flags associated with the solution
        self.flags = 0
        ## The measured YPR vector (in degrees), resolved in the ENU frame.
        self.ypr_deg = np.full((3,), np.nan)

        ##
        # The corrected heading between the primary device antenna and the secondary (in degrees) with
        # respect to true north.
        #
        # @note
        # Reported in the range [0, 360).
        self.heading_true_north_deg = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        buffer = self.details.pack(buffer)
        offset += self.details.calcsize()

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.solution_type),
            self.flags,
            self.ypr_deg[0],
            self.ypr_deg[1],
            self.ypr_deg[2],
            self.heading_true_north_deg)
        offset += self._STRUCT.size

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)

        (solution_type_int,
         self.flags,
         self.ypr_deg[0],
         self.ypr_deg[1],
         self.ypr_deg[2],
         self.heading_true_north_deg) = self._STRUCT.unpack_from(buffer, offset)
        offset += self._STRUCT.size

        self.solution_type = SolutionType(solution_type_int)

        return offset - initial_offset

    def __repr__(self):
        result = super().__repr__()[:-1]
        ypr_str = ['%.1f' % v for v in self.ypr_deg]
        result += f', solution_type={self.solution_type}, ypr=[{ypr_str}] deg]'
        return result

    def __str__(self):
        return f"""\
Heading Output @ {str(self.details.p1_time)}
  Solution Type: {self.solution_type}
  YPR (ENU) (deg): {self.ypr_deg[0]:.2f}, {self.ypr_deg[1]:.2f}, {self.ypr_deg[2]:.2f}
  Heading (deg): {self.heading_true_north_deg:.2f}
  """

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size + MeasurementDetails.calcsize()

    @classmethod
    def to_numpy(cls, messages: Sequence['HeadingOutput']):
        result = {
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
            'flags': np.array([int(m.flags) for m in messages], dtype=np.uint32),
            'ypr_deg': np.array([m.ypr_deg for m in messages]).T,
            'heading_true_north_deg': np.array([m.heading_true_north_deg for m in messages], dtype=float).T,
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result


class RawHeadingOutput(MessagePayload):
    """!
     @brief Raw (uncorrected) heading sensor measurement output.
    """
    MESSAGE_TYPE = MessageType.RAW_HEADING_OUTPUT
    MESSAGE_VERSION = 0

    _STRUCT = struct.Struct('<B3xL3f3fff')

    def __init__(self):
        ## Measurement timestamps, if available. See @ref measurement_messages.
        self.details = MeasurementDetails()

        ## Set to @ref SolutionType::RTKFixed when heading is available, or @ref SolutionType::Invalid otherwise.
        self.solution_type = SolutionType.Invalid
        ## A bitmask of flags associated with the solution.
        self.flags = 0

        ##
        # The position of the secondary GNSS antenna relative to the primary antenna (in meters), resolved with respect
        # to the local ENU tangent plane: east, north, up.
        self.relative_position_enu_m = np.full((3,), np.nan)
        ##
        # The position standard deviation (in meters), resolved with respect to the
        # local ENU tangent plane: east, north, up.
        self.position_std_enu_m = np.full((3,), np.nan)

        ##
        # The heading between the primary device antenna and the secondary (in degrees) with
        # respect to true north.
        #
        # @note
        # Reported in the range [0, 360).
        self.heading_true_north_deg = np.nan

        ##
        # The estimated distance between primary and secondary antennas (in meters).
        self.baseline_distance_m = np.nan

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        buffer = self.details.pack(buffer)
        offset += self.details.calcsize()

        self._STRUCT.pack_into(
            buffer, offset,
            int(self.solution_type),
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

    def unpack(self, buffer: bytes, offset: int = 0, message_version: int = MessagePayload._UNSPECIFIED_VERSION) -> int:
        initial_offset = offset

        offset += self.details.unpack(buffer, offset)

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

    def __repr__(self):
        result = super().__repr__()[:-1]
        result += f', solution_type={self.solution_type}, heading={self.heading_true_north_deg:.1f} deg, ' \
                  f'baseline={self.baseline_distance_m} m]'
        return result

    def __str__(self):
        return f"""\
Raw Heading Output @ {str(self.details.p1_time)}
  Solution Type: {self.solution_type}
  Relative position (ENU) (m): {self.relative_position_enu_m[0]:.2f}, {self.relative_position_enu_m[1]:.2f}, {self.relative_position_enu_m[2]:.2f}
  Position std (ENU) (m): {self.position_std_enu_m[0]:.2f}, {self.position_std_enu_m[1]:.2f}, {self.position_std_enu_m[2]:.2f}
  Heading (deg): {self.heading_true_north_deg:.2f}
  Baseline distance (m): {self.baseline_distance_m:.2f}"""

    @classmethod
    def calcsize(cls) -> int:
        return cls._STRUCT.size + MeasurementDetails.calcsize()

    @classmethod
    def to_numpy(cls, messages: Sequence['RawHeadingOutput']):
        result = {
            'solution_type': np.array([int(m.solution_type) for m in messages], dtype=int),
            'flags': np.array([int(m.flags) for m in messages], dtype=np.uint32),
            'relative_position_enu_m': np.array([m.relative_position_enu_m for m in messages]).T,
            'position_std_enu_m': np.array([m.position_std_enu_m for m in messages]).T,
            'heading_true_north_deg': np.array([float(m.heading_true_north_deg) for m in messages]),
            'baseline_distance_m': np.array([float(m.baseline_distance_m) for m in messages]),
        }
        result.update(MeasurementDetails.to_numpy([m.details for m in messages]))
        return result
