#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages import MessagePayload, message_type_to_class, message_type_by_name
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.log import locate_log


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
    parser.add_argument('-t', '--type', type=str, action='append',
                        help="An optional list of class names corresponding with the message types to be displayed. "
                             "Supported types:\n%s" % '\n'.join(['  %s' % c for c in message_type_by_name.keys()]))
    parser.add_argument('-s', '--summary', action='store_true',
                        help="Print a summary of the messages in the file.")

    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is "
                             "specified.")
    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1log file\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    # Locate the input file and set the output directory.
    input_path, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir, return_log_id=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = []
    if options.type is not None:
        # Convert to lowercase to perform case-insensitive search.
        type_by_name = {k.lower(): v for k, v in message_type_by_name.items()}
        for name in options.type:
            message_type = type_by_name.get(name.lower(), None)
            if message_type is None:
                print("Unrecognized message type '%s'." % name)
                sys.exit(1)
            else:
                message_types.append(message_type)
        message_types = set(message_types)

    decoder = FusionEngineDecoder()
    total_messages = 0
    message_stats = {}
    with open(input_path, 'rb') as f:
        while True:
            # Read the next message header.
            data = f.read(1024)
            if len(data) == 0:
                break

            # Decode the incoming data and print the contents of any complete messages.
            messages = decoder.on_data(data)
            for (header, message) in messages:
                if len(message_types) == 0 or header.message_type in message_types:
                    if options.summary:
                        total_messages += 1
                        if header.message_type not in message_stats:
                            message_stats[header.message_type] = {
                                'count': 1
                            }
                        else:
                            entry = message_stats[header.message_type]
                            entry['count'] += 1
                    else:
                        print_message(header, message)

    if options.summary:
        print('Input file: %s' % input_path)
        print('Log ID: %s' % log_id)
        print('')

        format_string = '| {:<50} | {:>8} |'
        print(format_string.format('Message Type', 'Count'))
        print(format_string.format('-' * 50, '-' * 8))
        for type, info in message_stats.items():
            print(format_string.format(message_type_to_class[type].__name__, info['count']))
        print(format_string.format('-' * 50, '-' * 8))
        print(format_string.format('Total', total_messages))
