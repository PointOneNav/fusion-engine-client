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
Connect to a Point One device over TCP and print out the incoming message
contents and/or log the messages to disk.
""")
    define_arguments(parser)
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the data source.")
    parser.add_argument('hostname',
                        help="The IP address or hostname of the data source.")
    options = parser.parse_args()

    # Connect to the device.
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((socket.gethostbyname(options.hostname), options.port))

    # Now run the client to listen for incoming data and decode/print the received message contents.
    run_client(options, transport)
