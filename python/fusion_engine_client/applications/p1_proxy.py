#!/usr/bin/env python3

import argparse
from argparse import Namespace
from datetime import datetime
import sys
import threading
import time
from typing import Callable, Dict, List, Optional, Set, Tuple, Type

import numpy as np

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import FusionEngineDecoder, FusionEngineEncoder
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.pose_relay import transform_pose_to_target, transformed_pose_to_external_pose_input
from ..utils.time_provider import TimeProvider
from ..utils.trace import BrokenPipeStreamHandler, HighlightFormatter
from ..utils.transport_utils import *

_logger = logging.getLogger('point_one.fusion_engine.applications.p1_proxy')

# Map each raw output message we forward to the corresponding input message class sent to the target device.
_INPUT_CLASS_BY_OUTPUT_TYPE: Dict[MessageType, Type[MessagePayload]] = {
    MessageType.RAW_WHEEL_SPEED_OUTPUT: WheelSpeedInput,
    MessageType.RAW_VEHICLE_SPEED_OUTPUT: VehicleSpeedInput,
    MessageType.RAW_IMU_OUTPUT: IMUInput,
    MessageType.POSE: ExternalPoseInput,
}

# Fields copied from each raw output message to its corresponding input message.
_COPY_FIELDS_BY_OUTPUT_TYPE: Dict[MessageType, Tuple[str, ...]] = {
    MessageType.RAW_WHEEL_SPEED_OUTPUT: (
        'front_left_speed_mps', 'front_right_speed_mps', 'rear_left_speed_mps', 'rear_right_speed_mps', 'gear',
        'flags'),
    MessageType.RAW_VEHICLE_SPEED_OUTPUT: ('vehicle_speed_mps', 'gear', 'flags'),
    MessageType.RAW_IMU_OUTPUT: ('temperature_degc', 'accel_mps2', 'gyro_rps'),
}

# Forwardable message types, by name.
_MESSAGE_TYPE_BY_NAME: Dict[str, MessageType] = {
    'WheelSpeedOutput': MessageType.RAW_WHEEL_SPEED_OUTPUT,
    'VehicleSpeedOutput': MessageType.RAW_VEHICLE_SPEED_OUTPUT,
    'IMUOutput': MessageType.RAW_IMU_OUTPUT,
    'Pose': MessageType.POSE,
}

# Shorthand aliases accepted in addition to the full message names above.
_MESSAGE_TYPE_SHORTHANDS: Dict[str, MessageType] = {
    'wheel': MessageType.RAW_WHEEL_SPEED_OUTPUT,
    'vehicle': MessageType.RAW_VEHICLE_SPEED_OUTPUT,
    'imu': MessageType.RAW_IMU_OUTPUT,
    'pose': MessageType.POSE,
}


def parse_message_types(value: str) -> Set[MessageType]:
    """!
    @brief Parse a comma-separated list of message type names to forward.

    @param value The raw command-line string, e.g. "WheelSpeedOutput,IMUOutput" or the shorthand "wheel,imu". Names
           are case-insensitive. 'all' or '' selects every supported type.

    @return The set of `MessageType`s to forward.
    """
    if value.strip().lower() in ('all', ''):
        return set(_MESSAGE_TYPE_BY_NAME.values())

    types_by_name = {name.lower(): message_type for name, message_type in _MESSAGE_TYPE_BY_NAME.items()}
    types_by_name.update(_MESSAGE_TYPE_SHORTHANDS)

    selected = set()
    for name in value.split(','):
        name = name.strip()
        message_type = types_by_name.get(name.lower())
        if message_type is None:
            valid = ', '.join(list(_MESSAGE_TYPE_BY_NAME.keys()) + list(_MESSAGE_TYPE_SHORTHANDS.keys()))
            raise argparse.ArgumentTypeError(f"unsupported message type '{name}'. Valid options: {valid}, or 'all'.")
        selected.add(message_type)
    return selected


def parse_vec3(value: str) -> np.ndarray:
    """!
    @brief Parse a comma-separated "X,Y,Z" string into a 3-element float array.

    @param value The raw command-line string, e.g. "1.0,2.0,3.0".

    @return A 3-element `np.ndarray` of floats.
    """
    parts = value.split(',')
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(f"expected 3 comma-separated numbers (e.g. '1.0,2.0,3.0'), got '{value}'")
    try:
        return np.array([float(p) for p in parts])
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected 3 comma-separated numbers (e.g. '1.0,2.0,3.0'), got '{value}'")


def build_input_message(source_message: MessagePayload, options: Namespace, time_provider: TimeProvider,
                        reset_engine_position: bool = False) -> Optional[MessagePayload]:
    """!
    @brief Convert a raw output message from the source device into the corresponding input message for the target
           device.

    Note that we intentionally do _not_ copy the source device's P1 time: P1 time is specific to each device and
    is not shared between them. Instead, we either let the target device timestamp the measurement when it is
    received, or, if requested, convert the source P1 time to GPS time so the target can align it more precisely with
    its own P1 time.

    A pose message is transformed to the target device's lever arm and mounting (see the pose options) and always uses
    the source's GPS time.

    @param source_message The received raw output message (see `_INPUT_CLASS_BY_OUTPUT_TYPE` for supported types).
    @param options The parsed command line options. If `options.use_gps_time` is `True`, timestamp the input message
           using GPS time derived from the source device's P1 time. Otherwise, leave the timestamp unset so the target
           device timestamps it on reception. Pose messages are transformed using `options.source_lever_arm`,
           `options.target_lever_arm`, `options.target_rotation`, and `options.target_translation`.
    @param time_provider A `TimeProvider` used to convert source P1 time to GPS time when `options.use_gps_time` is
           enabled.
    @param reset_engine_position If `True`, a pose input message requests that the target device reset its position
           using the pose. Ignored for other message types.

    @return The populated input message, or `None` if the message type is not supported.
    """
    input_class = _INPUT_CLASS_BY_OUTPUT_TYPE.get(source_message.get_type())
    if input_class is None:
        return None

    if source_message.get_type() == MessageType.POSE:
        transformed_pose = transform_pose_to_target(
            source_message, options.source_lever_arm, options.target_lever_arm, options.target_rotation,
            options.target_translation)
        return transformed_pose_to_external_pose_input(
            source_message, transformed_pose, reset_engine_position=reset_engine_position)

    input_message = input_class()
    for field in _COPY_FIELDS_BY_OUTPUT_TYPE[source_message.get_type()]:
        setattr(input_message, field, getattr(source_message, field))

    input_message.details.data_source = source_message.details.data_source

    gps_time = None
    if options.use_gps_time:
        if source_message.details.measurement_time_source == SystemTimeSource.GPS_TIME:
            gps_time = source_message.details.measurement_time
        else:
            gps_time = time_provider.p1_to_gps(source_message.p1_time)

    if gps_time:
        input_message.details.measurement_time = gps_time
        input_message.details.measurement_time_source = SystemTimeSource.GPS_TIME
    else:
        if options.use_gps_time:
            _logger.debug('GPS time not yet available. Falling back to timestamp on reception.')
        input_message.details.measurement_time_source = SystemTimeSource.INVALID

    return input_message


class Target:
    """!
    @brief A target device that is connected in the background and reconnected automatically if it goes away.

    A target that fails to connect, or that fails while being sent to, does not affect the other targets. It is retried
    every @ref _RETRY_INTERVAL_SEC until it comes back. Data is dropped for a target while it is disconnected.
    """

    _RETRY_INTERVAL_SEC = 5.0

    def __init__(self, descriptor: str, timeout_sec: float):
        self.descriptor = descriptor
        self._timeout_sec = timeout_sec
        self._transport: Optional[TransportClass] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._reconnect_loop, name=f'target-{descriptor}', daemon=True)

    @property
    def connected(self) -> bool:
        return self._transport is not None

    def start(self):
        self._try_connect(print_func=_logger.info)
        self._thread.start()

    def _try_connect(self, print_func: Callable = None):
        try:
            transport = create_transport(self.descriptor, timeout_sec=self._timeout_sec, print_func=print_func,
                                         mode='output')
        except Exception as e:
            # Only log the first failure of an outage so we don't spam while a target is down.
            if print_func is not None:
                _logger.warning(f"Failed to connect to target '{self.descriptor}': {e}. "
                                f"Retrying every {self._RETRY_INTERVAL_SEC:g} sec.")
            return

        with self._lock:
            if self._stop_event.is_set():
                transport.close()
                return
            self._transport = transport

        if print_func is None:
            _logger.info(f"Reconnected to target '{self.descriptor}'.")

    def _reconnect_loop(self):
        while not self._stop_event.wait(self._RETRY_INTERVAL_SEC):
            if self._transport is None:
                self._try_connect()

    def send(self, data: bytes) -> bool:
        """!
        @brief Send data to the target if it is connected.

        @param data The data to send.

        @return `True` if the data was sent.
        """
        transport = self._transport
        if transport is None:
            return False

        try:
            transport.send(data)
        except OSError as e:
            with self._lock:
                if self._transport is transport:
                    self._transport = None
            transport.close()
            _logger.warning(f"Lost connection to target '{self.descriptor}': {e}. "
                            f"Retrying every {self._RETRY_INTERVAL_SEC:g} sec.")
            return False

        return True

    def close(self):
        self._stop_event.set()
        with self._lock:
            transport, self._transport = self._transport, None
        if transport is not None:
            transport.close()


def main() -> None:
    parser = ArgumentParser(description="""\
Proxy raw measurement output from a source device to one or more targets as the corresponding input message.

Connects to a source device and one or more targets, enables output for the messages to be proxied (e.g., wheel speed,
IMU), and forwards each received measurement to every target as the corresponding input message. Pose output is
forwarded as ExternalPoseInput, optionally transformed to account for the target's lever arm and mounting (see the Pose
options below).

A target that is unreachable at startup, or that disconnects later, does not stop the proxy: it is retried every few
seconds and data is dropped for it in the meantime. The source is required, and the proxy exits if it is lost.

Messages may be timestamped either using GPS time (default) or on reception by the target device (--use-gps-time=false).

Examples:
  # Proxy to a single target device.
  ./p1_proxy.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201

  # Proxy to multiple target devices.
  ./p1_proxy.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 tcp://192.168.1.201:30201

  # Proxy only wheel speed and IMU measurements.
  ./p1_proxy.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 -m wheel,imu

  # Listen on port 30303 for any number of FusionEngine applications/devices to connect to this proxy, rather than
  # connecting out to a target device.
  ./p1_proxy.py tcp://192.168.1.100:30202 tcp://:30303
""")

    shorthand_by_type = {message_type: name for name, message_type in _MESSAGE_TYPE_SHORTHANDS.items()}
    supported_types = '\n'.join(f'- {name} ({shorthand_by_type[message_type]})'
                                for name, message_type in _MESSAGE_TYPE_BY_NAME.items())

    parser.add_argument(
        'source', type=str,
        help="Source device transport (provides raw measurement output).\n" + TRANSPORT_HELP_STRING)
    parser.add_argument(
        'target', type=str, nargs='+',
        help="One or more target transports (each receives measurement input). Use tcp://:<port> to listen for "
             "incoming connections instead of connecting out to a target; any number of clients may connect and "
             "disconnect at any time, and all of them receive the data.\n" + TRANSPORT_HELP_STRING)

    parser.add_argument(
        '-m', '--message-type', type=parse_message_types, action='append',
        help="""\
The message types to forward. May be specified multiple times (-m wheel -m imu), or as a comma-separated list
(-m wheel,imu). All matches are case-insensitive. If not specified, all supported types are forwarded.

Supported types:
%s""" % supported_types)
    parser.add_argument(
        '--use-gps-time', action=ExtendedBooleanAction, default=True,
        help="""\
Timestamp forwarded wheel speed, vehicle speed, and IMU measurements using GPS time instead of letting the target
timestamp them on reception. Pose is always timestamped using the source's GPS time when available.""")
    parser.add_argument(
        '--summary-interval', type=float, default=5.0,
        help="Print a summary of forwarded messages every N seconds.")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    pose_group = parser.add_argument_group('Pose')
    pose_group.add_argument(
        '--pose-rate', choices=('10hz', '100hz'), default='10hz',
        help="""\
Pose output rate requested from the source device: '10hz' (MessageRate.INTERVAL_100_MS) or '100hz'
(MessageRate.INTERVAL_10_MS).""")
    pose_group.add_argument(
        '--reset-target-position', action='store_true',
        help="""\
Set the reset position flag on the first pose forwarded after startup, causing each target to reset its position using
that pose. By default, poses are forwarded as normal updates without resetting the target.""")
    pose_group.add_argument(
        '--source-lever-arm', type=parse_vec3, default='0,0,0', metavar='X,Y,Z',
        help="""\
Output lever arm of the source device in the source vehicle's body frame (meters), as x_forward,y_left,z_up (e.g.,
'0.5,0,1.0').""")
    pose_group.add_argument(
        '--target-lever-arm', type=parse_vec3, default='0,0,0', metavar='X,Y,Z',
        help="""\
Output lever arm of the target device in the target vehicle's body frame (meters), as x_forward,y_left,z_up. Should
match the target's own configured output lever arm.""")
    pose_group.add_argument(
        '--target-rotation', type=parse_vec3, default='0,0,0', metavar='YAW,PITCH,ROLL',
        help="""\
Orientation of the target device body frame relative to the source's body frame (YPR, degrees) -- how the target is
mounted on the source vehicle (e.g., '90,0,0').""")
    pose_group.add_argument(
        '--target-translation', type=parse_vec3, default='0,0,0', metavar='X,Y,Z',
        help="""\
Translation of the target device body frame relative to the source's body frame (meters, XYZ) -- how the target is
mounted on the source vehicle.""")

    options = parser.parse_args()

    if options.message_type:
        message_types = set().union(*options.message_type)
    else:
        message_types = set(_MESSAGE_TYPE_BY_NAME.values())

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        _logger.setLevel(logging.DEBUG)
        if options.verbose > 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)
    BrokenPipeStreamHandler.install()

    # Connect to the source device and each target. A tcp://:<port> target listens in the background and does not
    # block waiting for a client to connect.
    response_timeout_sec = 3.0
    try:
        source_transport: TransportClass = create_transport(
            options.source, timeout_sec=response_timeout_sec, print_func=_logger.info)
    except Exception as e:
        _logger.error(f"Failed to connect to source: {e}")
        sys.exit(1)

    # A target that fails to connect does not stop the proxy; it is retried in the background.
    targets = [Target(descriptor, response_timeout_sec) for descriptor in options.target]
    for target in targets:
        target.start()

    encoder = FusionEngineEncoder()

    # Request raw measurement output from the source as each measurement becomes available, and pose output at
    # --pose-rate.
    for message_type in _MESSAGE_TYPE_BY_NAME.values():
        if message_type not in message_types:
            continue

        if message_type == MessageType.POSE:
            rate = MessageRate.INTERVAL_100_MS if options.pose_rate == '10hz' else MessageRate.INTERVAL_10_MS
        else:
            rate = MessageRate.ON_CHANGE

        rate_request = SetMessageRate(output_interface=InterfaceID(TransportType.CURRENT),
                                      protocol=ProtocolType.FUSION_ENGINE, message_id=message_type, rate=rate)
        source_transport.send(encoder.encode_message(rate_request))

    _logger.info("Connected. Waiting for measurement data from source...")

    # Main loop.
    decoder = FusionEngineDecoder(return_bytes=False)
    time_provider = TimeProvider()

    messages_received = 0
    messages_forwarded = 0
    reset_position_pending = options.reset_target_position
    start_time = datetime.now()
    last_summary_time = start_time

    try:
        while True:
            # Need to specify a read size or read waits for end of file. This returns immediately even if 0 bytes
            # are available.
            received_data = recv_from_transport(source_transport, 64)
            if len(received_data) == 0:
                time.sleep(0.1)
            else:
                for _, message in decoder.on_data(received_data):
                    messages_received += 1

                    if isinstance(message, PoseMessage):
                        # Always track the source device P1/GPS time relationship, even if Pose isn't being
                        # forwarded, so other measurements can be timestamped in GPS time.
                        time_provider.handle_message(message)

                    # Skip messages that weren't selected with --message-type.
                    if message.get_type() not in message_types:
                        continue

                    input_message = build_input_message(message, options, time_provider,
                                                        reset_engine_position=reset_position_pending)
                    if isinstance(message, PoseMessage):
                        # Only the first pose forwarded after startup resets the targets.
                        reset_position_pending = False

                    encoded_data = encoder.encode_message(input_message)
                    num_sent = sum(target.send(encoded_data) for target in targets)
                    messages_forwarded += 1

                    _logger.debug(f"Forwarded {message.get_type().name} -> {input_message.get_type().name} to "
                                  f"{num_sent} of {len(targets)} target(s).")

            now = datetime.now()
            if (now - last_summary_time).total_seconds() >= options.summary_interval:
                elapsed_sec = (now - start_time).total_seconds()
                _logger.info(f"Elapsed: {elapsed_sec:.1f} sec, received: {messages_received}, "
                             f"forwarded: {messages_forwarded}")
                last_summary_time = now
    except KeyboardInterrupt:
        pass
    except (ConnectionError, OSError) as e:
        _logger.error(f"Connection error: {e}")
    finally:
        source_transport.close()
        for target in targets:
            target.close()
        _logger.info(f"Done. Forwarded {messages_forwarded} of {messages_received} received messages.")


if __name__ == "__main__":
    main()
