#!/usr/bin/env python3

from collections import defaultdict
import os
import sys

import numpy as np

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import MixedLogReader
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser, TriStateBooleanAction
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from fusion_engine_client.utils.time_range import TimeRange
from fusion_engine_client.utils.trace import HighlightFormatter

_logger = logging.getLogger('point_one.fusion_engine.applications.print_contents')


def print_message(header, contents, offset_bytes, one_line=False):
    if isinstance(contents, MessagePayload):
        parts = str(contents).split('\n')
        parts[0] += ' [sequence=%d, size=%d B, offset=%d B (0x%x)]' %\
                    (header.sequence_number, header.get_message_size(), offset_bytes, offset_bytes)
        if one_line:
            _logger.info(parts[0])
        else:
            _logger.info('\n'.join(parts))
    else:
        _logger.info('Decoded %s message [sequence=%d, size=%d B, offset=%d B (0x%x)]' %
                     (header.get_type_string(), header.sequence_number, header.get_message_size(),
                      offset_bytes, offset_bytes))


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Decode and print the contents of messages contained in a *.p1log file or other
binary file containing FusionEngine messages. The binary file may also contain
other types of data.
""")

    parser.add_argument(
        '--absolute-time', '--abs', action=TriStateBooleanAction,
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file. Ignored if --time contains a type specifier.")
    parser.add_argument(
        '-f', '--format', choices=['pretty', 'oneline'], default='pretty',
        help="Specify the format used to print the message contents.")
    parser.add_argument(
        '-s', '--summary', action='store_true',
        help="Print a summary of the messages in the file.")
    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be displayed. May be specified "
             "multiple times (-m Type 1 -m Type 2), or as a comma-separated list (-m Type1,Type2). "
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
    parser.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file, "
             "unless an 'abs' type is specified or --absolute-time is set.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    log_parser = parser.add_argument_group('Log Control')
    log_parser.add_argument(
        '--ignore-index', action='store_true',
        help="If set, do not load the .p1i index file corresponding with the .p1log data file. If specified and a .p1i "
             "file does not exist, do not generate one. Otherwise, a .p1i file will be created automatically to "
             "improve data read speed in the future.")
    log_parser.add_argument(
        '--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
        help="The base directory containing FusionEngine logs to be searched if a log pattern is specified.")
    log_parser.add_argument(
        '--progress', action='store_true',
        help="Print file read progress to the console periodically.")
    log_parser.add_argument(
        'log',
        help="The log to be read. May be one of:\n"
             "- The path to a .p1log file or a file containing FusionEngine messages and other content\n"
             "- The path to a FusionEngine log directory\n"
             "- A pattern matching a FusionEngine log directory under the specified base directory "
             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    read_index = not options.ignore_index
    generate_index = not options.ignore_index

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)

    # Locate the input file and set the output directory.
    input_path, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir, return_log_id=True,
                                    extract_fusion_engine_data=False)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    _logger.info("Processing input file '%s'." % input_path)

    # Parse the time range.
    time_range = TimeRange.parse(options.time, absolute=options.absolute_time)

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = []
    if options.message_type is not None:
        # Convert to lowercase to perform case-insensitive search.
        type_by_name = {k.lower(): v for k, v in message_type_by_name.items()}

        # Split comma-separated names. That way the user can specify multiple -m entries or comma-separated names (or
        # a mix of the two):
        #   -m Type1,Type2 -m Type 3
        requested_types = []
        for name in options.message_type:
            requested_types.extend(name.split(','))

        for name in requested_types:
            lower_name = name.lower()
            message_type = type_by_name.get(lower_name, None)
            if message_type is None:
                # If we can't find an exact match for the key, try a partial match.
                matches = {k: v for k, v in type_by_name.items() if k.startswith(lower_name)}
                if len(matches) == 1:
                    message_types.append(next(iter(matches.values())))
                elif len(matches) > 1:
                    types = [v for v in matches.values()]
                    class_names = [message_type_to_class[t].__name__ for t in types]
                    _logger.info("Found multiple types matching '%s':\n  %s" % (name, '\n  '.join(class_names)))
                    sys.exit(1)
                else:
                    _logger.info("Unrecognized message type '%s'." % name)
                    sys.exit(1)
            else:
                message_types.append(message_type)
        message_types = set(message_types)

    # Check if any of the requested message types do _not_ have P1 time (e.g., profiling messages). The index file
    # does not currently contain non-P1 time messages, so if we use it to search for messages we will end up
    # skipping all of these ones. Instead, we disable the index and revert to full file search.
    if read_index:
        if len(message_types) == 0:
            need_system_time = True
        else:
            need_system_time = False
            for message_type in message_types:
                cls = message_type_to_class[message_type]
                message = cls()
                if hasattr(message, 'p1_time'):
                    continue
                else:
                    timestamps = getattr(message, 'timestamps', None)
                    if isinstance(timestamps, MeasurementTimestamps):
                        continue
                    else:
                        need_system_time = True
                        break

        if need_system_time and options.time is not None:
            _logger.info('Non-P1 time messages requested and time range specified. Disabling index file.')
            read_index = False

    # Process all data in the file.
    reader = MixedLogReader(input_path, return_bytes=True, return_offset=True, show_progress=options.progress,
                            ignore_index=not read_index, generate_index=generate_index,
                            message_types=message_types, time_range=time_range)

    if reader.generating_index() and (len(message_types) > 0 or options.time is not None):
        _logger.info('Generating index file - processing complete file. This may take some time.')

    first_p1_time_sec = None
    last_p1_time_sec = None
    newest_p1_time = None

    first_system_time_sec = None
    last_system_time_sec = None
    newest_system_time_sec = None

    total_messages = 0
    bytes_decoded = 0

    def create_stats_entry(): return {'count': 1}
    message_stats = defaultdict(create_stats_entry)
    for header, message, data, offset_bytes in reader:
        bytes_decoded += len(data)

        # Update the data summary in summary mode, or print the message contents otherwise.
        total_messages += 1
        if options.summary:
            p1_time = message.get_p1_time()
            if p1_time is not None:
                if first_p1_time_sec is None:
                    first_p1_time_sec = float(p1_time)
                    last_p1_time_sec = float(p1_time)
                    newest_p1_time = p1_time
                else:
                    if p1_time < newest_p1_time:
                        _logger.warning('P1 time restart detected after %s.' % str(newest_p1_time))
                    last_p1_time_sec = max(last_p1_time_sec, float(p1_time))
                    newest_p1_time = p1_time

            system_time_sec = message.get_system_time_sec()
            if system_time_sec is not None:
                if first_system_time_sec is None:
                    first_system_time_sec = system_time_sec
                    last_system_time_sec = system_time_sec
                    newest_system_time_sec = system_time_sec
                else:
                    if system_time_sec < newest_system_time_sec:
                        _logger.warning('System time restart detected after %s.' %
                                        system_time_to_str(newest_system_time_sec, is_seconds=True))
                    last_system_time_sec = max(last_system_time_sec, system_time_sec)
                    newest_system_time_sec = system_time_sec

            entry = message_stats[header.message_type]
            entry['count'] += 1
        else:
            print_message(header, message, offset_bytes, one_line=options.format == 'oneline')

    # Print the data summary.
    if options.summary:
        _logger.info('Input file: %s' % input_path)
        _logger.info('Log ID: %s' % log_id)
        if first_p1_time_sec is not None:
            _logger.info('Duration (P1): %d seconds' % (last_p1_time_sec - first_p1_time_sec))
        else:
            _logger.info('Duration (P1): unknown')
        if first_system_time_sec is not None:
            _logger.info('Duration (system): %d seconds' % (last_system_time_sec - first_system_time_sec))
        else:
            _logger.info('Duration (system): unknown')
        _logger.info('Total data read: %d B' % reader.get_bytes_read())
        _logger.info('Selected data size: %d B' % bytes_decoded)
        _logger.info('')

        format_string = '| {:<50} | {:>8} |'
        _logger.info(format_string.format('Message Type', 'Count'))
        _logger.info(format_string.format('-' * 50, '-' * 8))
        for type, info in message_stats.items():
            _logger.info(format_string.format(message_type_to_class[type].__name__, info['count']))
        _logger.info(format_string.format('-' * 50, '-' * 8))
        _logger.info(format_string.format('Total', total_messages))
    elif total_messages == 0:
        _logger.warning('No valid FusionEngine messages found.')
