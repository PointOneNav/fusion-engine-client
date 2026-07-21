import json

import numpy as np
import pytest
from pymap3d import geodetic2ecef

from fusion_engine_client.analysis.data_loader import DataLoader
from fusion_engine_client.analysis import reference as reference_module
from fusion_engine_client.analysis.reference import ReferenceData
from fusion_engine_client.messages import PoseMessage, PoseAuxMessage, SolutionType, Timestamp
from fusion_engine_client.parsers import FusionEngineEncoder

# A small, deterministic set of pose epochs used across several tests:
#   index 0: Invalid solution -- must be excluded from every statistic.
#   index 1: AutonomousGPS, has PoseAux data -- "first" valid epoch.
#   index 2: RTKFloat, PoseAux missing (tests NaN gap handling via TimeAlignmentMode.INSERT).
#   index 3: RTKFixed.
#   index 4: RTKFixed.
_EPOCHS = [
    dict(p1_time=1.0, gps_time=1000.0, solution_type=SolutionType.Invalid,
         lla_deg=(0.0, 0.0, 0.0), ypr_deg=None, velocity_enu_mps=None),
    dict(p1_time=2.0, gps_time=1001.0, solution_type=SolutionType.AutonomousGPS,
         lla_deg=(37.0, -122.0, 10.0), ypr_deg=(10.0, 1.0, 2.0), velocity_enu_mps=(1.0, 0.1, 0.0)),
    dict(p1_time=3.0, gps_time=1002.0, solution_type=SolutionType.RTKFloat,
         lla_deg=(37.1, -122.1, 11.0), ypr_deg=(20.0, 2.0, 3.0), velocity_enu_mps=None),
    dict(p1_time=4.0, gps_time=1003.0, solution_type=SolutionType.RTKFixed,
         lla_deg=(37.2, -122.2, 12.0), ypr_deg=(30.0, 3.0, 4.0), velocity_enu_mps=(3.0, 0.3, 0.0)),
    dict(p1_time=5.0, gps_time=1004.0, solution_type=SolutionType.RTKFixed,
         lla_deg=(37.3, -122.3, 13.0), ypr_deg=(40.0, 4.0, 5.0), velocity_enu_mps=(4.0, 0.4, 0.0)),
]


def _build_messages(epochs):
    messages = []
    for epoch in epochs:
        pose = PoseMessage()
        pose.p1_time = Timestamp(epoch['p1_time'])
        pose.gps_time = Timestamp(epoch['gps_time'])
        pose.solution_type = epoch['solution_type']
        pose.lla_deg = np.array(epoch['lla_deg'], dtype=float)
        if epoch['ypr_deg'] is not None:
            pose.ypr_deg = np.array(epoch['ypr_deg'], dtype=float)
        messages.append(pose)

        if epoch['velocity_enu_mps'] is not None:
            aux = PoseAuxMessage()
            aux.p1_time = Timestamp(epoch['p1_time'])
            aux.velocity_enu_mps = np.array(epoch['velocity_enu_mps'], dtype=float)
            messages.append(aux)

    return messages


def _write_log(path, epochs):
    encoder = FusionEngineEncoder()
    with open(path, 'wb') as f:
        for message in _build_messages(epochs):
            f.write(encoder.encode_message(message))


@pytest.fixture
def loader(tmp_path):
    path = tmp_path / 'test_file.p1log'
    _write_log(path, _EPOCHS)
    return DataLoader(path=str(path))


def _expected_ecef(*indices):
    lla = np.array([_EPOCHS[i]['lla_deg'] for i in indices]).T
    return np.array(geodetic2ecef(lat=lla[0, :], lon=lla[1, :], alt=lla[2, :], deg=True))


class TestProperties:
    def test_stationary(self):
        ref = ReferenceData.from_stationary_lla(np.array([37.0, -122.0, 10.0]))
        assert ref.is_stationary
        assert not ref.has_velocity
        assert not ref.has_orientation
        assert ref.is_truth
        assert ref.displacement_label == 'Error'

    def test_own_log_is_not_truth(self, loader):
        ref = ReferenceData.from_own_log(loader, statistic='median')
        assert not ref.is_truth
        assert ref.displacement_label == 'Displacement'

    def test_reference_log_is_truth(self, loader):
        ref = ReferenceData.from_reference_log(loader)
        assert ref.is_truth
        assert ref.displacement_label == 'Error'
        assert not ref.is_stationary


class TestStationaryConstructors:
    def test_from_stationary_lla(self):
        lla_deg = np.array([37.1234, -122.526335, 102.34])
        ref = ReferenceData.from_stationary_lla(lla_deg)
        expected_ecef_m = np.array(geodetic2ecef(*lla_deg, deg=True))
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)
        assert ref.is_truth
        assert ref.gps_time_sec is None
        assert '37.12340000' in ref.description

    def test_from_stationary_ecef(self):
        position_ecef_m = np.array([-2707071.0, -4321671.7, 3817403.2])
        ref = ReferenceData.from_stationary_ecef(position_ecef_m)
        assert ref.position_ecef_m == pytest.approx(position_ecef_m)
        assert ref.is_truth
        assert 'ECEF' in ref.description


class TestFromOwnLog:
    def test_median(self, loader):
        ref = ReferenceData.from_own_log(loader, statistic='median')
        assert not ref.is_truth
        assert ref.description == 'Median Position'

        expected_ecef_m = np.median(_expected_ecef(1, 2, 3, 4), axis=1)
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)

        # Epoch 2 (index 2) has no PoseAux data; the other 3 valid epochs do, so the median velocity should still be
        # well-defined via nanmedian.
        assert ref.has_velocity
        expected_velocity = np.nanmedian(
            np.array([[1.0, 0.1, 0.0], [np.nan, np.nan, np.nan], [3.0, 0.3, 0.0], [4.0, 0.4, 0.0]]).T, axis=1)
        assert ref.velocity_enu_mps == pytest.approx(expected_velocity)

        assert ref.has_orientation
        expected_ypr = np.median(np.array([e['ypr_deg'] for e in _EPOCHS[1:]]).T, axis=1)
        assert ref.ypr_deg == pytest.approx(expected_ypr)

    def test_first(self, loader):
        ref = ReferenceData.from_own_log(loader, statistic='first')
        assert ref.description == 'First Position'

        expected_ecef_m = _expected_ecef(1)[:, 0]
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)

        # The first valid epoch (index 1) has both orientation and velocity data.
        assert ref.has_orientation
        assert ref.ypr_deg == pytest.approx(np.array(_EPOCHS[1]['ypr_deg']))
        assert ref.has_velocity
        assert ref.velocity_enu_mps == pytest.approx(np.array(_EPOCHS[1]['velocity_enu_mps']))

    def test_median_fixed(self, loader):
        ref = ReferenceData.from_own_log(loader, statistic='median_fixed')
        assert ref.description == 'Median Fixed Position'

        expected_ecef_m = np.median(_expected_ecef(3, 4), axis=1)
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)
        assert ref.has_velocity

    def test_median_fixed_falls_back_when_no_fixed_solutions(self, tmp_path, monkeypatch):
        epochs = [e for e in _EPOCHS if e['solution_type'] != SolutionType.RTKFixed]
        path = tmp_path / 'no_fixed.p1log'
        _write_log(path, epochs)
        no_fixed_loader = DataLoader(path=str(path))

        warnings = []
        monkeypatch.setattr(reference_module._logger, 'warning', lambda msg: warnings.append(msg))

        ref = ReferenceData.from_own_log(no_fixed_loader, statistic='median_fixed')
        assert ref.description == 'Median Position'
        assert any('No fixed positions' in w for w in warnings)

    def test_no_valid_solutions_returns_none(self, tmp_path):
        epochs = [dict(e, solution_type=SolutionType.Invalid) for e in _EPOCHS]
        path = tmp_path / 'all_invalid.p1log'
        _write_log(path, epochs)
        invalid_loader = DataLoader(path=str(path))

        assert ReferenceData.from_own_log(invalid_loader, statistic='median') is None

    def test_invalid_statistic_raises(self, loader):
        with pytest.raises(ValueError):
            ReferenceData.from_own_log(loader, statistic='bogus')


class TestFromReferenceLog:
    def test_loads_time_varying_data(self, loader):
        ref = ReferenceData.from_reference_log(loader)
        assert ref.is_truth
        assert not ref.is_stationary

        # 4 valid epochs (index 0 is Invalid and excluded).
        assert len(ref.gps_time_sec) == 4
        assert list(ref.gps_time_sec) == sorted(ref.gps_time_sec)
        assert ref.gps_time_sec[0] == pytest.approx(1001.0)
        assert ref.gps_time_sec[-1] == pytest.approx(1004.0)

        expected_ecef_m = _expected_ecef(1, 2, 3, 4)
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)

        assert ref.has_velocity
        # Epoch at gps_time=1002 (index 2) has no PoseAux data -> NaN gap.
        assert np.all(np.isnan(ref.velocity_enu_mps[:, 1]))
        assert ref.velocity_enu_mps[:, 0] == pytest.approx(np.array(_EPOCHS[1]['velocity_enu_mps']))

    def test_no_valid_solutions_returns_none(self, tmp_path):
        epochs = [dict(e, solution_type=SolutionType.Invalid) for e in _EPOCHS]
        path = tmp_path / 'all_invalid.p1log'
        _write_log(path, epochs)
        invalid_loader = DataLoader(path=str(path))

        assert ReferenceData.from_reference_log(invalid_loader) is None

    def test_unresolvable_path_returns_none(self, tmp_path):
        empty_log_base = tmp_path / 'log_base'
        empty_log_base.mkdir()
        assert ReferenceData.from_reference_log('no_such_log', log_base_dir=str(empty_log_base)) is None

    def test_path_or_hash_resolution(self, tmp_path):
        # Build <log_base>/2024-01-15/abc123hash/fusion_engine.p1log with a manifest, mirroring a real FE log
        # directory layout, and confirm from_reference_log() can locate and load it by log ID.
        log_base = tmp_path / 'log_base'
        log_dir = log_base / '2024-01-15' / 'abc123hash'
        log_dir.mkdir(parents=True)
        _write_log(log_dir / 'fusion_engine.p1log', _EPOCHS)
        with open(log_dir / 'manifest.json', 'w') as f:
            json.dump({'channels': ['fusion_engine.p1log'], 'guid': 'abc123hash'}, f)

        ref = ReferenceData.from_reference_log('abc123hash', log_base_dir=str(log_base))
        assert ref is not None
        assert ref.is_truth
        assert 'abc123hash' in ref.description
        assert len(ref.gps_time_sec) == 4


class TestInterpolation:
    @pytest.fixture
    def moving_ref(self):
        return ReferenceData(description='test', is_truth=True,
                             position_ecef_m=np.array([[0.0, 10.0], [0.0, 20.0], [0.0, 30.0]]),
                             gps_time_sec=np.array([0.0, 10.0]),
                             velocity_enu_mps=np.array([[1.0, 3.0], [2.0, 4.0], [np.nan, np.nan]]))

    def test_interpolate_midpoint(self, moving_ref):
        pos = moving_ref.interpolate_position_ecef_m(np.array([5.0]))
        assert pos[:, 0] == pytest.approx([5.0, 10.0, 15.0])

    def test_interpolation_is_cached(self, moving_ref, monkeypatch):
        original = reference_module._interp_columns
        calls = []
        monkeypatch.setattr(reference_module, '_interp_columns',
                            lambda *args, **kwargs: calls.append(1) or original(*args, **kwargs))

        query = np.array([5.0])

        # A repeated query with the same start/end/count is served from cache -- no additional call.
        first = moving_ref.interpolate_position_ecef_m(query)
        second = moving_ref.interpolate_position_ecef_m(query)
        assert len(calls) == 1
        assert first is second

        # A different field has its own cache entry -- computing velocity doesn't disturb position's cache.
        moving_ref.interpolate_velocity_enu_mps(query)
        assert len(calls) == 2
        moving_ref.interpolate_position_ecef_m(query)
        assert len(calls) == 2

        # A query with a different start/end/count is not a cache hit.
        moving_ref.interpolate_position_ecef_m(np.array([0.0, 10.0]))
        assert len(calls) == 3

    def test_interpolate_out_of_range_is_nan(self, moving_ref):
        pos = moving_ref.interpolate_position_ecef_m(np.array([-5.0, 15.0]))
        assert np.all(np.isnan(pos))

    def test_interpolate_velocity_with_all_nan_row(self, moving_ref):
        vel = moving_ref.interpolate_velocity_enu_mps(np.array([5.0]))
        assert vel[0, 0] == pytest.approx(2.0)
        assert vel[1, 0] == pytest.approx(3.0)
        # The third row is entirely NaN in the source data -- cannot be interpolated.
        assert np.isnan(vel[2, 0])

    def test_interpolate_ypr_none_when_unavailable(self, moving_ref):
        assert moving_ref.interpolate_ypr_deg(np.array([5.0])) is None

    def test_stationary_interpolation_tiles(self):
        ref = ReferenceData.from_stationary_ecef(np.array([1.0, 2.0, 3.0]))
        pos = ref.interpolate_position_ecef_m(np.array([0.0, 1.0, 2.0]))
        assert pos.shape == (3, 3)
        expected = np.tile(np.array([1.0, 2.0, 3.0]).reshape(3, 1), (1, 3))
        assert pos == pytest.approx(expected)

    def test_get_coverage_mask_full(self, moving_ref):
        mask = moving_ref.get_coverage_mask(np.array([0.0, 5.0, 10.0]))
        assert np.all(mask)

    def test_get_coverage_mask_partial_warns(self, moving_ref, monkeypatch):
        warnings = []
        monkeypatch.setattr(reference_module._logger, 'warning', lambda msg: warnings.append(msg))

        mask = moving_ref.get_coverage_mask(np.array([-5.0, 5.0, 15.0]))
        assert list(mask) == [False, True, False]
        assert len(warnings) == 1

    def test_get_coverage_mask_stationary_always_covers(self):
        ref = ReferenceData.from_stationary_ecef(np.array([1.0, 2.0, 3.0]))
        mask = ref.get_coverage_mask(np.array([-1e9, 0.0, 1e9]))
        assert np.all(mask)


class TestResolveCliArgument:
    def test_none_returns_none(self, loader):
        assert ReferenceData.resolve_cli_argument(None, loader=loader) is None

    def test_lla_inferred_from_magnitude(self, loader):
        ref = ReferenceData.resolve_cli_argument('37.1234, -122.526335, 102.34', loader=loader)
        assert 'ECEF' not in ref.description
        expected_ecef_m = np.array(geodetic2ecef(37.1234, -122.526335, 102.34, deg=True))
        assert ref.position_ecef_m == pytest.approx(expected_ecef_m)

    def test_ecef_inferred_from_magnitude(self, loader):
        position_ecef_m = np.array([-2707071.0, -4321671.7, 3817403.2])
        ref = ReferenceData.resolve_cli_argument(
            '-2707071.0, -4321671.7, 3817403.2', loader=loader)
        assert 'ECEF' in ref.description
        assert ref.position_ecef_m == pytest.approx(position_ecef_m)

    def test_lla_prefix_forces_lla(self, loader):
        ref = ReferenceData.resolve_cli_argument('lla: 37.1234, -122.526335, 102.34', loader=loader)
        assert 'ECEF' not in ref.description

    def test_ecef_prefix_forces_ecef(self, loader):
        ref = ReferenceData.resolve_cli_argument(
            'ecef: -2707071.0, -4321671.7, 3817403.2', loader=loader)
        assert 'ECEF' in ref.description

    def test_prefix_is_case_insensitive(self, loader):
        ref = ReferenceData.resolve_cli_argument('ECEF: -2707071.0, -4321671.7, 3817403.2', loader=loader)
        assert 'ECEF' in ref.description

    @pytest.mark.parametrize('statistic', ['first', 'median', 'median_fixed'])
    def test_own_log_keywords_dispatch(self, loader, statistic):
        via_resolve = ReferenceData.resolve_cli_argument(statistic, loader=loader)
        via_direct = ReferenceData.from_own_log(loader, statistic=statistic)
        assert via_resolve.description == via_direct.description
        assert via_resolve.position_ecef_m == pytest.approx(via_direct.position_ecef_m)
        assert not via_resolve.is_truth

    def test_unrecognized_string_falls_back_to_log_path_and_fails_gracefully(self, loader, tmp_path):
        empty_log_base = tmp_path / 'log_base'
        empty_log_base.mkdir()
        result = ReferenceData.resolve_cli_argument(
            'not_a_real_log_hash', loader=loader, log_base_dir=str(empty_log_base))
        assert result is None
