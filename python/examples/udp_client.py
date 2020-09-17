from argparse import ArgumentParser
import os
import socket
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *

from examples.message_decode import decode_message


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=12345,
                        help="The UDP port to which messages are being sent.")
    options = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', options.port))

    while True:
        # Read the next packet.
        data = sock.recv(1024)

        # Deserialize the header.
        try:
            header = MessageHeader()
            offset = header.unpack(buffer=data)
        except Exception as e:
            print('Decode error: %s' % str(e))
            continue

        if not decode_message(header, data, offset):
            continue
