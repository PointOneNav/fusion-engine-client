import numpy as np
import pymap3d as pm
import pytest

from fusion_engine_client.messages import ExternalPoseInput, PoseMessage, SolutionType, SystemTimeSource, Timestamp
from fusion_engine_client.utils.pose_relay import transform_pose_to_target, transformed_pose_to_external_pose_input

ZERO = np.zeros(3)


def _make_valid_pose():
    pose = PoseMessage()
    pose.p1_time = Timestamp(10.0)
    pose.gps_time = Timestamp(1000.0)
    pose.solution_type = SolutionType.RTKFixed
    pose.lla_deg = np.array([37.7749, -122.4194, 10.0])
    pose.position_std_enu_m = np.array([0.1, 0.2, 0.3])
    pose.ypr_deg = np.array([45.0, 1.0, 2.0])
    pose.ypr_std_deg = np.array([0.5, 0.1, 0.1])
    pose.velocity_body_mps = np.array([3.0, 0.0, 0.0])
    pose.velocity_std_body_mps = np.array([0.05, 0.05, 0.05])
    return pose


class TestTransformPoseToTarget:
    def test_identity_transform(self):
        pose = _make_valid_pose()
        result = transform_pose_to_target(pose, ZERO, ZERO, ZERO, ZERO)

        np.testing.assert_allclose(result['position_ecef_m'], pm.geodetic2ecef(*pose.lla_deg), atol=1e-6)
        np.testing.assert_allclose(result['ypr_deg'], pose.ypr_deg)
        np.testing.assert_allclose(result['ypr_std_deg'], pose.ypr_std_deg)
        # Rotating the body velocity into ENU should not change its magnitude.
        assert np.linalg.norm(result['velocity_enu_mps']) == pytest.approx(3.0)
        # Rotating the position covariance into ECEF should preserve its total variance.
        assert np.sum(result['position_std_ecef_m'] ** 2) == pytest.approx(np.sum(pose.position_std_enu_m ** 2))

    def test_matching_lever_arms_cancel(self):
        pose = _make_valid_pose()
        lever_arm_m = np.array([1.0, -0.5, 0.8])
        result = transform_pose_to_target(pose, lever_arm_m, lever_arm_m, ZERO, ZERO)
        np.testing.assert_allclose(result['position_ecef_m'], pm.geodetic2ecef(*pose.lla_deg), atol=1e-6)

    def test_target_lever_arm_offsets_position(self):
        pose = _make_valid_pose()
        result = transform_pose_to_target(pose, ZERO, np.array([1.0, 0.0, 0.0]), ZERO, ZERO)
        offset_m = result['position_ecef_m'] - np.array(pm.geodetic2ecef(*pose.lla_deg))
        assert np.linalg.norm(offset_m) == pytest.approx(1.0)

    def test_invalid_pose_passes_through_nan(self):
        result = transform_pose_to_target(PoseMessage(), ZERO, ZERO, np.array([90.0, 0.0, 0.0]), ZERO)
        for key, value in result.items():
            assert np.all(np.isnan(value)), key


class TestTransformedPoseToExternalPoseInput:
    def test_valid_pose(self):
        pose = _make_valid_pose()
        ext_pose = transformed_pose_to_external_pose_input(pose, transform_pose_to_target(pose, ZERO, ZERO, ZERO, ZERO))
        assert ext_pose.solution_type == SolutionType.RTKFixed
        assert ext_pose.details.measurement_time_source == SystemTimeSource.GPS_TIME
        assert float(ext_pose.details.measurement_time) == pytest.approx(1000.0)
        assert ext_pose.flags == ExternalPoseInput.FLAG_RESET_POSITION_DATA

    def test_reset_disabled(self):
        pose = _make_valid_pose()
        ext_pose = transformed_pose_to_external_pose_input(pose, transform_pose_to_target(pose, ZERO, ZERO, ZERO, ZERO),
                                                           reset_engine_position=False)
        assert ext_pose.flags == 0

    def test_invalid_pose(self):
        pose = PoseMessage()
        ext_pose = transformed_pose_to_external_pose_input(pose, transform_pose_to_target(pose, ZERO, ZERO, ZERO, ZERO))
        assert ext_pose.solution_type == SolutionType.Invalid
        assert ext_pose.details.measurement_time_source == SystemTimeSource.INVALID
        assert np.all(np.isnan(ext_pose.position_ecef_m))
        # Must still serialize cleanly so it can be forwarded.
        ext_pose.pack()
