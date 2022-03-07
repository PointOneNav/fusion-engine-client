#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *
from fusion_engine_client.messages import ros

from examples.message_decode import print_message


def decode_message(header, data, offset):
    # Validate the message length and CRC.
    if len(data) != header.calcsize() + header.payload_size_bytes:
        return False
    else:
        header.validate_crc(data)

    # Check that the sequence number increments as expected.
    if header.sequence_number != decode_message.expected_sequence_number:
        print('Warning: unexpected sequence number. [expected=%d, received=%d]' %
              (decode_message.expected_sequence_number, header.sequence_number))

    decode_message.expected_sequence_number = header.sequence_number + 1

    # Deserialize and print the message contents.
    #
    # Note: This could also be done more generally using the fusion_engine_client.message_type_to_class dictionary.
    # We do it explicitly here for sake of example.
    if header.message_type == PoseMessage.MESSAGE_TYPE:
        contents = PoseMessage()
        contents.unpack(buffer=data, offset=offset)
    elif header.message_type == GNSSInfoMessage.MESSAGE_TYPE:
        contents = GNSSInfoMessage()
        contents.unpack(buffer=data, offset=offset)
    elif header.message_type == GNSSSatelliteMessage.MESSAGE_TYPE:
        contents = GNSSSatelliteMessage()
        contents.unpack(buffer=data, offset=offset)
    elif header.message_type == ros.PoseMessage.MESSAGE_TYPE:
        contents = ros.PoseMessage()
        contents.unpack(buffer=data, offset=offset)
    elif header.message_type == ros.ROSGPSFixMessage.MESSAGE_TYPE:
        contents = ros.ROSGPSFixMessage()
        contents.unpack(buffer=data, offset=offset)
    elif header.message_type == ros.ROSIMUMessage.MESSAGE_TYPE:
        contents = ros.ROSIMUMessage()
        contents.unpack(buffer=data, offset=offset)
    else:
        contents = None

    print_message(header, contents)

    return True


decode_message.expected_sequence_number = 0


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Manually decode and print the contents of messages contained in a *.p1log file.

Note that this application assumes the file contains _only_ FusionEngine
messages. For files containing mixed content, see message_decode.py.
""")
    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    f = open(options.file, 'rb')

    while True:
        # Read the next message header.
        data = f.read(MessageHeader.calcsize())
        if len(data) == 0:
            break

        # Deserialize the header.
        try:
            header = MessageHeader()
            offset = header.unpack(buffer=data)
        except Exception as e:
            print('Decode error: %s' % str(e))
            break

        # Read the message payload and append it to the header.
        data += f.read(header.payload_size_bytes)

        if not decode_message(header, data, offset):
            break
