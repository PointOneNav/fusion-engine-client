#!/usr/bin/env python3

import os
import socket
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.messages import MessagePayload
from fusion_engine_client.parsers import FusionEngineDecoder


if __name__ == "__main__":
    # Parse command-line arguments.
    parser = ArgumentParser(description="""\
Connect to a Point One device over TCP and print out the incoming message
contents.
""")
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the data source.")
    parser.add_argument('hostname',
                        help="The IP address or hostname of the data source.")
    options = parser.parse_args()

    # Connect to the device.
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((socket.gethostbyname(options.hostname), options.port))

    # Listen for incoming data and parse FusionEngine messages.
    try:
        decoder = FusionEngineDecoder()
        while True:
            received_data = transport.recv(1024)
            messages = decoder.on_data(received_data)
            for header, message in messages:
                if isinstance(message, MessagePayload):
                    print(str(message))
                else:
                    print(f'{header.message_type} message (not supported)')
    except KeyboardInterrupt:
        pass

    # Close the transport when finished.
    transport.close()
