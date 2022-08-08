#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder

if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Encode a FusionEngine message and print the resulting binary content to the
console.
""")

    options = parser.parse_args()

    # Enable FusionEngine PoseMessage output on UART1
    message = SetMessageOutputRate(output_interface=InterfaceID(TransportType.SERIAL, 1),
                                   protocol=ProtocolType.FUSION_ENGINE,
                                   message_id=10000,
                                   rate=MessageRate.ON_CHANGE)

    encoder = FusionEngineEncoder()
    encoded_data = encoder.encode_message(message)

    bytes_per_row = 16
    bytes_per_col = 2
    byte_string = ''
    for i, b in enumerate(encoded_data):
        if i > 0:
            if (i % bytes_per_row) == 0:
                byte_string += '\n'
            elif (i % bytes_per_col) == 0:
                byte_string += ' '

        byte_string += '%02x' % b

    print(byte_string)
