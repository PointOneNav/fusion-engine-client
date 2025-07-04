#!/usr/bin/env python3

import sys

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import MixedLogReader
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction, CSVAction
from ..utils.log import define_cli_arguments as define_log_search_arguments, locate_log
from ..utils.print_utils import DeviceSummary, add_print_format_argument, print_message, print_summary_table
from ..utils.time_range import TimeRange
from ..utils.trace import HighlightFormatter, BrokenPipeStreamHandler

_logger = logging.getLogger('point_one.fusion_engine.applications.print_contents')


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
    add_print_format_argument(parser, '-f', '--format', '--display-format')
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
        '-n', '--max', type=int, default=None,
        help="Print up to a maximum of N messages. If --message-type is specified, only count messages matching the "
             "specified type(s).")
    parser.add_argument(
        '-s', '--summary', action='store_true',
        help="Print a summary of the messages in the file.")
    parser.add_argument(
        '--skip', type=int, default=0,
        help="Skip the first N messages in the log. If --message-type is specified, only count messages matching the "
             "specified type(s).")
    parser.add_argument(
        '--source-identifier', '--source-id', action=CSVAction, nargs='*',
        help="Plot the FusionEngine Pose messages with the listed source identifier(s). Must be integers. May be "
             "specified multiple times (--source-id 0 --source-id 1), as a space-separated list (--source-id 0 1), or "
             "as a comma-separated list (--source-id 0,1). If not specified, all available source identifiers present "
             "in the log will be used.")
    parser.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file, "
             "unless an 'abs' type is specified or --absolute-time is set.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    log_parser = parser.add_argument_group('Input File/Log Control')
    define_log_search_arguments(log_parser)
    log_parser.add_argument(
        '--progress', action='store_true',
        help="Print file read progress to the console periodically.")

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
    message_types = None
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

    if options.source_identifier is None:
        source_id = None
    else:
        try:
            source_id = [int(s) for s in options.source_identifier]
        except ValueError:
            _logger.error('Source identifiers must be integers. Exiting.')
            sys.exit(1)

    # Process all data in the file.
    reader = MixedLogReader(input_path, return_bytes=True, return_offset=True, show_progress=options.progress,
                            ignore_index=not read_index, message_types=message_types, time_range=time_range,
                            source_ids=source_id)

    first_p1_time_sec = None
    last_p1_time_sec = None
    newest_p1_time = None
    newest_p1_message_type = None

    first_system_time_sec = None
    last_system_time_sec = None
    newest_system_time_sec = None
    newest_system_message_type = None

    total_decoded_messages = 0
    total_messages = 0
    bytes_decoded = 0
    device_summary = DeviceSummary()

    try:
        for header, message, data, offset_bytes in reader:
            total_decoded_messages += 1
            if total_decoded_messages <= options.skip:
                continue
            elif options.max is not None and (total_decoded_messages - options.skip) > options.max:
                break

            # Update the data summary in summary mode, or print the message contents otherwise.
            total_messages += 1
            bytes_decoded += len(data)
            if options.summary:
                device_summary.update(header, message)

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
                            dt_sec = system_time_sec - newest_system_time_sec
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
        print_summary_table(device_summary)
    elif total_messages == 0:
        _logger.warning('No valid FusionEngine messages found.')


if __name__ == "__main__":
    main()
