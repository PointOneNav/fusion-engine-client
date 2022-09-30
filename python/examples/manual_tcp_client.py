#!/usr/bin/env python3

import os
import socket
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.argument_parser import ArgumentParser

from examples.manual_message_decode import decode_message


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to an Point One device over TCP and print out the incoming message
contents and/or log the messages to disk.

This example interprets the incoming data directly, and does not use the
FusionEngineDecoder class. The incoming data stream must contain only
FusionEngine messages. See also tcp_client.py.
""")
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the data source.")
    parser.add_argument('hostname',
                        help="The IP address or hostname of the data source.")
    options = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((socket.gethostbyname(options.hostname), options.port))

    received_data = b''
    current_header = None
    current_offset = 0
    while True:
        # Read some data.
        try:
            new_data = sock.recv(1024)
        except KeyboardInterrupt:
            break

        received_data += new_data

        # Process all complete packets in the stream.
        while True:
            # Wait for a complete message header.
            if current_header is None:
                if len(received_data) - current_offset < MessageHeader._SIZE:
                    # No more complete packets in the buffer. Discard any data that was already processed.
                    received_data = received_data[current_offset:]
                    current_offset = 0
                    break
                else:
                    current_header = MessageHeader()
                    current_offset += current_header.unpack(buffer=received_data, offset=current_offset)

            # Now wait for the message payload.
            if len(received_data) - current_offset < current_header.payload_size_bytes:
                break

            # Finally, decode the message. This function will verify the CRC, but in theory at least, this should not be
            # necessary for a TCP stream.
            decode_message(current_header, received_data, current_offset)
            current_offset += current_header.payload_size_bytes
            current_header = None

    sock.close()
