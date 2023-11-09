import struct

from construct import Adapter, Struct, Int8ul, Padding
import numpy as np

from .timestamp import Timestamp, TimestampConstruct
from ..utils.construct_utils import AutoEnum, ClassAdapter
from ..utils.enum_utils import IntEnum


class SensorDataSource(IntEnum):
    """!
    @brief The source of received sensor measurements, if known.
    """
    ## Data source not known.
    UNKNOWN = 0
    ## Sensor data captured internal to the device (embedded IMU, GNSS receiver, etc.).
    INTERNAL = 1
    ## Sensor data generated via hardware voltage signal (wheel tick, external event, etc.).
    HARDWARE_IO = 2
    ## Sensor data captured from a vehicle CAN bus.
    CAN = 3
    ## Sensor data provided over a serial connection.
    SERIAL = 4
    ## Sensor data provided over a network connection.
    NETWORK = 5


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
    ## Message timestamped in GPS time, referenced to 1980/1/6.
    GPS_TIME = 4


class MeasurementDetails(object):
    """!
    @brief The time of applicability and additional information for an incoming sensor measurement.
    """
    Construct = Struct(
        "measurement_time" / TimestampConstruct,
        "measurement_time_source" / AutoEnum(Int8ul, SystemTimeSource),
        "data_source" / AutoEnum(Int8ul, SensorDataSource),
        Padding(2),
        "p1_time" / TimestampConstruct,
    )

    _STRUCT = struct.Struct('<BB2x')

    def __init__(self):
        self.measurement_time = Timestamp()
        self.measurement_time_source = SystemTimeSource.INVALID
        self.data_source = SensorDataSource.UNKNOWN
        self.p1_time = Timestamp()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.measurement_time.pack(buffer, offset, return_buffer=False)
        self._STRUCT.pack_into(buffer, offset, int(self.measurement_time_source), int(self.data_source))
        offset += self._STRUCT.size
        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.measurement_time.unpack(buffer, offset)
        (measurement_time_source_int, data_source_int) = self._STRUCT.unpack_from(buffer, offset)
        offset += self._STRUCT.size
        offset += self.p1_time.unpack(buffer, offset)

        self.measurement_time_source = SystemTimeSource(measurement_time_source_int)
        self.data_source = SensorDataSource(data_source_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + cls._STRUCT.size

    def __str__(self):
        if self.measurement_time_source == SystemTimeSource.P1_TIME or \
            self.measurement_time_source == SystemTimeSource.GPS_TIME:
            measurement_time_str = str(self.measurement_time)
        else:
            measurement_time_str = 'System: %.3f sec' % self.measurement_time
        string = f'Measurement time: {measurement_time_str} ' \
                 f'(source: {self.measurement_time_source.to_string()})\n'
        if self.measurement_time_source != SystemTimeSource.P1_TIME:
            string += f'P1 time: {str(self.p1_time)}\n'
        string += f'Data source: {str(self.data_source)}'
        return string

    @classmethod
    def to_numpy(cls, messages):
        time_source = np.array([int(m.measurement_time_source) for m in messages], dtype=int)
        data_source = np.array([int(m.data_source) for m in messages], dtype=int)
        measurement_time = np.array([float(m.measurement_time) for m in messages])

        # If the p1_time field is not set _and_ the incoming measurement time source is explicitly set to P1 time (i.e.,
        # the data provider is synchronized to P1 time), use the measurement_time value. Note that we always prefer the
        # p1_time value if it is present -- the value in measurement_time may be adjusted internally by the device, and
        # the adjusted result will be stored in p1_time (measurement_time will never be modified).
        p1_time = np.array([float(m.p1_time) for m in messages])
        idx = np.logical_and(time_source == SystemTimeSource.P1_TIME, np.isnan(p1_time))
        p1_time[idx] = measurement_time[idx]

        result = {
            'measurement_time': measurement_time,
            'measurement_time_source': time_source,
            'data_source': data_source,
            'p1_time': p1_time,
        }

        idx = time_source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION
        if np.any(idx):
            system_time = np.full_like(time_source, np.nan)
            system_time[idx] = measurement_time[idx]
            result['system_time'] = system_time

        return result


MeasurementDetailsConstruct = ClassAdapter(MeasurementDetails, MeasurementDetails.Construct)
