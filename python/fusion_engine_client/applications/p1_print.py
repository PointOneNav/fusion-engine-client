#!/usr/bin/env python3

from collections import defaultdict
import sys

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import MixedLogReader
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.bin_utils import bytes_to_hex
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from ..utils.time_range import TimeRange
from ..utils.trace import HighlightFormatter, BrokenPipeStreamHandler

_logger = logging.getLogger('point_one.fusion_engine.applications.print_contents')


def print_message(header, contents, offset_bytes, format='pretty', bytes=None):
    if format == 'binary':
        if bytes is None:
            raise ValueError('No data provided for binary format.')
        parts = []
    elif isinstance(contents, MessagePayload):
        if format in ('oneline', 'oneline-binary', 'oneline-detailed'):
            # The repr string should always start with the message type, then other contents:
            #   [POSE (10000), p1_time=12.029 sec, gps_time=2249:528920.500 (1360724120.500 sec), ...]
            # We want to reformat and insert the additional details as follows for consistency:
            #   POSE (10000) [sequence=10, ... p1_time=12.029 sec, gps_time=2249:528920.500 (1360724120.500 sec), ...]
            message_str = repr(contents).split('\n')[0]
            message_str = message_str.replace('[', '', 1)
            break_idx = message_str.find(',')
            if break_idx >= 0:
                message_str = f'{message_str[:break_idx]} [{message_str[(break_idx + 2):]}'
            else:
                message_str = message_str.rstrip(']')
            parts = [message_str]
        else:
            parts = str(contents).split('\n')
    else:
        parts = [f'{header.get_type_string()} (unsupported)']

    if format in ('pretty', 'pretty-binary', 'oneline-detailed', 'oneline-binary'):
        details = 'sequence=%d, size=%d B, offset=%d B (0x%x)' %\
                  (header.sequence_number, header.get_message_size(), offset_bytes, offset_bytes)

        idx = parts[0].find('[')
        if idx < 0:
            parts[0] += f' [{details}]'
        else:
            parts[0] = f'{parts[0][:(idx + 1)]}{details}, {parts[0][(idx + 1):]}'

    if bytes is None:
        pass
    elif format == 'binary':
        byte_string = bytes_to_hex(bytes, bytes_per_row=-1, bytes_per_col=2).replace('\n', '\n  ')
        parts.insert(1, byte_string)
    elif format == 'pretty-binary':
        byte_string = '    ' + bytes_to_hex(bytes, bytes_per_row=16, bytes_per_col=2).replace('\n', '\n    ')
        parts.insert(1, "  Binary:\n%s" % byte_string)
    elif format == 'oneline-binary':
        byte_string = '  ' + bytes_to_hex(bytes, bytes_per_row=16, bytes_per_col=2).replace('\n', '\n  ')
        parts.insert(1, byte_string)

    _logger.info('\n'.join(parts))


def main():
    parser = ArgumentParser(description="""\
Decode and print the contents of messages contained in a *.p1log file or other
binary file containing FusionEngine messages. The binary file may also contain
other types of data.
""")

    parser.add_argument(
        '--absolute-time', '--abs', action=ExtendedBooleanAction,
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file. Ignored if --time contains a type specifier.")
    parser.add_argument(
        '-f', '--format', choices=['binary', 'pretty', 'pretty-binary', 'oneline', 'oneline-detailed',
                                   'oneline-binary'],
        default='pretty',
        help="Specify the format used to print the message contents:\n"
             "- Print the binary representation of each message on a single line, but no other details\n"
             "- pretty - Print the message contents in a human-readable format (default)\n"
             "- pretty-binary - Use `pretty` format, but include the binary representation of each message\n"
             "- oneline - Print a summary of each message on a single line\n"
             "- oneline-detailed - Print a one-line summary, including message offset details\n"
             "- oneline-binary - Use `oneline-detailed` format, but include the binary representation of each message")
    parser.add_argument(
        '-s', '--summary', action='store_true',
        help="Print a summary of the messages in the file.")
    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be displayed. May be specified "
             "multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). All matches are"
             "case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
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
    BrokenPipeStreamHandler.install()

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
    message_types = set()
    if options.message_type is not None:
        # Pattern match to any of:
        #   -m Type1
        #   -m Type1 -m Type2
        #   -m Type1,Type2
        #   -m Type1,Type2 -m Type3
        #   -m Type*
        try:
            message_types = MessagePayload.find_matching_message_types(options.message_type)
            if len(message_types) == 0:
                # find_matching_message_types() will print an error.
                sys.exit(1)
        except ValueError as e:
            _logger.error(str(e))
            sys.exit(1)

    # Process all data in the file.
    reader = MixedLogReader(input_path, return_bytes=True, return_offset=True, show_progress=options.progress,
                            ignore_index=not read_index, message_types=message_types, time_range=time_range)

    first_p1_time_sec = None
    last_p1_time_sec = None
    newest_p1_time = None
    newest_p1_message_type = None

    first_system_time_sec = None
    last_system_time_sec = None
    newest_system_time_sec = None
    newest_system_message_type = None

    total_messages = 0
    bytes_decoded = 0

    def create_stats_entry(): return {'count': 1}
    message_stats = defaultdict(create_stats_entry)
    try:
        for header, message, data, offset_bytes in reader:
            bytes_decoded += len(data)

            # Update the data summary in summary mode, or print the message contents otherwise.
            total_messages += 1
            if options.summary:
                entry = message_stats[header.message_type]
                entry['count'] += 1

                if message is not None:
                    p1_time = message.get_p1_time()
                    if p1_time is not None:
                        if first_p1_time_sec is None:
                            first_p1_time_sec = float(p1_time)
                            last_p1_time_sec = float(p1_time)
                            newest_p1_time = p1_time
                            newest_p1_message_type = header.message_type
                        else:
                            # We allow a small tolerance to account for normal latency between measurements and computed
                            # data like pose solutions, as well as latency between different types of measurements.
                            dt_sec = float(p1_time - newest_p1_time)
                            if dt_sec < -0.2:
                                _logger.warning(
                                    'Backwards/restarted P1 time detected after %s (%s). [new_message=%s, '
                                    'new_p1_time=%s, offset=%d B]' %
                                    (str(newest_p1_time), str(newest_p1_message_type), header.get_type_string(),
                                     str(p1_time), offset_bytes))
                            last_p1_time_sec = max(last_p1_time_sec, float(p1_time))
                            newest_p1_time = p1_time
                            newest_p1_message_type = header.message_type

                    system_time_sec = message.get_system_time_sec()
                    if system_time_sec is not None:
                        if first_system_time_sec is None:
                            first_system_time_sec = system_time_sec
                            last_system_time_sec = system_time_sec
                            newest_system_time_sec = system_time_sec
                            newest_system_message_type = header.message_type
                        else:
                            # We allow a small tolerance to account for normal latency between measurements and computed
                            # data like pose solutions, as well as latency between different types of measurements.
                            dt_sec = newest_system_time_sec - system_time_sec
                            if dt_sec < -0.2:
                                _logger.warning(
                                    'Backwards/restarted system time detected after %s (%s). [new_message=%s, '
                                    'new_system_time=%s, offset=%d B]' %
                                    (system_time_to_str(newest_system_time_sec, is_seconds=True),
                                     str(newest_system_message_type), header.get_type_string(),
                                     system_time_to_str(system_time_sec, is_seconds=True),
                                     offset_bytes))
                            last_system_time_sec = max(last_system_time_sec, system_time_sec)
                            newest_system_time_sec = system_time_sec
                            newest_system_message_type = header.message_type
            else:
                print_message(header, message, offset_bytes, format=options.format, bytes=data)
    except (BrokenPipeError, KeyboardInterrupt) as e:
        sys.exit(1)

    # Print the data summary.
    if options.summary:
        _logger.info('Input file: %s' % input_path)
        _logger.info('Log ID: %s' % log_id)
        if first_p1_time_sec is not None:
            _logger.info('Duration (P1): %.1f seconds' % (last_p1_time_sec - first_p1_time_sec))
        else:
            _logger.info('Duration (P1): unknown')
        if first_system_time_sec is not None:
            _logger.info('Duration (system): %.1f seconds' % (last_system_time_sec - first_system_time_sec))
        else:
            _logger.info('Duration (system): unknown')
        _logger.info('Total data read: %d B' % reader.get_bytes_read())
        _logger.info('Selected data size: %d B' % bytes_decoded)
        _logger.info('')

        format_string = '| {:<50} | {:>5} | {:>8} |'
        _logger.info(format_string.format('Message Name', 'Type', 'Count'))
        _logger.info(format_string.format('-' * 50, '-' * 5, '-' * 8))
        for type, info in sorted(message_stats.items(), key=lambda x: int(x[0])):
            name = message_type_to_class[type].__name__ if type in message_type_to_class else "Unknown"
            _logger.info(format_string.format(name, int(type), info['count']))
        _logger.info(format_string.format('-' * 50, '-' * 5, '-' * 8))
        _logger.info(format_string.format('Total', '', total_messages))
    elif total_messages == 0:
        _logger.warning('No valid FusionEngine messages found.')


if __name__ == "__main__":
    main()
