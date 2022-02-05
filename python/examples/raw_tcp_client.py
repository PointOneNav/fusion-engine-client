#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import socket
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *

from examples.raw_message_decode import decode_message


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to an Atlas device over TCP and print out the incoming message
contents.

This example interprets the incoming data directly, and does not use the
FusionEngineDecoder class. The incoming data stream must contain only
FusionEngine messages. See also tcp_client.py.
""")
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the Atlas device.")
    parser.add_argument('ip_address',
                        help="The IP address of the Atlas device.")
    options = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((options.ip_address, options.port))

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
