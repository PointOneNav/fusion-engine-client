#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages import MessagePayload, message_type_to_class, message_type_by_name
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.log import locate_log
from fusion_engine_client.utils.time_range import TimeRange


def print_message(header, contents, one_line=False):
    if isinstance(contents, MessagePayload):
        parts = str(contents).split('\n')
        parts[0] += ' [sequence=%d, size=%d B]' % (header.sequence_number, header.get_message_size())
        if one_line:
            print(parts[0])
        else:
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

    parser.add_argument(
        '--absolute-time', '--abs', action='store_true',
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file.")
    parser.add_argument(
        '-f', '--format', choices=['pretty', 'oneline'], default='pretty',
        help="Specify the format used to print the message contents.")
    parser.add_argument(
        '-s', '--summary', action='store_true',
        help="Print a summary of the messages in the file.")
    parser.add_argument(
        '--time', type=str, metavar='[START][:END]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file. "
             "See --absolute-time.")
    parser.add_argument(
        '-t', '--type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be displayed. "
             "Supported types:\n%s" % '\n'.join(['  %s' % c for c in message_type_by_name.keys()]))

    log_parser = parser.add_argument_group('Log Control')
    log_parser.add_argument(
        '--log-base-dir', metavar='DIR', default='/logs',
        help="The base directory containing FusionEngine logs to be searched if a log pattern is specified.")
    log_parser.add_argument(
        'log',
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

    # Parse the time range.
    time_range = TimeRange.parse(options.time, absolute=options.absolute_time)

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

    # Process all data in the file.
    decoder = FusionEngineDecoder(return_bytes=True)

    first_p1_time_sec = None
    last_p1_time_sec = None
    first_system_time_sec = None
    last_system_time_sec = None
    total_messages = 0
    bytes_read = 0
    bytes_decoded = 0
    message_stats = {}
    with open(input_path, 'rb') as f:
        still_working = True
        while still_working:
            # Read the next message header.
            data = f.read(1024)
            if len(data) == 0:
                break
            else:
                bytes_read += len(data)

            # Decode the incoming data and print the contents of any complete messages.
            messages = decoder.on_data(data)
            for (header, message, message_raw) in messages:
                if len(message_types) == 0 or header.message_type in message_types:
                    # Limit to the user-specified time range if applicable.
                    in_range, p1_time, system_time_ns = time_range.is_in_range(message, return_timestamps=True)
                    if not in_range:
                        if time_range.in_range_started():
                            still_working = False
                            break
                        else:
                            continue

                    bytes_decoded += len(message_raw)

                    # Update the data summary in summary mode, or print the message contents otherwise.
                    if options.summary:
                        if p1_time is not None:
                            if first_p1_time_sec is None:
                                first_p1_time_sec = float(p1_time)
                            last_p1_time_sec = float(p1_time)

                        if system_time_ns is not None:
                            if first_system_time_sec is None:
                                first_system_time_sec = system_time_ns * 1e-9
                            last_system_time_sec = system_time_ns * 1e-9

                        total_messages += 1
                        if header.message_type not in message_stats:
                            message_stats[header.message_type] = {
                                'count': 1
                            }
                        else:
                            entry = message_stats[header.message_type]
                            entry['count'] += 1
                    else:
                        print_message(header, message, one_line=options.format == 'oneline')

    if options.summary:
        print('Input file: %s' % input_path)
        print('Log ID: %s' % log_id)
        if first_p1_time_sec is not None:
            print('Duration: %d seconds' % (last_p1_time_sec - first_p1_time_sec))
        elif first_system_time_sec is not None:
            print('Duration: %d seconds' % (last_system_time_sec - first_system_time_sec))
        print('Total data read: %d B' % bytes_read)
        print('Selected data size: %d B' % bytes_decoded)
        print('')

        format_string = '| {:<50} | {:>8} |'
        print(format_string.format('Message Type', 'Count'))
        print(format_string.format('-' * 50, '-' * 8))
        for type, info in message_stats.items():
            print(format_string.format(message_type_to_class[type].__name__, info['count']))
        print(format_string.format('-' * 50, '-' * 8))
        print(format_string.format('Total', total_messages))
