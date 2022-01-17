#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import MessagePayload
from fusion_engine_client.parsers import FusionEngineDecoder


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
    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    f = open(options.file, 'rb')

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
