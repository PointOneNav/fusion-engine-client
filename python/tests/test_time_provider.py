from datetime import datetime

from gpstime import gpstime
import numpy as np
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


class _FakeReader:
    """!
    @brief Minimal stand-in for a @ref DataLoader, returning pre-baked pose arrays from read().
    """
    def __init__(self, p1_time, gps_time):
        self.p1_time = np.asarray(p1_time, dtype=float)
        self.gps_time = np.asarray(gps_time, dtype=float)
        self.last_read_kwargs = None

    def read(self, **kwargs):
        self.last_read_kwargs = kwargs
        pose_data = type('PoseData', (), {'p1_time': self.p1_time, 'gps_time': self.gps_time})()
        return {PoseMessage.MESSAGE_TYPE: pose_data}


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


class TestSetReferenceData:
    def test_loads_table_in_chronological_order(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [10.0, 20.0]
        assert list(tp._reference_gps_time) == pytest.approx([GPS_DATE_SEC, GPS_DATE_SEC + 10.0])

    def test_reset_discards_data_before_it(self):
        # P1 time jumps backward at index 2 (device reboot) -- only data from the most recent boot session
        # (starting at the new, smaller P1 time) should be kept, not reordered in with the earlier session.
        reader = _FakeReader(p1_time=[10.0, 20.0, 5.0, 15.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0,
                                       GPS_DATE_SEC + 1000.0, GPS_DATE_SEC + 1010.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [5.0, 15.0]
        assert list(tp._reference_gps_time) == pytest.approx([GPS_DATE_SEC + 1000.0, GPS_DATE_SEC + 1010.0])

    def test_multiple_resets_keeps_only_last_segment(self):
        reader = _FakeReader(p1_time=[10.0, 5.0, 20.0, 3.0, 8.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 100.0, GPS_DATE_SEC + 110.0,
                                       GPS_DATE_SEC + 500.0, GPS_DATE_SEC + 505.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [3.0, 8.0]
        assert list(tp._reference_gps_time) == pytest.approx([GPS_DATE_SEC + 500.0, GPS_DATE_SEC + 505.0])

    def test_reset_with_mutually_exclusive_ranges_combines_segments(self):
        # Session 1 (recorded late, P1 in [50, 60]) is followed by a reset, then session 2 (recorded from near the
        # start, P1 in [5, 10]). The ranges don't overlap, so both sessions can be safely combined and sorted.
        reader = _FakeReader(p1_time=[50.0, 60.0, 5.0, 10.0],
                             gps_time=[GPS_DATE_SEC + 50.0, GPS_DATE_SEC + 60.0,
                                       GPS_DATE_SEC + 500.0, GPS_DATE_SEC + 505.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [5.0, 10.0, 50.0, 60.0]
        assert list(tp._reference_gps_time) == pytest.approx(
            [GPS_DATE_SEC + 500.0, GPS_DATE_SEC + 505.0, GPS_DATE_SEC + 50.0, GPS_DATE_SEC + 60.0])
        # Interpolating within either session's own range should use that session's local relationship.
        result = tp.p1_to_gps(np.array([7.5, 55.0]))
        assert result == pytest.approx([GPS_DATE_SEC + 502.5, GPS_DATE_SEC + 55.0])

    def test_drops_nan_entries(self):
        reader = _FakeReader(p1_time=[10.0, np.nan, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 5.0, np.nan])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [10.0]
        assert list(tp._reference_gps_time) == pytest.approx([GPS_DATE_SEC])

    def test_drops_duplicate_p1_times(self):
        reader = _FakeReader(p1_time=[10.0, 10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert list(tp._reference_p1_time) == [10.0, 20.0]

    def test_passes_source_id_through(self):
        reader = _FakeReader(p1_time=[10.0], gps_time=[GPS_DATE_SEC])
        tp = TimeProvider()
        tp.set_reference_data(reader, source_id=3)
        assert reader.last_read_kwargs['source_ids'] == 3

    def test_empty_pose_data(self):
        reader = _FakeReader(p1_time=[], gps_time=[])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert len(tp._reference_p1_time) == 0


class TestP1ToGPSArray:
    def test_no_reference_returns_nan(self):
        tp = TimeProvider()
        result = tp.p1_to_gps(np.array([10.0, 12.0]))
        assert isinstance(result, np.ndarray)
        assert np.all(np.isnan(result))

    def test_uses_bulk_reference_table_interpolation(self):
        reader = _FakeReader(p1_time=[10.0, 20.0, 30.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0, GPS_DATE_SEC + 20.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.p1_to_gps(np.array([15.0, 25.0]))
        assert result == pytest.approx([GPS_DATE_SEC + 5.0, GPS_DATE_SEC + 15.0])

    def test_bulk_reference_table_extrapolation(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.p1_to_gps(np.array([5.0, 25.0]))
        assert result == pytest.approx([GPS_DATE_SEC - 5.0, GPS_DATE_SEC + 15.0])

    def test_falls_back_to_sequential_state_when_no_table_loaded(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        result = tp.p1_to_gps(np.array([15.0, 25.0]))
        assert result == pytest.approx([GPS_DATE_SEC + 5.0, GPS_DATE_SEC + 15.0])

    def test_bulk_table_takes_priority_over_sequential_state(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        # Sequential state implies a different (wrong) relationship; the bulk table should win.
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC + 1000.0))
        result = tp.p1_to_gps(np.array([15.0]))
        assert result == pytest.approx([GPS_DATE_SEC + 5.0])

    def test_matches_scalar_result(self):
        reader = _FakeReader(p1_time=[10.0, 20.0, 30.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0, GPS_DATE_SEC + 20.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        array_result = tp.p1_to_gps(np.array([15.0]))[0]
        scalar_result = float(tp.p1_to_gps(Timestamp(15.0)))
        assert array_result == pytest.approx(scalar_result)

    def test_datetime_format(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.p1_to_gps(np.array([10.0, np.nan]), format='datetime')
        assert result.dtype.kind == 'M'
        assert not np.isnat(result[0])
        assert np.isnat(result[1])
        expected = gpstime.fromgps(GPS_DATE_SEC)
        assert result[0].astype('datetime64[us]').item() == expected.replace(tzinfo=None)

    def test_nan_input_returns_nan(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.p1_to_gps(np.array([15.0, np.nan]))
        assert result[0] == pytest.approx(GPS_DATE_SEC + 5.0)
        assert np.isnan(result[1])


class TestGPSToP1Array:
    def test_no_reference_returns_nan(self):
        tp = TimeProvider()
        result = tp.gps_to_p1(np.array([GPS_DATE_SEC]))
        assert np.all(np.isnan(result))

    def test_uses_bulk_reference_table_interpolation(self):
        reader = _FakeReader(p1_time=[10.0, 20.0, 30.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0, GPS_DATE_SEC + 20.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.gps_to_p1(np.array([GPS_DATE_SEC + 5.0, GPS_DATE_SEC + 15.0]))
        assert result == pytest.approx([15.0, 25.0])

    def test_falls_back_to_sequential_state_when_no_table_loaded(self):
        tp = TimeProvider()
        tp.handle_message(_make_pose(10.0, GPS_DATE_SEC))
        tp.handle_message(_make_pose(20.0, GPS_DATE_SEC + 10.0))
        result = tp.gps_to_p1(np.array([GPS_DATE_SEC + 5.0]))
        assert result == pytest.approx([15.0])

    def test_roundtrip_with_bulk_table(self):
        reader = _FakeReader(p1_time=[10.0, 20.0, 30.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0, GPS_DATE_SEC + 20.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        original = np.array([12.5, 24.0])
        recovered = tp.gps_to_p1(tp.p1_to_gps(original))
        assert recovered == pytest.approx(original)


class TestHasGpsReference:
    def test_default_false(self):
        tp = TimeProvider()
        assert not tp.has_gps_reference()

    def test_true_after_loading_reference_table(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.has_gps_reference()

    def test_true_when_p1_is_gps(self):
        reader = _FakeReader(p1_time=[GPS_DATE_SEC], gps_time=[GPS_DATE_SEC])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.has_gps_reference()

    def test_false_when_no_gps_time_in_log(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[np.nan, np.nan])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert not tp.has_gps_reference()


class TestGetGpsPosixOffsetSec:
    def test_none_with_no_reference(self):
        tp = TimeProvider()
        assert tp.get_gps_posix_offset_sec() is None

    def test_cached_not_recomputed_per_call(self):
        from unittest import mock
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        with mock.patch('fusion_engine_client.utils.time_provider.gps2unix') as mock_gps2unix:
            offset1 = tp.get_gps_posix_offset_sec()
            offset2 = tp.get_gps_posix_offset_sec()
            mock_gps2unix.assert_not_called()
        assert offset1 == offset2

    def test_offset_matches_gpstime_library(self):
        from gpstime import gps2unix
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        offset = tp.get_gps_posix_offset_sec()
        assert offset == pytest.approx(gps2unix(GPS_DATE_SEC) - GPS_DATE_SEC)
        # Applying the offset to any GPS time in the table should recover the accurate POSIX/Unix timestamp.
        assert GPS_DATE_SEC + offset == pytest.approx(gps2unix(GPS_DATE_SEC))

    def test_uses_p1_time_as_sample_when_p1_is_gps_and_table_empty(self):
        # p1_time looks like GPS time, but gps_time was never populated, so the reference table is empty.
        from gpstime import gps2unix
        reader = _FakeReader(p1_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0], gps_time=[np.nan, np.nan])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.is_p1_gps_time()
        offset = tp.get_gps_posix_offset_sec()
        assert offset == pytest.approx(gps2unix(GPS_DATE_SEC) - GPS_DATE_SEC)

    def test_skips_non_gps_like_samples_before_gps_acquired(self):
        # Before GPS time is first acquired, P1 time starts as a small boot-relative counter -- not GPS-like -- even
        # though the platform switches to using GPS time as P1 time once it's available. The first valid sample
        # (10.0) is not GPS-like and must not be used as the representative sample.
        from gpstime import gps2unix
        reader = _FakeReader(p1_time=[10.0, 20.0, GPS_DATE_SEC], gps_time=[np.nan, np.nan, np.nan])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.is_p1_gps_time()
        offset = tp.get_gps_posix_offset_sec()
        assert offset == pytest.approx(gps2unix(GPS_DATE_SEC) - GPS_DATE_SEC)


class TestP1IsGpsTime:
    def test_default_false(self):
        tp = TimeProvider()
        assert not tp.is_p1_gps_time()

    def test_normal_boot_relative_p1_time_not_detected(self):
        reader = _FakeReader(p1_time=[10.0, 20.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert not tp.is_p1_gps_time()

    def test_detects_gps_as_p1(self):
        reader = _FakeReader(p1_time=[GPS_DATE_SEC, GPS_DATE_SEC + 1.0], gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 1.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.is_p1_gps_time()

    def test_single_gps_like_sample_is_conclusive(self):
        # Only one sample looks like GPS time (e.g. a reset happened partway through); that alone is conclusive.
        reader = _FakeReader(p1_time=[5.0, GPS_DATE_SEC], gps_time=[GPS_DATE_SEC + 100.0, GPS_DATE_SEC])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        assert tp.is_p1_gps_time()

    def test_p1_to_gps_array_is_identity_far_outside_reference_range(self):
        reader = _FakeReader(p1_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        # Query far outside the reference range -- still exact, since P1 IS GPS by definition.
        result = tp.p1_to_gps(np.array([GPS_DATE_SEC + 1e6]))
        assert result == pytest.approx([GPS_DATE_SEC + 1e6])

    def test_gps_to_p1_array_is_identity_far_outside_reference_range(self):
        reader = _FakeReader(p1_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0],
                             gps_time=[GPS_DATE_SEC, GPS_DATE_SEC + 10.0])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.gps_to_p1(np.array([GPS_DATE_SEC + 1e6]))
        assert result == pytest.approx([GPS_DATE_SEC + 1e6])

    def test_datetime_format_when_p1_is_gps(self):
        reader = _FakeReader(p1_time=[GPS_DATE_SEC], gps_time=[GPS_DATE_SEC])
        tp = TimeProvider()
        tp.set_reference_data(reader)
        result = tp.p1_to_gps(np.array([GPS_DATE_SEC]), format='datetime')
        assert result.dtype.kind == 'M'
        assert not np.isnat(result[0])
