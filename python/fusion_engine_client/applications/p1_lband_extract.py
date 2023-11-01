#!/usr/bin/env python3

import os
import sys

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..utils.trace import HighlightFormatter, BrokenPipeStreamHandler
from ..utils.time_range import TimeRange
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils import trace as logging
from ..parsers import MixedLogReader
from ..messages import *


_logger = logging.getLogger('point_one.fusion_engine.applications.lband_extract')


def main():
    parser = ArgumentParser(description="""\
Extract L-band corrections data from a log containing FusionEngine L-band frame messages.
""")

    parser.add_argument(
        '--absolute-time', '--abs', action=ExtendedBooleanAction,
        help="Interpret the timestamps in --time as absolute P1 times. Otherwise, treat them as relative to the first "
             "message in the file. Ignored if --time contains a type specifier.")
    parser.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file, "
             "unless an 'abs' type is specified or --absolute-time is set.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")
    output_parser = parser.add_argument_group('Output Control')
    output_parser.add_argument('-o', '--output', type=str, metavar='DIR',
                               help="The directory where output will be stored. Defaults to the parent directory of the input"
                               "file, or to the log directory if reading from a log.")
    output_parser.add_argument('-p', '--prefix', type=str,
                               help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                               "filename of the input data file (e.g., `input.p1log`), or `fusion_engine` if reading "
                               "from a log (e.g., `fusion_engine.p1log`).")
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
    input_path, output_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir,
                                                return_log_id=True, return_output_dir=True, extract_fusion_engine_data=False)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    if options.output is not None:
        output_dir = options.output

    # Read through the data file, searching for valid LBandFrame messages to extract and store in
    # 'output_dir/<prefix>.p1log'.
    message_types = set([MessageType.LBAND_FRAME])
    if options.prefix is not None:
        prefix = options.prefix
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, prefix + '.lband.bin')

    _logger.info("Processing input file '%s'." % input_path)

    # Parse the time range.
    time_range = TimeRange.parse(options.time, absolute=options.absolute_time)

    if options.time is not None:
        _logger.info('L-band messages do not use P1 time. Disabling index file when applying time range to system timestamps.')
        read_index = False

    # Process all LBandFrameMessage data in the file.
    reader = MixedLogReader(input_path, return_bytes=True, return_offset=True, show_progress=options.progress,
                            ignore_index=not read_index, message_types=message_types, time_range=time_range)

    total_messages = 0
    bytes_decoded = 0

    with open(output_path, 'wb') as fd:
        try:
            for header, message, data, offset_bytes in reader:
                # This check is purely for type inference.
                if isinstance(message, LBandFrameMessage):
                    bytes_decoded += len(message.data_payload)
                    total_messages += 1
                    fd.write(message.data_payload)
        except (BrokenPipeError, KeyboardInterrupt) as e:
            sys.exit(1)

    # Print the data summary.
    if total_messages > 0:
        _logger.info('Input File: %s' % input_path)
        _logger.info('Output File: %s' % output_path)
        _logger.info('Log ID: %s' % log_id)
        _logger.info('Total Messages: %d' % total_messages)
        _logger.info('L-band Bytes Decoded: %d' % bytes_decoded)
    elif total_messages == 0:
        _logger.warning('No valid L-band frame messages found.')


if __name__ == "__main__":
    main()
