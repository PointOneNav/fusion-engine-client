#!/usr/bin/env python3

import os
import sys
import time

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.bin_utils import bytes_to_hex
from fusion_engine_client.utils.transport_utils import *


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Send example vehicle/wheel speed measurements to a Point One device at a fixed
rate.
""")

    parser.add_argument(
        '-i', '--interval', type=float, default=1.0,
        help="The message interval (in seconds).")
    parser.add_argument(
        '-t', '--type', choices=('vehicle', 'wheel', 'one_wheel'), default='vehicle',
        help="""\
Specify the type of speed message to be sent to the device:
- on_wheel - Send a WheelSpeedInput message with a single speed for the
  front-right wheel
- vehicle - Send a VehicleSpeedInput message with a single speed value
- wheel - Send a WheelSpeedInput message with a speed values for each wheel
""")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    parser.add_argument(
        'transport', type=str,
        help=TRANSPORT_HELP_STRING)

    options = parser.parse_args()

    # Configure output logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s', stream=sys.stdout)
    logger = logging.getLogger('point_one.fusion_engine.app')

    if options.verbose == 0:
        logger.setLevel(logging.INFO)
    elif options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif options.verbose == 2:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('point_one.fusion_engine.parsers').setLevel(
            logging.getTraceLevel(depth=options.verbose - 1))

    # Connect to the device using the specified transport.
    try:
        transport = create_transport(options.transport, print_func=logger.info, timeout_sec=3.0)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    # Specify the message to be sent.
    if options.type == 'vehicle':
        message = VehicleSpeedInput()
        message.vehicle_speed_mps = 1
    elif options.type == 'wheel':
        message = WheelSpeedInput()
        message.front_right_speed_mps = 1
        message.front_left_speed_mps = 1
        message.rear_right_speed_mps = 1
        message.rear_left_speed_mps = 1
    elif options.type == 'one_wheel':
        message = WheelSpeedInput()
        message.front_right_speed_mps = 1
    else:
        logger.error(f"Unrecognized message type '{options.type}'.")
        sys.exit(2)

    encoder = FusionEngineEncoder()

    try:
        while True:
            logger.info("Sending message:\n%s" % str(message))

            encoded_data = encoder.encode_message(message)
            logger.debug(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))

            transport.send(encoded_data)
            time.sleep(options.interval)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
