from typing import Dict

import numpy as np
import pymap3d as pm

from ..analysis.attitude import dcm_to_euler_angles, euler_angles_to_dcm, get_enu_rotation_matrix
from ..messages import ExternalPoseInput, PoseMessage, SystemTimeSource, Timestamp

# Coordinate frame abbreviations:
#   enu - Local navigation frame (East, North, Up)
#   ecef - Earth-Centered, Earth-Fixed frame
#   sb - Source body frame
#   tb - Target body frame


def calculate_ypr_enu_to_tb_deg(ypr_enu_to_sb_deg: np.ndarray, rotmat_tb_to_sb: np.ndarray) -> np.ndarray:
    """!
    @brief Calculate the target body attitude in the local ENU frame.

    @param ypr_enu_to_sb_deg The source body attitude in the ENU frame (YPR, degrees).
    @param rotmat_tb_to_sb The rotation matrix from the target body frame to the source body frame.

    @return The target body attitude in the ENU frame (YPR, degrees).
    """
    rotmat_enu_to_sb = \
        euler_angles_to_dcm(ypr_enu_to_sb_deg[::-1], order='321', deg=True)
    rotmat_sb_to_enu = rotmat_enu_to_sb.T
    rotmat_tb_to_enu = rotmat_sb_to_enu @ rotmat_tb_to_sb
    rpy = dcm_to_euler_angles(rotmat_tb_to_enu.T, order='321', deg=True)
    return rpy[::-1]


def calculate_jacobian_ypr_target_wrt_source(ypr_enu_to_sb_deg: np.ndarray, rotmat_tb_to_sb: np.ndarray,
                                             delta_deg: float = 1e-6) -> np.ndarray:
    """!
    @brief Numerically approximate the Jacobian of the target YPR with respect to the source YPR using central
           differences.

    @param ypr_enu_to_sb_deg The source body attitude in the ENU frame (YPR, degrees).
    @param rotmat_tb_to_sb The rotation matrix from the target body frame to the source body frame.
    @param delta_deg The perturbation applied to each source angle (degrees).

    @return A 3x3 Jacobian matrix.
    """
    jacobian = np.zeros((3, 3))
    for j in range(3):
        ypr_enu_to_sb_deg_plus = ypr_enu_to_sb_deg.copy()
        ypr_enu_to_sb_deg_minus = ypr_enu_to_sb_deg.copy()
        ypr_enu_to_sb_deg_plus[j] += delta_deg
        ypr_enu_to_sb_deg_minus[j] -= delta_deg
        ypr_enu_to_tb_deg_plus = \
            calculate_ypr_enu_to_tb_deg(ypr_enu_to_sb_deg_plus, rotmat_tb_to_sb)
        ypr_enu_to_tb_deg_minus = \
            calculate_ypr_enu_to_tb_deg(ypr_enu_to_sb_deg_minus, rotmat_tb_to_sb)
        jacobian[:, j] = \
            (ypr_enu_to_tb_deg_plus - ypr_enu_to_tb_deg_minus) / (2.0 * delta_deg)
    return jacobian


def transform_pose_to_target(source_pose_msg: PoseMessage,
                             source_lever_arm_m: np.ndarray, target_lever_arm_m: np.ndarray,
                             ypr_tb_to_sb_deg: np.ndarray, vec_tb_to_sb_m: np.ndarray) -> Dict[str, np.ndarray]:
    """!
    @brief Transform a source device's pose to the corresponding pose of a target device.

    Any unavailable (NaN) fields in the source pose are passed through as NaN in the result.

    @param source_pose_msg The @ref PoseMessage from the source device.
    @param source_lever_arm_m The source device's output lever arm in the source body frame (meters).
    @param target_lever_arm_m The target device's output lever arm in the target body frame (meters).
    @param ypr_tb_to_sb_deg The orientation of the target body frame relative to the source body frame (YPR, degrees).
    @param vec_tb_to_sb_m The translation of the target body frame relative to the source body frame (meters).

    @return A `dict` containing the target position/attitude/velocity and their standard deviations.
    """
    have_target_rot = not np.allclose(ypr_tb_to_sb_deg, 0.0)
    if have_target_rot:
        rotmat_tb_to_sb = \
            euler_angles_to_dcm(ypr_tb_to_sb_deg[::-1], order='321', deg=True)
    else:
        rotmat_tb_to_sb = np.eye(3)

    # ---------- Position ----------
    source_position_ecef_m = np.array(
        pm.geodetic2ecef(source_pose_msg.lla_deg[0],
                         source_pose_msg.lla_deg[1],
                         source_pose_msg.lla_deg[2]))

    rotmat_ecef_to_enu = get_enu_rotation_matrix(
        source_pose_msg.lla_deg[0], source_pose_msg.lla_deg[1], deg=True)
    rotmat_enu_to_ecef = rotmat_ecef_to_enu.T

    # We will still pass through NAN attitude, but for the sake of
    # the position transformation we can treat it as no rotation.
    ypr_enu_to_sb_deg = source_pose_msg.ypr_deg
    if np.any(np.isnan(ypr_enu_to_sb_deg)):
        rotmat_enu_to_sb = np.eye(3)
    else:
        rotmat_enu_to_sb = euler_angles_to_dcm(
            ypr_enu_to_sb_deg[::-1], order='321', deg=True)
    rotmat_sb_to_enu = rotmat_enu_to_sb.T
    rotmat_sb_to_ecef = rotmat_enu_to_ecef @ rotmat_sb_to_enu

    vec_tb_to_sb_in_ecef_m = rotmat_sb_to_ecef @ vec_tb_to_sb_m

    # Apply lever arm correction to get target output position in
    # ECEF.
    # target_position_ecef_m =
    #      source_position_ecef_m - (source lever arm in ECEF)
    #      + vec_tb_to_sb_in_ecef_m + (target lever arm in ECEF)
    target_position_ecef_m = source_position_ecef_m \
        - rotmat_sb_to_ecef @ source_lever_arm_m + vec_tb_to_sb_in_ecef_m \
        + rotmat_sb_to_ecef @ rotmat_tb_to_sb @ target_lever_arm_m

    source_position_enu_cov_m2 = np.diag(source_pose_msg.position_std_enu_m ** 2)
    target_position_ecef_cov_m2 = \
        rotmat_enu_to_ecef @ source_position_enu_cov_m2 @ rotmat_ecef_to_enu
    target_position_ecef_std_m = np.sqrt(np.diag(target_position_ecef_cov_m2))

    # ---------- Attitude ----------
    if have_target_rot and not np.any(np.isnan(ypr_enu_to_sb_deg)):
        # YPR does not transform linearly, so we need to
        # pre and post multiply by the Jacobian.
        ypr_enu_to_tb_deg = calculate_ypr_enu_to_tb_deg(
            ypr_enu_to_sb_deg, rotmat_tb_to_sb)
        jacobian = calculate_jacobian_ypr_target_wrt_source(
            ypr_enu_to_sb_deg, rotmat_tb_to_sb)
        ypr_enu_to_sb_cov_deg2 = np.diag(source_pose_msg.ypr_std_deg ** 2)
        ypr_enu_to_tb_cov_deg2 = jacobian @ ypr_enu_to_sb_cov_deg2 @ jacobian.T
        ypr_enu_to_tb_std_deg = np.sqrt(np.diag(ypr_enu_to_tb_cov_deg2))
    else:
        ypr_enu_to_tb_deg = ypr_enu_to_sb_deg.copy()
        ypr_enu_to_tb_std_deg = source_pose_msg.ypr_std_deg.copy()

    # ---------- Velocity ----------
    # IMPORTANT!: Assume target is not moving relative to source,
    # and that the source angular rate is zero, whether or not
    # the source velocity is non-zero.

    have_source_vel = not np.any(np.isnan(source_pose_msg.velocity_body_mps))
    if have_source_vel:
        velocity_sb_mps = source_pose_msg.velocity_body_mps
        # source_velocity_enu_mps = (source body velocity in ENU)
        #                           + (source velocity relative to source body in ENU)
        # Last term is assumed zero.
        source_velocity_enu_mps = rotmat_sb_to_enu @ velocity_sb_mps

        # target_velocity_enu_mps = source_velocity_enu_mps
        #                           + (target velocity wrt source in ENU)
        # Last term is assumed zero.
        target_velocity_enu_mps = source_velocity_enu_mps
        velocity_sb_cov_m2ps2 = np.diag(source_pose_msg.velocity_std_body_mps ** 2)
        target_velocity_enu_cov_m2ps2 = \
            rotmat_sb_to_enu @ velocity_sb_cov_m2ps2 @ rotmat_enu_to_sb
        target_velocity_enu_std_mps = \
            np.sqrt(np.diag(target_velocity_enu_cov_m2ps2))
    else:
        target_velocity_enu_mps = np.full(3, np.nan)
        target_velocity_enu_std_mps = np.full(3, np.nan)

    return {
        "position_ecef_m": target_position_ecef_m,
        "position_std_ecef_m": target_position_ecef_std_m,
        "ypr_deg": ypr_enu_to_tb_deg,
        "ypr_std_deg": ypr_enu_to_tb_std_deg,
        "velocity_enu_mps": target_velocity_enu_mps,
        "velocity_std_enu_mps": target_velocity_enu_std_mps,
    }


def transformed_pose_to_external_pose_input(source_pose_msg: PoseMessage, transformed_pose: Dict[str, np.ndarray],
                                            reset_engine_position: bool = True) -> ExternalPoseInput:
    """!
    @brief Package a transformed pose (see @ref transform_pose_to_target()) as an @ref ExternalPoseInput message.

    @param source_pose_msg The @ref PoseMessage from the source device, used for timing and solution type.
    @param transformed_pose The result from @ref transform_pose_to_target().
    @param reset_engine_position If `True`, set `FLAG_RESET_POSITION_DATA` so the target resets its position using this
           pose.

    @return The populated @ref ExternalPoseInput message.
    """
    ext_pose = ExternalPoseInput()

    # Timestamps.
    if source_pose_msg.gps_time:
        ext_pose.details.measurement_time = source_pose_msg.gps_time
        ext_pose.details.measurement_time_source = SystemTimeSource.GPS_TIME
    else:
        ext_pose.details.measurement_time = Timestamp()
        ext_pose.details.measurement_time_source = SystemTimeSource.INVALID

    ext_pose.solution_type = source_pose_msg.solution_type
    ext_pose.flags = ExternalPoseInput.FLAG_RESET_POSITION_DATA if reset_engine_position else 0

    ext_pose.position_ecef_m = transformed_pose["position_ecef_m"].astype(np.float64)
    ext_pose.position_std_ecef_m = transformed_pose["position_std_ecef_m"].astype(np.float32)

    ext_pose.ypr_deg = transformed_pose["ypr_deg"].astype(np.float32)
    ext_pose.ypr_std_deg = transformed_pose["ypr_std_deg"].astype(np.float32)

    ext_pose.velocity_enu_mps = transformed_pose["velocity_enu_mps"].astype(np.float32)
    ext_pose.velocity_std_enu_mps = transformed_pose["velocity_std_enu_mps"].astype(np.float32)

    return ext_pose
