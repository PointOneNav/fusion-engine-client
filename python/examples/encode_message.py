#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import FusionEngineEncoder
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.bin_utils import bytes_to_hex

if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Encode a FusionEngine message and print the resulting binary content to the
console.
""")

    options = parser.parse_args()

    # Enable FusionEngine PoseMessage output on UART1
    message = SetMessageRate(output_interface=InterfaceID(TransportType.SERIAL, 1),
                             protocol=ProtocolType.FUSION_ENGINE,
                             message_id=MessageType.POSE,
                             rate=MessageRate.ON_CHANGE)
    print(message)

    encoder = FusionEngineEncoder()
    encoded_data = encoder.encode_message(message)

    print('')
    print(bytes_to_hex(encoded_data, bytes_per_row=16, bytes_per_col=2))
