from datetime import datetime, timedelta, timezone
import math
import struct

from construct import Adapter, Struct, Int32ul


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


def system_time_to_str(system_time_ns):
    system_time_sec = system_time_ns * 1e-9
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
