#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import MessagePayload
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR


def print_message(header, contents):
    if isinstance(contents, MessagePayload):
        parts = str(contents).split('\n')
        parts[0] += ' [sequence=%d, size=%d B]' % (header.sequence_number, header.get_message_size())
        print('\n'.join(parts))
    else:
        print('Decoded %s message [sequence=%d, size=%d B]' %
              (header.get_type_string(), header.sequence_number, header.get_message_size()))


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Decode and print the contents of messages contained in a *.p1log file or other
binary file containing FusionEngine messages. The binary file may also contain
other types of data.
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
    # Note here that we intentionally tell locate_log() _not_ to convert the input file to a *.p1log file
    # (extract_fusion_engine_data=False). That way, if it finds a file containing a mix of FusionEngine messages and
    # other data, we can use that file directly to demonstrate how the FusionEngineDecoder class operates.
    input_path, output_dir, log_id = locate_log(options.log, return_output_dir=True, return_log_id=True,
                                                log_base_dir=options.log_base_dir, extract_fusion_engine_data=False)
    if input_path is None:
        sys.exit(1)

    if log_id is None:
        logger.info('Loading %s.' % os.path.basename(input_path))
    else:
        logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

    # Read binary data from the file a 1 KB chunk at a time and decode any FusionEngine messages in the stream. Any data
    # that is not part of a FusionEngine message will be ignored.
    f = open(input_path, 'rb')

    decoder = FusionEngineDecoder()
    while True:
        # Read the next message header.
        data = f.read(1024)
        if len(data) == 0:
            break

        # Decode the incoming data and print the contents of any complete messages.
        messages = decoder.on_data(data)
        for (header, message) in messages:
            print_message(header, message)
