from datetime import datetime, timedelta, timezone
import math
import struct

from gpstime import gpstime
import pytest

from fusion_engine_client.messages.timestamp import (
    GPS_POSIX_EPOCH,
    SECONDS_PER_WEEK,
    Timestamp,
    Y2K_GPS_SEC,
    is_gps_time,
)

# GPS time for 2026/4/29 08:00:00 UTC — same reference used in test_time_provider.py.
GPS_DATE_SEC = 1461484818.0

GPS_DATE_WEEK = int(GPS_DATE_SEC / SECONDS_PER_WEEK)
GPS_DATE_TOW = GPS_DATE_SEC - GPS_DATE_WEEK * SECONDS_PER_WEEK


class TestConstruction:
    def test_default_is_invalid(self):
        assert not Timestamp()

    def test_nan_is_invalid(self):
        assert not Timestamp(math.nan)

    def test_zero_is_valid(self):
        assert Timestamp(0.0)

    def test_positive_is_valid(self):
        assert Timestamp(10.0)

    def test_stores_seconds(self):
        assert float(Timestamp(10.5)) == pytest.approx(10.5)

    def test_fractional_seconds_preserved(self):
        assert float(Timestamp(123.456789)) == pytest.approx(123.456789)


class TestIsValid:
    def test_default_invalid(self):
        assert not Timestamp().is_valid()

    def test_valid_timestamp(self):
        assert Timestamp(10.0).is_valid()

    def test_bool_false_for_invalid(self):
        assert bool(Timestamp()) is False

    def test_bool_true_for_valid(self):
        assert bool(Timestamp(10.0)) is True


class TestIsGPS:
    def test_small_p1_time_not_gps(self):
        assert not Timestamp(10.0).is_gps()

    def test_gps_time_is_gps(self):
        assert Timestamp(GPS_DATE_SEC).is_gps()

    def test_y2k_boundary_is_gps(self):
        assert Timestamp(Y2K_GPS_SEC).is_gps()

    def test_just_below_y2k_not_gps(self):
        assert not Timestamp(Y2K_GPS_SEC - 1).is_gps()

    def test_is_gps_time_helper_scalar(self):
        assert is_gps_time(GPS_DATE_SEC)
        assert not is_gps_time(10.0)

    def test_as_gps_returns_datetime_for_gps_time(self):
        result = Timestamp(GPS_DATE_SEC).as_gps()
        expected = GPS_POSIX_EPOCH + timedelta(seconds=GPS_DATE_SEC)
        assert result == expected

    def test_as_gps_returns_none_for_p1_time(self):
        assert Timestamp(10.0).as_gps() is None

    def test_as_utc_returns_datetime_for_gps_time(self):
        result = Timestamp(GPS_DATE_SEC).as_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_as_utc_returns_none_for_p1_time(self):
        assert Timestamp(10.0).as_utc() is None

    def test_as_gps_and_as_utc_differ_by_leap_seconds(self):
        gps_dt = Timestamp(GPS_DATE_SEC).as_gps()
        utc_dt = Timestamp(GPS_DATE_SEC).as_utc()
        delta = abs((gps_dt - utc_dt).total_seconds())
        # GPS is ahead of UTC by 18 leap seconds of 2017.
        assert delta == 18


class TestGetWeekTow:
    def test_gps_time_returns_correct_week_tow(self):
        week, tow = Timestamp(GPS_DATE_SEC).get_week_tow()
        assert week == GPS_DATE_WEEK
        assert tow == pytest.approx(GPS_DATE_TOW)

    def test_week_tow_reconstructs_original(self):
        week, tow = Timestamp(GPS_DATE_SEC).get_week_tow()
        assert week * SECONDS_PER_WEEK + tow == pytest.approx(GPS_DATE_SEC)

    def test_p1_time_returns_invalid(self):
        week, tow = Timestamp(10.0).get_week_tow()
        assert week == -1
        assert math.isnan(tow)


class TestFromDatetime:
    def test_from_gpstime_roundtrip(self):
        gt = gpstime.fromgps(GPS_DATE_SEC)
        ts = Timestamp.from_datetime(gt)
        assert float(ts) == pytest.approx(GPS_DATE_SEC, abs=1e-3)

    def test_from_utc_datetime_roundtrip(self):
        dt = gpstime.fromgps(GPS_DATE_SEC)
        ts = Timestamp.from_datetime(dt)
        assert float(ts) == pytest.approx(GPS_DATE_SEC, abs=1e-3)

    def test_from_datetime_is_gps(self):
        dt = gpstime.fromgps(GPS_DATE_SEC)
        ts = Timestamp.from_datetime(dt)
        assert ts.is_gps()


class TestArithmetic:
    def test_add_float(self):
        result = Timestamp(10.0) + 5.0
        assert isinstance(result, Timestamp)
        assert float(result) == pytest.approx(15.0)

    def test_radd_float(self):
        result = 5.0 + Timestamp(10.0)
        assert isinstance(result, Timestamp)
        assert float(result) == pytest.approx(15.0)

    def test_add_timedelta(self):
        result = Timestamp(10.0) + timedelta(seconds=3)
        assert isinstance(result, Timestamp)
        assert float(result) == pytest.approx(13.0)

    def test_sub_float(self):
        result = Timestamp(10.0) - 3.0
        assert isinstance(result, Timestamp)
        assert float(result) == pytest.approx(7.0)

    def test_sub_timedelta(self):
        result = Timestamp(10.0) - timedelta(seconds=3)
        assert isinstance(result, Timestamp)
        assert float(result) == pytest.approx(7.0)

    def test_sub_timestamp_returns_timedelta(self):
        result = Timestamp(10.0) - Timestamp(3.0)
        assert isinstance(result, timedelta)
        assert result.total_seconds() == pytest.approx(7.0)

    def test_sub_invalid_timestamp_returns_none(self):
        assert (Timestamp(10.0) - Timestamp()) is None
        assert (Timestamp() - Timestamp(10.0)) is None

    def test_iadd_float(self):
        ts = Timestamp(10.0)
        ts += 5.0
        assert float(ts) == pytest.approx(15.0)

    def test_iadd_timedelta(self):
        ts = Timestamp(10.0)
        ts += timedelta(seconds=5)
        assert float(ts) == pytest.approx(15.0)

    def test_isub_float(self):
        ts = Timestamp(10.0)
        ts -= 3.0
        assert float(ts) == pytest.approx(7.0)

    def test_isub_timedelta(self):
        ts = Timestamp(10.0)
        ts -= timedelta(seconds=3)
        assert float(ts) == pytest.approx(7.0)


class TestComparison:
    def test_eq(self):
        assert Timestamp(10.0) == Timestamp(10.0)
        assert not (Timestamp(10.0) == Timestamp(11.0))

    def test_ne(self):
        assert Timestamp(10.0) != Timestamp(11.0)
        assert not (Timestamp(10.0) != Timestamp(10.0))

    def test_lt(self):
        assert Timestamp(10.0) < Timestamp(11.0)
        assert not (Timestamp(11.0) < Timestamp(10.0))

    def test_le(self):
        assert Timestamp(10.0) <= Timestamp(10.0)
        assert Timestamp(10.0) <= Timestamp(11.0)
        assert not (Timestamp(11.0) <= Timestamp(10.0))

    def test_gt(self):
        assert Timestamp(11.0) > Timestamp(10.0)
        assert not (Timestamp(10.0) > Timestamp(11.0))

    def test_ge(self):
        assert Timestamp(10.0) >= Timestamp(10.0)
        assert Timestamp(11.0) >= Timestamp(10.0)
        assert not (Timestamp(10.0) >= Timestamp(11.0))

    def test_compare_with_raw_float(self):
        assert Timestamp(10.0) == 10.0
        assert Timestamp(10.0) < 11.0
        assert Timestamp(10.0) > 9.0


class TestPackUnpack:
    def test_calcsize(self):
        assert Timestamp.calcsize() == 8

    def test_pack_returns_size_by_default(self):
        result = Timestamp(10.0).pack()
        assert result == 8

    def test_pack_return_buffer(self):
        buf = Timestamp(10.0).pack(return_buffer=True)
        assert isinstance(buf, bytes)
        assert len(buf) == 8

    def test_pack_unpack_roundtrip(self):
        original = Timestamp(10.5)
        buf = original.pack(return_buffer=True)
        recovered = Timestamp()
        recovered.unpack(buf)
        assert float(recovered) == pytest.approx(10.5, abs=1e-9)

    def test_pack_unpack_fractional(self):
        original = Timestamp(GPS_DATE_SEC + 0.123456789)
        buf = original.pack(return_buffer=True)
        recovered = Timestamp()
        recovered.unpack(buf)
        assert float(recovered) == pytest.approx(float(original), abs=1e-6)

    def test_pack_invalid_uses_sentinel(self):
        buf = Timestamp().pack(return_buffer=True)
        int_part, frac_part = struct.unpack_from('<II', buf)
        assert int_part == 0xFFFFFFFF
        assert frac_part == 0xFFFFFFFF

    def test_unpack_sentinel_gives_invalid(self):
        buf = struct.pack('<II', 0xFFFFFFFF, 0xFFFFFFFF)
        ts = Timestamp()
        ts.unpack(buf)
        assert not ts

    def test_pack_into_buffer_at_offset(self):
        buf = bytearray(16)
        Timestamp(10.0).pack(buffer=buf, offset=4)
        recovered = Timestamp()
        recovered.unpack(bytes(buf), offset=4)
        assert float(recovered) == pytest.approx(10.0, abs=1e-9)

    def test_unpack_returns_size(self):
        buf = Timestamp(10.0).pack(return_buffer=True)
        ts = Timestamp()
        bytes_read = ts.unpack(buf)
        assert bytes_read == 8


class TestStringRepresentation:
    def test_p1_str_format(self):
        assert Timestamp(10.0).to_p1_str() == '10.000 sec'

    def test_gps_str_format(self):
        s = Timestamp(GPS_DATE_SEC).to_gps_str()
        expected = '%d:%.3f (%.3f sec)' % (GPS_DATE_WEEK, GPS_DATE_TOW, GPS_DATE_SEC)
        assert s == expected

    def test_str_p1_prefix(self):
        assert str(Timestamp(10.0)).startswith('P1:')

    def test_str_gps_prefix(self):
        assert str(Timestamp(GPS_DATE_SEC)).startswith('GPS:')
