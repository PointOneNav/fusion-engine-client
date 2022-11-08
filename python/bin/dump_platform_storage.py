#!/usr/bin/env python3

import logging
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages import *
from fusion_engine_client.parsers import MixedLogReader
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from fusion_engine_client.utils.time_range import TimeRange

_logger = logging.getLogger('point_one.fusion_engine.applications.print_contents')

if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Decode and print the contents of messages contained in a *.p1log file or other
binary file containing FusionEngine messages. The binary file may also contain
other types of data.
""")
    parser.add_argument(
        '-t', '--time', type=str, metavar='[START][:END]',
        help="The desired time range to be analyzed. Both start and end may be omitted to read from beginning or to "
             "the end of the file. By default, timestamps are treated as relative to the first message in the file. "
             "See --absolute-time.")
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
    parser.add_argument(
        '-o',
        '--output',
        type=str,
        metavar='DIR',
        help="The file path where output will be stored. Defaults to `platform_storage.bin` and `platform_storage_version.txt` in parent directory of the input"
        "file, or to the log directory if reading from a log.")
    parser.add_argument('-s', '--storage-type', default=DataType.USER_CONFIG.name, choices=(v.name for v in DataType),
                        help="The type of platform storage to dump.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--first', action='store_true',
                       help="Only dump the first instance of the platform storage type.")
    group.add_argument('-l', '--last', action='store_true',
                       help="Only dump the last instance of the platform storage type.")

    options = parser.parse_args()

    read_index = not options.ignore_index
    generate_index = not options.ignore_index

    storage_type = DataType[options.storage_type]

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.TRACE, depth=options.verbose - 1)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    # Locate the input file and set the output directory.
    input_path, output_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir, return_log_id=True,
                                                extract_fusion_engine_data=False, return_output_dir=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    output_bin_file = os.path.join(output_dir, 'platform_storage.bin')

    if options.output is not None:
        output_bin_file = options.output

    if '.' in output_bin_file:
        output_version_file = ''.join(output_bin_file.split('.')[:-1])
    else:
        output_version_file = output_bin_file
    output_version_file = output_version_file + '_version.txt'

    _logger.info("Processing input file '%s'." % input_path)

    # Parse the time range.
    time_range = TimeRange.parse(options.time)

    if options.time is not None:
        _logger.info('Non-P1 time messages requested and time range specified. Disabling index file.')
        read_index = False

    message_types = (MessageType.PLATFORM_STORAGE_DATA, InternalMessageType.LEGACY_PLATFORM_STORAGE_DATA)

    # Process all data in the file.
    reader = MixedLogReader(input_path, show_progress=options.progress,
                            ignore_index=not read_index, generate_index=generate_index,
                            message_types=message_types, time_range=time_range)

    if reader.generating_index():
        _logger.info('Generating index file - processing complete file. This may take some time.')

    total_messages = 0

    version = None

    last_message_data = None
    with open(output_bin_file, 'wb') as fd:
        for header, message in reader:
            if message.data_type == storage_type:
                total_messages += 1
                version = message.data_version
                if options.last:
                    last_message = message.data
                else:
                    fd.write(message.data)
                    if options.first:
                        break

        if last_message_data:
            fd.write(last_message_data)

    if total_messages == 0:
        _logger.warning(f'No valid {options.storage_type} PlatformStorage messages found.')
    else:
        version_str = f'{version.major}.{version.minor}'
        _logger.info(
            f'Decoded {total_messages} instances of {options.storage_type} PlatformStorage message version {version_str}.')
        with open(output_version_file, 'w') as fd:
            fd.write(version_str)
