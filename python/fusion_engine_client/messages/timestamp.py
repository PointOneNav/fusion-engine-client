from datetime import datetime, timedelta, timezone
import math
import struct

from construct import Adapter, Struct, Int32ul
import numpy as np

from ..utils.enum_utils import IntEnum


class Timestamp:
    _INVALID = 0xFFFFFFFF

    _FORMAT = '<II'
    _SIZE: int = struct.calcsize(_FORMAT)

    _GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)

    def __init__(self, time_sec=math.nan):
        self.seconds = float(time_sec)

    def as_gps(self) -> datetime:
        if math.isnan(self.seconds):
            return None
        else:
            return Timestamp._GPS_EPOCH + timedelta(seconds=self.seconds)

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = False) -> (bytes, int):
        if math.isnan(self.seconds):
            int_part = Timestamp._INVALID
            frac_part_ns = Timestamp._INVALID
        else:
            int_part = int(self.seconds)
            frac_part_ns = int((self.seconds - int_part) * 1e9)

        if buffer is None:
            buffer = struct.pack(Timestamp._FORMAT, int_part, frac_part_ns)
        else:
            args = (int_part, frac_part_ns)
            struct.pack_into(Timestamp._FORMAT, buffer, offset, *args)

        if return_buffer:
            return buffer
        else:
            return self.calcsize()

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        (int_part, frac_part_ns) = struct.unpack_from(Timestamp._FORMAT, buffer, offset)
        if int_part == Timestamp._INVALID or frac_part_ns == Timestamp._INVALID:
            self.seconds = math.nan
        else:
            self.seconds = int_part + (frac_part_ns * 1e-9)
        return Timestamp._SIZE

    @classmethod
    def calcsize(cls) -> int:
        return Timestamp._SIZE

    def __eq__(self, other):
        return self.seconds == float(other)

    def __ne__(self, other):
        return self.seconds != float(other)

    def __lt__(self, other):
        return self.seconds < float(other)

    def __le__(self, other):
        return self.seconds <= float(other)

    def __gt__(self, other):
        return self.seconds > float(other)

    def __ge__(self, other):
        return self.seconds >= float(other)

    def __bool__(self):
        return not math.isnan(self.seconds)

    def __float__(self):
        return self.seconds

    def __str__(self):
        return 'P1 time %.3f sec' % self.seconds


def system_time_to_str(system_time, is_seconds=False):
    if is_seconds:
        system_time_sec = system_time
    else:
        system_time_sec = system_time * 1e-9

    if system_time_sec >= 946684800: # 2000/1/1 00:00:00
        return 'POSIX time %s (%.3f sec)' % \
               (datetime.utcfromtimestamp(system_time_sec).replace(tzinfo=timezone.utc), system_time_sec)
    else:
        return 'System time %.3f sec' % system_time_sec


TimestampRawConstruct = Struct(
    "int_part" / Int32ul,
    "frac_part_ns" / Int32ul,
)


class TimestampAdapter(Adapter):
    """!
    @brief Adapter for automatically converting between construct streams and
           Timestamp.
    """

    def __init__(self, *args):
        super().__init__(*args)

    def _decode(self, obj, context, path):
        # skip _io member
        if obj.int_part == Timestamp._INVALID or obj.frac_part_ns == Timestamp._INVALID:
           seconds = math.nan
        else:
            seconds = obj.int_part + (obj.frac_part_ns * 1e-9)
        return Timestamp(seconds)

    def _encode(self, obj, context, path):
        if math.isnan(obj.seconds):
            int_part = Timestamp._INVALID
            frac_part_ns = Timestamp._INVALID
        else:
            int_part = int(obj.seconds)
            frac_part_ns = int((obj.seconds - int_part) * 1e9)
        return {'int_part': int_part, 'frac_part_ns': frac_part_ns}


TimestampConstruct = TimestampAdapter(TimestampRawConstruct)


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


class MeasurementTimestamps(object):
    """!
    @brief The time of applicability for an incoming sensor measurement.

    By convention this will be the first member of any measurement definition intended to be externally sent by the user
    to the device.

    The @ref measurement_time field stores time of applicability/reception for the measurement data, expressed in one of
    the available source time bases (see @ref SystemTimeSource). The timestamp will be converted to P1 time
    automatically by FusionEngine using an internal model of P1 vs source time. The converted value will be assigned to
    @ref p1_time for usage and logging purposes.

    On most platforms, incoming sensor measurements are timestamped automatically by FusionEngine when they arrive. To
    request timestamp on arrival, set @ref measurement_time to invalid, and set the @ref measurement_time_source to
    @ref SystemTimeSource::INVALID.

    On some platforms, incoming sensor measurements may be timestamped externally by the user prior to arrival, either
    in GPS time (@ref SystemTimeSource::GPS_TIME), or using a monotonic clock controlled by the user system (@ref
    SystemTimeSource::SENDER_SYSTEM_TIME).

    @note
    Use of an external monotonic clock requires additional coordination with the target FusionEngine device.

    Measurements may only be timestamped externally using P1 time (@ref SystemTimeSource::P1_TIME) if the external
    system supports remote synchronization of the P1 time clock model.
    """
    _STRUCT = struct.Struct('<B3x')

    def __init__(self):
        self.measurement_time = Timestamp()
        self.measurement_time_source = SystemTimeSource.INVALID
        self.p1_time = Timestamp()

    def pack(self, buffer: bytes = None, offset: int = 0, return_buffer: bool = True) -> (bytes, int):
        if buffer is None:
            buffer = bytearray(self.calcsize())

        initial_offset = offset

        offset += self.measurement_time.pack(buffer, offset, return_buffer=False)
        self._STRUCT.pack_into(buffer, offset, int(self.measurement_time_source))
        offset += self._STRUCT.size
        offset += self.p1_time.pack(buffer, offset, return_buffer=False)

        if return_buffer:
            return buffer
        else:
            return offset - initial_offset

    def unpack(self, buffer: bytes, offset: int = 0) -> int:
        initial_offset = offset

        offset += self.measurement_time.unpack(buffer, offset)
        (measurement_time_source_int,) = self._STRUCT.unpack_from(buffer, offset)
        offset += self._STRUCT.size
        offset += self.p1_time.unpack(buffer, offset)

        self.measurement_time_source = SystemTimeSource(measurement_time_source_int)

        return offset - initial_offset

    @classmethod
    def calcsize(cls) -> int:
        return 2 * Timestamp.calcsize() + cls._STRUCT.size

    def __str__(self):
        string = f'Measurement time: {str(self.measurement_time)} (source: {str(self.measurement_time_source)})\n'
        string += f'P1 time: {str(self.p1_time)}'
        return string

    @classmethod
    def to_numpy(cls, messages):
        source = np.array([int(m.measurement_time_source) for m in messages], dtype=int)
        measurement_time = np.array([float(m.measurement_time) for m in messages])

        # If the p1_time field is not set _and_ the incoming measurement time source is explicitly set to P1 time (i.e.,
        # the data provider is synchronized to P1 time), use the measurement_time value. Note that we always prefer the
        # p1_time value if it is present -- the value in measurement_time may be adjusted internally by the device, and
        # the adjusted result will be stored in p1_time (measurement_time will never be modified).
        p1_time = np.array([float(m.p1_time) for m in messages])
        idx = np.logical_and(source == SystemTimeSource.P1_TIME, np.isnan(p1_time))
        p1_time[idx] = measurement_time[idx]

        result = {
            'measurement_time': measurement_time,
            'measurement_time_source': source,
            'p1_time': p1_time,
        }

        idx = source == SystemTimeSource.TIMESTAMPED_ON_RECEPTION
        if np.any(idx):
            system_time = np.full_like(source, np.nan)
            system_time[idx] = measurement_time[idx]
            result['system_time'] = system_time

        return result
