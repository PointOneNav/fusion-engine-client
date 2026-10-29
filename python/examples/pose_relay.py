#!/usr/bin/env python3

"""Relay a pose from a source device to a target device via ExternalPoseInput,
accounting for source/target lever arms and target body mounting with respect to
source body.
"""

from datetime import datetime
import os
import sys
import time

import numpy as np

# Add the Python root directory (fusion-engine-client/python/) to the import
# search path to enable FusionEngine imports if this application is being run
# directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import MessageType, PoseMessage
from fusion_engine_client.messages.defs import SolutionType, SourceIdentifier
from fusion_engine_client.parsers import FusionEngineDecoder, FusionEngineEncoder
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.bin_utils import bytes_to_hex
from fusion_engine_client.utils.pose_relay import transform_pose_to_target, transformed_pose_to_external_pose_input
from fusion_engine_client.utils.transport_utils import *

logger = logging.getLogger('point_one.fusion_engine.pose_relay')


def main():
    parser = ArgumentParser(description="""Relay pose from a source device to
a target device via ExternalPoseInput.

Connects to a source device, receives PoseMessage outputs, transforms the first
valid pose while accounting for lever arm differences and target mounting, and
sends an ExternalPoseInput message to the target device.

Lever arms are specified in each body frame (+x forward, +y left, +z up) for
each source and target, and represent the position of each device's output point
(i.e., the point whose position appears in the PoseMessage or ExternalPoseInput)
relative to the body origin.

Target rotation is specified as Yaw-Pitch-Roll (YPR, degrees), describing the
orientation of the target device's body frame relative to the source's body
frame. See @ref euler_angles_to_dcm for rotation convention details.

Target translation is specified as XYZ (meters), describing the position of the
target device's body frame origin relative to the source's body frame origin.

Examples:
    # Source at body origin, target at [1, 0, 0] (1m forward), no rotation
    # or translation:
    ./pose_relay.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 \\
        --target-lever-arm 1 0 0

    # Source output lever arm at [0.5, 0, 1.0], target at [1.0, -0.3, 0.8]:
    ./pose_relay.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 \\
        --source-lever-arm 0.5 0 1.0 --target-lever-arm 1.0 -0.3 0.8 \\

    # Target is rotated 90 degrees in yaw relative to vehicle body, and
    # translated 0.5m forward and 0.2m left relative to vehicle body:
    ./pose_relay.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 \\
        --target-rotation 90 0 0 --target-translation 0.5 0.2 0
""")

    parser.add_argument(
        'source', type=str,
        help="Source device transport (provides PoseMessage).\n" + TRANSPORT_HELP_STRING)

    parser.add_argument(
        'target', type=str,
        help="Target device transport (receives ExternalPoseInput).\n" + TRANSPORT_HELP_STRING)

    parser.add_argument(
        '--source-lever-arm', type=float, nargs=3, default=[0.0, 0.0, 0.0],
        metavar=('X', 'Y', 'Z'),
        help="""Output lever arm of the source device in the source vehicle's
body frame (meters). This is the position of the source device's reported output
point relative to the source vehicle body origin: [x_forward, y_left, z_up].""")

    parser.add_argument(
        '--target-lever-arm', type=float, nargs=3, default=[0.0, 0.0, 0.0],
        metavar=('X', 'Y', 'Z'),
        help="""Output lever arm of the target device in the target vehicle's
body frame (meters). This is the position of the target device's desired output
point relative to the target vehicle body origin: [x_forward, y_left, z_up].

This should match the output lever arm configured on the target device, so
that the ExternalPoseInput position corresponds to the point the target will
report in its own PoseMessage after initialization.""")

    parser.add_argument(
        '--target-rotation', type=float, nargs=3, default=[0.0, 0.0, 0.0],
        metavar=('YAW', 'PITCH', 'ROLL'),
        help="""Orientation of the target device body frame relative to the
source's body frame, specified as YPR (degrees). This describes how the target
device is mounted on the source vehicle. E.g., if the target is rotated 90
degrees in yaw relative to the source vehicle, specify: 90 0 0.""")

    parser.add_argument(
        '--target-translation', type=float, nargs=3, default=[0.0, 0.0, 0.0],
        metavar=('X', 'Y', 'Z'),
        help="""Translation of the target device body frame relative to the
source's body frame, specified as XYZ (meters). This describes how the target
device is mounted on the source vehicle. E.g., if the target is translated 1
meter forward relative to the source vehicle, specify: 1 0 0.""")

    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
        stream=sys.stderr)

    if options.verbose == 0:
        logger.setLevel(logging.INFO)
    elif options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)

    # Parse lever arms and transforms.
    # B - source body frame, b - target body frame, t - target output, s - source output
    source_lever_arm_m = np.array(options.source_lever_arm)
    target_lever_arm_m = np.array(options.target_lever_arm)

    # Target rotation.
    ypr_tb_to_sb_deg = np.array(options.target_rotation)

    # Target translation.
    vec_tb_to_sb_m = np.array(options.target_translation)

    logger.info(f"Source output lever arm: [{source_lever_arm_m[0]:.3f}, {source_lever_arm_m[1]:.3f}, {source_lever_arm_m[2]:.3f}] m")
    logger.info(f"Target output lever arm: [{target_lever_arm_m[0]:.3f}, {target_lever_arm_m[1]:.3f}, {target_lever_arm_m[2]:.3f}] m")
    logger.info(f"Target-to-source-body rotation: [{ypr_tb_to_sb_deg[0]:.1f}, {ypr_tb_to_sb_deg[1]:.1f}, {ypr_tb_to_sb_deg[2]:.1f}] deg")
    logger.info(f"Target-to-source-body translation: [{vec_tb_to_sb_m[0]:.3f}, {vec_tb_to_sb_m[1]:.3f}, {vec_tb_to_sb_m[2]:.3f}] m")

    # Connect to source and target.
    response_timeout_sec = 3.0
    try:
        source_transport = create_transport(options.source,
                                            timeout_sec=response_timeout_sec,
                                            print_func=logger.info)
    except Exception as e:
        logger.error(f"Failed to connect to source: {e}")
        sys.exit(1)

    try:
        target_transport = create_transport(options.target,
                                            timeout_sec=response_timeout_sec,
                                            print_func=logger.info)
    except Exception as e:
        logger.error(f"Failed to connect to target: {e}")
        sys.exit(1)

    logger.info("Connected. Waiting for pose messages from source...")

    # Main loop.
    decoder = FusionEngineDecoder(return_bytes=False)
    encoder = FusionEngineEncoder()

    start_time = datetime.now()

    poses_received = 0
    poses_forwarded = 0

    try:
        while True:
            # Need to specify read size or read waits for end of file character.
            # This returns immediately even if 0 bytes are available.
            received_data = recv_from_transport(source_transport, 64)

            if len(received_data) == 0:
                time.sleep(0.1)
                continue

            messages = decoder.on_data(received_data)
            for header, message in messages:
                if header.message_type != MessageType.POSE:
                    continue

                poses_received += 1
                source_pose_msg: PoseMessage = message

                logger.debug("Received pose message: \n" +
                             f"LLA Position: [{source_pose_msg.lla_deg[0]:.6f}, {source_pose_msg.lla_deg[1]:.6f}, {source_pose_msg.lla_deg[2]:.3f}] deg\n" +
                             f"Attitude: [{source_pose_msg.ypr_deg[0]:.1f}, {source_pose_msg.ypr_deg[1]:.1f}, {source_pose_msg.ypr_deg[2]:.1f}] deg\n" +
                             f"Body Velocity: [{source_pose_msg.velocity_body_mps[0]:.2f}, {source_pose_msg.velocity_body_mps[1]:.2f}, {source_pose_msg.velocity_body_mps[2]:.2f}] m/s\n" +
                             "Attempting to transform and forward...")

                if source_pose_msg.solution_type == SolutionType.Invalid:
                    logger.debug("Skipping invalid pose solution.")
                    continue

                if np.any(np.isnan(source_pose_msg.lla_deg)):
                    logger.debug("Skipping pose with NaN position.")
                    continue

                if np.linalg.norm(source_pose_msg.velocity_body_mps) > 0.1:
                    logger.warning(
                        "Source velocity is non-zero. We assume no relative motion between source and target. "
                        "If the target is moving relative to the source, relayed velocity will be incorrect."
                    )

                transformed_pose = transform_pose_to_target(
                    source_pose_msg, source_lever_arm_m, target_lever_arm_m,
                    ypr_tb_to_sb_deg, vec_tb_to_sb_m)

                ext_pose = transformed_pose_to_external_pose_input(
                    source_pose_msg, transformed_pose)

                # Encode and send.
                encoded_data = encoder.encode_message(
                    ext_pose,
                    source_identifier=SourceIdentifier.OUTPUT_LEVER_ARM)
                logger.debug(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))

                target_transport.send(encoded_data)

                poses_forwarded += 1
                logger.info(
                    f"Forwarded pose: "
                    f"ECEF Position: [{transformed_pose['position_ecef_m'][0]:.2f}, {transformed_pose['position_ecef_m'][1]:.2f}, {transformed_pose['position_ecef_m'][2]:.2f}] m, "
                    f"Attitude: [{transformed_pose['ypr_deg'][0]:.1f}, {transformed_pose['ypr_deg'][1]:.1f}, {transformed_pose['ypr_deg'][2]:.1f}] deg, "
                    f"ENU Velocity: [{transformed_pose['velocity_enu_mps'][0]:.2f}, {transformed_pose['velocity_enu_mps'][1]:.2f}, {transformed_pose['velocity_enu_mps'][2]:.2f}] m/s")
                break

            if poses_forwarded > 0:
                break

        source_transport.close()
        target_transport.close()

    except KeyboardInterrupt:
        pass
    finally:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Done. Pose relayed in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()
