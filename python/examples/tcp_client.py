#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import socket
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.parsers import FusionEngineDecoder

from examples.message_decode import print_message


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to an Atlas device over TCP and print out the incoming message
contents.
""")
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the Atlas device.")
    parser.add_argument('ip_address',
                        help="The IP address of the Atlas device.")
    options = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((options.ip_address, options.port))

    decoder = FusionEngineDecoder()
    while True:
        # Read some data.
        try:
            received_data = sock.recv(1024)
        except KeyboardInterrupt:
            break

        messages = decoder.on_data(received_data)
        for (header, message) in messages:
            print_message(header, message)

    sock.close()
