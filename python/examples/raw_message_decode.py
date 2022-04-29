#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *
from fusion_engine_client.messages import ros
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR

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
    elif header.message_type == ros.ROSPoseMessage.MESSAGE_TYPE:
        contents = ros.ROSPoseMessage()
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
""")
    parser.add_argument('--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is "
                             "specified.")
    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1log file or a file containing FusionEngine messages and other "
                             "content\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")
    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(format='%(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.INFO)

    # Locate the input file and set the output directory.
    #
    # Note that, unlike the message_decode.py example, here we _do_ ask locate_log() to create a *.p1log file for us if
    # it finds an input file containing a mix of FusionEngine messages and other data. The loop below assumes that the
    # file we are reading contains _only_ FusionEngine messages.
    input_path, output_dir, log_id = locate_log(options.log, return_output_dir=True, return_log_id=True,
                                                log_base_dir=options.log_base_dir)
    if input_path is None:
        sys.exit(1)

    if log_id is None:
        logger.info('Loading %s.' % os.path.basename(input_path))
    else:
        logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

    # Read one FusionEngine message at a time from the binary file. If the file contains any data that is not part of a
    # valid FusionEngine message, we will exit immediately.
    f = open(input_path, 'rb')

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
