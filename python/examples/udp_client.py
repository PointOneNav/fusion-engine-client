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
Connect to a Point One device over UDP and print out the incoming message
contents.

When using UDP, you must configure the device to send data to your machine.
""")
    parser.add_argument('-p', '--port', type=int, default=30400,
                        help="The FusionEngine UDP port on the data source.")
    options = parser.parse_args()

    # Connect to the device.
    transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind(('', options.port))

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
