#!/usr/bin/env python3

"""Proxy raw wheel/vehicle speed output from a source device to a target device as wheel/vehicle speed input.

This is useful when a vehicle has a "primary" device with a good connection to the vehicle's wheel speed or CAN
data (the source), and one or more other devices (targets) that need that same speed data but are not wired to
the vehicle themselves.
"""

from datetime import datetime
import os
import sys
import time

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine
# imports if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineDecoder, FusionEngineEncoder
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from fusion_engine_client.utils.time_provider import TimeProvider
from fusion_engine_client.utils.transport_utils import *

logger = logging.getLogger('point_one.fusion_engine.proxy_wheel_speed')

# Map each raw output message we forward to the corresponding input message class sent to the target device.
_INPUT_CLASS_BY_OUTPUT_TYPE = {
    MessageType.RAW_WHEEL_SPEED_OUTPUT: WheelSpeedInput,
    MessageType.RAW_VEHICLE_SPEED_OUTPUT: VehicleSpeedInput,
}

# Fields to copy directly from the source output message to the target input message. Both message types share
# the "gear" and "flags" fields; the speed field name(s) differ between wheel and vehicle speed messages.
_COPY_FIELDS_BY_OUTPUT_TYPE = {
    MessageType.RAW_WHEEL_SPEED_OUTPUT: (
        'front_left_speed_mps', 'front_right_speed_mps', 'rear_left_speed_mps', 'rear_right_speed_mps', 'gear',
        'flags'),
    MessageType.RAW_VEHICLE_SPEED_OUTPUT: ('vehicle_speed_mps', 'gear', 'flags'),
}


def build_input_message(source_message, use_gps_time, time_provider):
    """!
    @brief Convert a raw wheel/vehicle speed output message from the source device into the corresponding input
           message for the target device.

    Note that we intentionally do _not_ copy the source device's P1 time: P1 time is specific to each device and
    is not shared between them. Instead, we either let the target device timestamp the measurement when it is
    received, or, if requested, convert the source P1 time to GPS time so the target can align it more precisely with
    its own P1 time.

    @param source_message The received `RawWheelSpeedOutput` or `RawVehicleSpeedOutput` message.
    @param use_gps_time If `True`, timestamp the input message using GPS time derived from the source device's P1
           time. Otherwise, leave the timestamp unset so the target device timestamps it on reception.
    @param time_provider A `TimeProvider` used to convert source P1 time to GPS time when `use_gps_time` is
           enabled.

    @return The populated input message, or `None` if the message type is not supported.
    """
    input_class = _INPUT_CLASS_BY_OUTPUT_TYPE.get(source_message.get_type())
    if input_class is None:
        return None

    input_message = input_class()
    for field in _COPY_FIELDS_BY_OUTPUT_TYPE[source_message.get_type()]:
        setattr(input_message, field, getattr(source_message, field))

    input_message.details.data_source = source_message.details.data_source

    gps_time = None
    if use_gps_time:
        if source_message.details.measurement_time_source == SystemTimeSource.GPS_TIME:
            gps_time = source_message.details.measurement_time
        else:
            gps_time = time_provider.p1_to_gps(source_message.p1_time)

    if gps_time:
        input_message.details.measurement_time = gps_time
        input_message.details.measurement_time_source = SystemTimeSource.GPS_TIME
    else:
        if use_gps_time:
            logger.debug('GPS time not yet available. Falling back to timestamp on reception.')
        input_message.details.measurement_time_source = SystemTimeSource.INVALID

    return input_message


def main():
    parser = ArgumentParser(
        usage="%(prog)s SOURCE TARGET [TARGET...]",
        description="""\
Proxy raw wheel/vehicle speed output from a source device to a target device as wheel/vehicle speed input.

Connects to a source device and one or more target devices, enables raw wheel and vehicle speed output on the
source, and forwards each received measurement to every target as the corresponding input message.

Messages may be timestamped either using GPS time (default) or on reception by the target device (--use-gps-time=false).

Examples:
    # Proxy to a single target.
    ./proxy_wheel_speed.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201

    # Proxy to multiple targets.
    ./proxy_wheel_speed.py tcp://192.168.1.100:30202 tcp://192.168.1.200:30201 tcp://192.168.1.201:30201
""")

    parser.add_argument(
        'source', type=str,
        help="Source device transport (provides raw wheel/vehicle speed output).\n" + TRANSPORT_HELP_STRING)

    parser.add_argument(
        'target', type=str, nargs='+',
        help="One or more target device transports (each receives wheel/vehicle speed input).\n" +
             TRANSPORT_HELP_STRING)

    parser.add_argument(
        '--use-gps-time', action=ExtendedBooleanAction, default=True,
        help="""\
Timestamp forwarded measurements using GPS time instead of letting the target timestamp them on reception.""")

    parser.add_argument(
        '--summary-interval', type=float, default=5.0,
        help="Print a summary of forwarded messages every N seconds.")

    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
        stream=sys.stdout)

    if options.verbose == 0:
        logger.setLevel(logging.INFO)
    elif options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('point_one.fusion_engine.parsers').setLevel(
            logging.getTraceLevel(depth=options.verbose - 1))

    # Connect to the source and target devices.
    response_timeout_sec = 3.0
    try:
        source_transport = create_transport(options.source, timeout_sec=response_timeout_sec, print_func=logger.info)
    except Exception as e:
        logger.error(f"Failed to connect to source: {e}")
        sys.exit(1)

    target_transports = []
    for target in options.target:
        try:
            target_transports.append(
                create_transport(target, timeout_sec=response_timeout_sec, print_func=logger.info))
        except Exception as e:
            logger.error(f"Failed to connect to target '{target}': {e}")
            sys.exit(1)

    encoder = FusionEngineEncoder()

    # Ask the source device to send us raw wheel/vehicle speed output every time a new measurement is available. If
    # requested, also enable pose output so we can convert the source's P1 time to GPS time.
    message_types_to_enable = [MessageType.RAW_WHEEL_SPEED_OUTPUT, MessageType.RAW_VEHICLE_SPEED_OUTPUT]
    if options.use_gps_time:
        message_types_to_enable.append(MessageType.POSE)

    for message_type in message_types_to_enable:
        rate_request = SetMessageRate(output_interface=InterfaceID(TransportType.CURRENT),
                                      protocol=ProtocolType.FUSION_ENGINE, message_id=message_type,
                                      rate=MessageRate.ON_CHANGE)
        source_transport.send(encoder.encode_message(rate_request))

    logger.info("Connected. Waiting for wheel/vehicle speed data from source...")

    # Main loop.
    decoder = FusionEngineDecoder(return_bytes=False)
    time_provider = TimeProvider()

    messages_received = 0
    messages_forwarded = 0
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
                    if isinstance(message, PoseMessage):
                        time_provider.handle_message(message)
                        continue
                    elif not isinstance(message, (RawWheelSpeedOutput, RawVehicleSpeedOutput)):
                        continue

                    messages_received += 1

                    input_message = build_input_message(message, use_gps_time=options.use_gps_time,
                                                        time_provider=time_provider)
                    encoded_data = encoder.encode_message(input_message)
                    for target_transport in target_transports:
                        target_transport.send(encoded_data)
                    messages_forwarded += 1

                    logger.debug(f"Forwarded {message.get_type().name} -> {input_message.get_type().name} to "
                                f"{len(target_transports)} target(s).")

            now = datetime.now()
            if (now - last_summary_time).total_seconds() >= options.summary_interval:
                elapsed_sec = (now - start_time).total_seconds()
                logger.info(f"Elapsed: {elapsed_sec:.1f} sec, received: {messages_received}, "
                            f"forwarded: {messages_forwarded}")
                last_summary_time = now
    except KeyboardInterrupt:
        pass
    except (ConnectionError, OSError) as e:
        logger.error(f"Connection error: {e}")
    finally:
        source_transport.close()
        for target_transport in target_transports:
            target_transport.close()
        logger.info(f"Done. Forwarded {messages_forwarded} of {messages_received} received messages.")


if __name__ == "__main__":
    main()
