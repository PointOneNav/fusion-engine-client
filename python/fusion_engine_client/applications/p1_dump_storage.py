#!/usr/bin/env python3

import os
import sys
from collections import defaultdict

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import MixedLogReader
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from ..utils.time_range import TimeRange

_logger = logging.getLogger('point_one.fusion_engine.applications.print_contents')

CACHE_NAME_MAP = {
    DataType.USER_CONFIG: 'user_config.p1log',
    DataType.CALIBRATION_STATE: 'calibration_state.p1log',
    DataType.FILTER_STATE: 'filter_state.p1log'
}

def main():
    parser = ArgumentParser(description="""\
Decode and dump the platform storage data for a specific datatype.
The version of the data is also recorded to the a `*_version.txt` file.
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
    parser.add_argument('-s', '--storage-type', default=DataType.USER_CONFIG.name, choices=[v.name for v in DataType] + ["all"],
                        help="The type of platform storage to dump.")
    parser.add_argument('-p', '--payload-only', action='store_true',
                        help="Only dump the storage contents without the header or message body.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--first', action='store_true',
                       help="Only dump the first instance of the platform storage type.")
    group.add_argument('-l', '--last', action='store_true',
                       help="Only dump the last instance of the platform storage type.")

    options = parser.parse_args()

    read_index = not options.ignore_index

    if options.storage_type == "all":
        storage_types = set(CACHE_NAME_MAP.keys())
    else:
        storage_types = set(DataType[options.storage_type])

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

    # Locate the input file and set the output directory.
    input_path, output_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir, return_log_id=True,
                                                extract_fusion_engine_data=False, return_output_dir=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    _logger.info("Processing input file '%s'." % input_path)

    output_dir = os.path.join(output_dir, "cache/embedded")
    os.makedirs(output_dir, exist_ok=True)
    _logger.info("Storing results in '%s'." % output_dir)

    # Parse the time range.
    time_range = TimeRange.parse(options.time)

    if options.time is not None:
        _logger.info('Non-P1 time messages requested and time range specified. Disabling index file.')
        read_index = False

    message_types = (MessageType.PLATFORM_STORAGE_DATA, InternalMessageType.LEGACY_PLATFORM_STORAGE_DATA)

    # Process all data in the file.
    reader = MixedLogReader(input_path, show_progress=options.progress, return_bytes=True,
                            ignore_index=not read_index,
                            message_types=message_types, time_range=time_range)

    total_messages = defaultdict(int)
    versions = {}
    for header, message, data in reader:
        if message.data_type in storage_types:
            total_messages[message.data_type] += 1
            versions[message.data_type] = message.data_version
            file_path = os.path.join(output_dir, CACHE_NAME_MAP[message.data_type])
            if options.payload_only:
                data = message.data
            if options.last or options.first or total_messages == 1:
                open(file_path, 'wb').write(data)
                if options.first:
                    storage_types.remove(message.data_type)
            else:
                open(file_path, 'ab').write(data)

    if total_messages == 0:
        _logger.warning(f'No valid {options.storage_type} PlatformStorage messages found.')
    else:
        for type, version in versions.items():
            version_str = f'{version.major}.{version.minor}'
            _logger.info(
                f'Decoded {total_messages[type]} instances of {type.name} PlatformStorage message version {version_str}.')
            file_path = os.path.join(output_dir, CACHE_NAME_MAP[type])
            output_version_file = ''.join(file_path.split('.')[:-1]) + '_version.txt'
            with open(output_version_file, 'w') as fd:
                fd.write(version_str)


if __name__ == "__main__":
    main()
