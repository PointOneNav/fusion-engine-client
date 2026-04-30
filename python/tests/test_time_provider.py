from datetime import datetime

from gpstime import gpstime
import pytest

from fusion_engine_client.messages import PoseMessage, Timestamp
from fusion_engine_client.utils.time_provider import TimeProvider


# GPS time for 2026/4/29 08:00:00 UTC (arbitrary reference point for the tests below).
GPS_DATE_SEC = 1461484818.0


def _make_pose(p1_sec, gps_sec):
    msg = PoseMessage()
    msg.p1_time = Timestamp(p1_sec)
    msg.gps_time = Timestamp(gps_sec)
    return msg


class TestHandleMessage:
    def test_ignores_non_pose_message(self):
        tp = TimeProvider()
        # Passing a non-PoseMessage should not crash and leave state invalid.
        tp.handle_message(object())
        assert not tp._current_p1_time
        assert not tp._current_gps_time

    def test_stores_current_times(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        assert float(tp._current_p1_time) == pytest.approx(10.0)
        assert float(tp._current_gps_time) == pytest.approx(GPS_DATE_SEC)

    def test_advances_prev_times(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(11.0, GPS_DATE_SEC + 1.0))
        assert float(tp._prev_p1_time) == pytest.approx(10.0)
        assert float(tp._prev_gps_time) == pytest.approx(GPS_DATE_SEC)
        assert float(tp._current_p1_time) == pytest.approx(11.0)
        assert float(tp._current_gps_time) == pytest.approx(GPS_DATE_SEC + 1.0)

    # --- Backwards timestamp tests ---

    def test_backwards_timestamp_resets_and_stores_new(self):
        # A large backwards jump resets state and stores the new (earlier) time.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(5.0, GPS_DATE_SEC - 5.0))
        assert float(tp._current_p1_time) == pytest.approx(5.0)
        assert float(tp._current_gps_time) == pytest.approx(GPS_DATE_SEC - 5.0)
        assert not tp._prev_p1_time
        assert not tp._prev_gps_time

    def test_backwards_timestamp_after_two_updates_resets_prev(self):
        # After two good updates, a backwards jump clears prev so conversion falls back
        # to single-reference mode with only the new (reset) time.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        tp.handle_message(_make_pose(5.0, GPS_DATE_SEC - 5.0))
        assert float(tp._current_p1_time) == pytest.approx(5.0)
        assert not tp._prev_p1_time

    def test_backwards_conversion_uses_new_reference(self):
        # After a backwards reset the new single reference is used for conversion.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(5.0, GPS_DATE_SEC - 5.0))
        result = tp.p1_to_gps(Timestamp(7.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC - 3.0)

    def test_tiny_backwards_jump_within_threshold_treated_as_duplicate(self):
        # A backwards jump of exactly 0.5 ms (< 1 ms) is treated as a duplicate and ignored.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(10.0 - 0.0005, GPS_DATE_SEC - 0.0005))
        assert float(tp._current_p1_time) == pytest.approx(10.0)
        assert not tp._prev_p1_time

    # --- Duplicate timestamp tests ---

    def test_exact_duplicate_is_ignored(self):
        # Sending the same p1_time twice: second message should be dropped.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        assert float(tp._current_p1_time) == pytest.approx(10.0)
        assert not tp._prev_p1_time

    def test_near_duplicate_below_threshold_is_ignored(self):
        # A 0.5 ms forward jump (below the 1 ms threshold) is treated as a duplicate.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(10.0005, GPS_DATE_SEC + 0.0005))
        assert float(tp._current_p1_time) == pytest.approx(10.0)
        assert not tp._prev_p1_time

    def test_near_duplicate_above_threshold_is_accepted(self):
        # A 2 ms forward jump (above the 1 ms threshold) is treated as a new update.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(10.002, GPS_DATE_SEC + 0.002))
        assert float(tp._current_p1_time) == pytest.approx(10.002)
        assert float(tp._prev_p1_time) == pytest.approx(10.0)

    def test_duplicate_does_not_corrupt_conversion(self):
        # After a duplicate is dropped, conversion still works correctly using the
        # original reference.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))  # duplicate
        result = tp.p1_to_gps(Timestamp(12.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC + 2.0)


class TestP1ToGPS:
    def test_invalid_p1_returns_invalid(self):
        tp = TimeProvider()
        result = tp.p1_to_gps(Timestamp())
        assert not result

    def test_no_reference_returns_invalid(self):
        tp = TimeProvider()
        result = tp.p1_to_gps(Timestamp(10.0))
        assert not result

    def test_invalid_p1_returns_none_for_datetime_format(self):
        tp = TimeProvider()
        assert tp.p1_to_gps(Timestamp(), format='datetime') is None

    def test_no_reference_returns_none_for_datetime_format(self):
        tp = TimeProvider()
        assert tp.p1_to_gps(Timestamp(10.0), format='datetime') is None

    def test_single_reference_no_interpolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        # Offset is GPS_2021_SEC - 10.0; querying p1=12.0 should yield GPS_2021_SEC + 2.0.
        result = tp.p1_to_gps(Timestamp(12.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC + 2.0)

    def test_two_references_interpolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        # Midpoint between the two updates.
        result = tp.p1_to_gps(Timestamp(15.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC + 5.0)

    def test_two_references_extrapolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        # Past the latest update — extrapolates.
        result = tp.p1_to_gps(Timestamp(25.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC + 15.0)

    def test_interpolation_with_drift(self):
        # P1 runs slightly fast: 10 P1-sec == 10.001 GPS-sec.
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.001))
        result = tp.p1_to_gps(Timestamp(15.0))
        assert float(result) == pytest.approx(GPS_DATE_SEC + 5.0005)

    def test_datetime_format(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        result = tp.p1_to_gps(Timestamp(10.0), format='datetime')
        assert isinstance(result, datetime)

    def test_datetime_format_matches_timestamp_format(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        ts_result = tp.p1_to_gps(Timestamp(12.0))
        dt_result = tp.p1_to_gps(Timestamp(12.0), format='datetime')
        assert isinstance(dt_result, datetime)
        expected = gpstime.fromgps(float(ts_result))
        assert dt_result == expected


class TestGPSToP1:
    def test_invalid_gps_returns_invalid(self):
        tp = TimeProvider()
        result = tp.gps_to_p1(Timestamp())
        assert not result

    def test_no_reference_returns_invalid(self):
        tp = TimeProvider()
        result = tp.gps_to_p1(Timestamp(GPS_DATE_SEC))
        assert not result

    def test_single_reference_no_interpolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        result = tp.gps_to_p1(Timestamp(GPS_DATE_SEC + 2.0))
        assert float(result) == pytest.approx(12.0)

    def test_two_references_interpolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        result = tp.gps_to_p1(Timestamp(GPS_DATE_SEC + 5.0))
        assert float(result) == pytest.approx(15.0)

    def test_two_references_extrapolation(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        result = tp.gps_to_p1(Timestamp(GPS_DATE_SEC + 15.0))
        assert float(result) == pytest.approx(25.0)

    def test_accepts_datetime(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        dt = gpstime.fromgps(GPS_DATE_SEC + 2.0)
        result = tp.gps_to_p1(dt)
        assert float(result) == pytest.approx(12.0, abs=1e-3)

    def test_accepts_gpstime(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        gt = gpstime.fromgps(GPS_DATE_SEC + 2.0)
        result = tp.gps_to_p1(gt)
        assert float(result) == pytest.approx(12.0, abs=1e-3)

    def test_roundtrip_p1_to_gps_to_p1(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        original = Timestamp(14.5)
        gps = tp.p1_to_gps(original)
        recovered = tp.gps_to_p1(gps)
        assert float(recovered) == pytest.approx(float(original), abs=1e-6)
