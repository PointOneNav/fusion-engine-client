from typing import Union

from datetime import datetime, timedelta, timezone
import math
import struct

from construct import Adapter, Struct, Int32ul
from gpstime import gpstime
import numpy as np


SECONDS_PER_WEEK = 7 * 24 * 3600.0

GPS_POSIX_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)
GPS_POSIX_EPOCH_SEC = GPS_POSIX_EPOCH.timestamp()

# 2000/1/1 00:00:00
#
# Used to distinguish between:
# - P1 timestamps (0 at time of boot) vs GPS timestamps (referenced to 1/6/1980)
# - System CPU/MCU monotonic timestamps (0 at time of boot) vs POSIX timestamps (referenced to 1/1/1970)
Y2K_POSIX_SEC = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
Y2K_GPS_SEC = (Y2K_POSIX_SEC - GPS_POSIX_EPOCH_SEC) + 13


def datetime_to_string(time: datetime, decimals=3) -> str:
    if time is None:
        return 'None'
    else:
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        if decimals > 0:
            time_str += (('%%.0%df' % decimals) % (time.microsecond * 1e-6))[1:]
        return time_str


def is_gps_time(value_sec: Union[float, np.ndarray]) -> Union[bool, np.ndarray]:
    """!
    @brief Test if a timestamp (or list of timestamps) is large enough to be presumed a GPS time (>2000/1/1).

    @param value_sec A timestamp or `ndarray` array of timestamps (in seconds).

    @return `True` if the timestamp appears to be a GPS timestamp.
    """
    # Note: We're assuming no Point One device will ever operate before 2000/1/1, even in simulation, and that no
    # device will be running for 20 years continuously and have a P1 time > (2000 - 1980) seconds.
    return value_sec >= Y2K_GPS_SEC


class Timestamp:
    _INVALID = 0xFFFFFFFF

    _FORMAT = '<II'
    _SIZE: int = struct.calcsize(_FORMAT)

    def __init__(self, time_sec=math.nan):
        self.seconds = float(time_sec)

    def is_gps(self) -> bool:
        return is_gps_time(self.seconds)

    def as_gps(self) -> datetime:
        if self.is_gps():
            return GPS_POSIX_EPOCH + timedelta(seconds=self.seconds)
        else:
            return None

    def as_utc(self) -> datetime:
        if self.is_gps():
            return gpstime.fromgps(self.seconds)
        else:
            return None

    def get_week_tow(self) -> (int, float):
        if self.is_gps():
            week = int(self.seconds / SECONDS_PER_WEEK)
            tow_sec = self.seconds - week * SECONDS_PER_WEEK
            return week, tow_sec
        else:
            return np.nan, np.nan

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

    def __add__(self, other):
        return Timestamp(self.seconds + float(other))

    def __sub__(self, other):
        return Timestamp(self.seconds - float(other))

    def __iadd__(self, other):
        self.seconds += float(other)
        return self

    def __isub(self, other):
        self.seconds -= float(other)
        return self

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
        if self.is_gps():
            return 'GPS: %d:%.3f (%.3f sec)' % (*self.get_week_tow(), self.seconds)
        else:
            return 'P1: %.3f sec' % self.seconds


def system_time_to_str(system_time, is_seconds=False):
    if system_time is None:
        return 'None'

    if is_seconds:
        system_time_sec = system_time
    else:
        system_time_sec = system_time * 1e-9

    # Note: We're assuming no Point One device will ever operate before 2000/1/1, even in simulation, and that no
    # device will be running for 30 years continuously and have a system time > (2000 - 1970) seconds.
    if system_time_sec >= Y2K_POSIX_SEC:
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
