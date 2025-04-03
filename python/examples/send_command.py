#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineDecoder, FusionEngineEncoder
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.bin_utils import bytes_to_hex
from fusion_engine_client.utils.transport_utils import *


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Send a command to a Point One device and wait for a response.
""")

    parser.add_argument(
        '-i', '--ignore-response', action='store_true',
        help="Do not wait for a response from the device.")

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
    response_timeout_sec = 3.0

    try:
        transport = create_transport(options.transport, timeout_sec=response_timeout_sec, print_func=logger.info)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    # Specify the message to be sent.
    message = ResetRequest(reset_mask=ResetRequest.HOT_START)
    # message = SetConfigMessage(GNSSLeverArmConfig(0.4, 0.0, 1.2))
    # message = GetConfigMessage(GNSSLeverArmConfig)
    # message = SetConfigMessage(EnabledGNSSSystemsConfig(SatelliteType.GPS, SatelliteType.GALILEO))
    # message = SetMessageRate(output_interface=InterfaceID(TransportType.SERIAL, 1),
    #                          protocol=ProtocolType.FUSION_ENGINE,
    #                          message_id=MessageType.POSE,
    #                          rate=MessageRate.ON_CHANGE)
    # message = SetConfigMessage(InterfaceDiagnosticMessagesEnabled(True),
    #                            interface=InterfaceID(TransportType.TCP, 0))
    # message = GetConfigMessage(InterfaceDiagnosticMessagesEnabled,
    #                            interface=InterfaceID(TransportType.TCP, 0))
    # message = SetConfigMessage(
    #     TCPConfig(direction=TransportDirection.CLIENT, remote_address='remote-hostname', port=1234),
    #     interface=InterfaceID(TransportType.TCP, 1))
    # message = FaultControlMessage(payload=FaultControlMessage.EnableGNSS(False))

    # Send the command.
    logger.info("Sending message:\n%s" % str(message))

    encoder = FusionEngineEncoder()
    encoded_data = encoder.encode_message(message)
    logger.debug(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))

    transport.send(encoded_data)

    # Listen for the response.
    decoder = FusionEngineDecoder(warn_on_unrecognized=False, return_bytes=True)
    response = Response.OK if options.ignore_response else None
    start_time = datetime.now()
    while response is None:
        if (datetime.now() - start_time).total_seconds() > response_timeout_sec:
            logger.error("Timed out waiting for a response.")
            break

        try:
            received_data = transport.recv(1024)
        except socket.timeout:
            logger.error("Timed out waiting for a response.")
            break
        except KeyboardInterrupt:
            break

        messages = decoder.on_data(received_data)
        for header, message, encoded_data in messages:
            if isinstance(message, (CommandResponseMessage, ConfigResponseMessage)):
                logger.info("Received response:\n%s" % str(message))
                logger.debug(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))
                response = message.response
                break

    transport.close()

    if response == Response.OK:
        sys.exit(0)
    else:
        sys.exit(3)
