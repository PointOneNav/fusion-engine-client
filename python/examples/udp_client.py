#!/usr/bin/env python3

import os
import socket
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.utils.argument_parser import ArgumentParser

from examples.client_implementation import define_arguments, run_client


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to a Point One device over UDP and print out the incoming message
contents and/or log the messages to disk.

When using UDP, you must configure the device to send data to your machine.
""")
    define_arguments(parser)
    parser.add_argument('-p', '--port', type=int, default=30400,
                        help="The FusionEngine UDP port on the data source.")
    parser.add_argument('hostname',
                        help="The IP address or hostname of the data source.")
    options = parser.parse_args()

    # Connect to the device.
    transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind(('', options.port))

    # Now run the client to listen for incoming data and decode/print the received message contents.
    run_client(options, transport)
