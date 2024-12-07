#!/usr/bin/env python3

import os
import sys

try:
    import serial
except ImportError:
    print("This application requires pyserial. Please install (pip install pyserial) and run again.")
    sys.exit(1)

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.utils.argument_parser import ArgumentParser

from examples.client_implementation import define_arguments, run_client


if __name__ == "__main__":
    # Parse command-line arguments.
    parser = ArgumentParser(description="""\
Connect to a Point One device over serial and print out the incoming message
contents and/or log the messages to disk.
""")
    define_arguments(parser)
    parser.add_argument('-b', '--baud', type=int, default=460800,
                        help="The serial baud rate to be used.")
    parser.add_argument('port',
                        help="The serial device to use (e.g., /dev/ttyUSB0, COM1)")
    options = parser.parse_args()

    # Connect to the device.
    transport = serial.Serial(port=options.port, baudrate=options.baud)

    # Now run the client to listen for incoming data and decode/print the received message contents.
    run_client(options, transport)
