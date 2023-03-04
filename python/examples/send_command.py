#!/usr/bin/env python3

import os
import socket
import sys
from urllib.parse import urlparse

try:
    import serial
except ImportError:
    serial = None

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineDecoder, FusionEngineEncoder
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.bin_utils import bytes_to_hex


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

    parser.add_argument('device',
                        help="""\
The path to the target FusionEngine device:
- [serial://]<device>[:<baud>] - Send over serial (baud rate defaults to 460800).
- tcp://<hostname>[:<port>] - Send over TCP (port defaults to 30201).
""".strip())
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

    # Specify the message to be sent.
    message = ResetRequest(reset_mask=ResetRequest.HOT_START)
    # message = SetConfigMessage(GNSSLeverArmConfig(0.4, 0.0, 1.2))
    # message = GetConfigMessage(GNSSLeverArmConfig)
    # message = SetConfigMessage(EnabledGNSSSystemsConfig(SatelliteType.GPS, SatelliteType.GALILEO))
    # message = SetMessageRate(output_interface=InterfaceID(TransportType.SERIAL, 1),
    #                          protocol=ProtocolType.FUSION_ENGINE,
    #                          message_id=MessageType.POSE,
    #                          rate=MessageRate.ON_CHANGE)
    # message = FaultControlMessage(payload=FaultControlMessage.EnableGNSS(False))

    # Connect to the device.
    url = urlparse(options.device)

    if url.scheme == "":
        url = url._replace(scheme="serial")

    if url.hostname is None:
        parts = url.path.split(":")
        hostname = parts[0]
        if len(parts) > 1:
            port = int(parts[1])
        else:
            port = None
    else:
        hostname = url.hostname
        port = url.port

    response_timeout_sec = 3.0
    serial_port = None
    sock = None
    if url.scheme == 'serial':
        if serial is None:
            logger.error("Serial port access requires pyserial. Please install (pip install pyserial) and run again.")
            sys.exit(1)

        baud_rate = 460800 if port is None else port
        path = hostname
        if path == "":
            logger.error("You must specify the path to a serial device.")
            sys.exit(2)

        logger.info("Sending command to serial port %s @ %d baud." % (path, baud_rate))
        serial_port = serial.Serial(port=path, baudrate=baud_rate, timeout=response_timeout_sec)
    elif url.scheme == 'tcp':
        port = 30201 if port is None else port
        if hostname == "":
            logger.error("You must specify a hostname or IP address.")
            sys.exit(2)

        ip_address = socket.gethostbyname(hostname)
        logger.info("Sending command to tcp://%s:%d." % (ip_address, port))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip_address, port))
        sock.settimeout(response_timeout_sec)
    else:
        logger.error("Unsupported device specifier.")
        sys.exit(2)

    # Send the command.
    logger.info("Sending message:\n%s" % str(message))

    encoder = FusionEngineEncoder()
    encoded_data = encoder.encode_message(message)

    logger.debug(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))

    if serial_port:
        serial_port.write(encoded_data)
    else:
        sock.send(encoded_data)

    # Listen for the response.
    decoder = FusionEngineDecoder(warn_on_unrecognized=False, return_bytes=True)
    response = Response.OK if options.ignore_response else None
    start_time = datetime.now()
    while response is None:
        if (datetime.now() - start_time).total_seconds() > response_timeout_sec:
            logger.error("Timed out waiting for a response.")
            break

        try:
            if serial_port:
                received_data = serial_port.read(1024)
                if len(received_data) == 0:
                    logger.error("Timed out waiting for a response.")
                    break
            else:
                received_data = sock.recv(1024)
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

    if serial_port:
        serial_port.close()
    else:
        sock.close()

    if response == Response.OK:
        sys.exit(0)
    else:
        sys.exit(3)
