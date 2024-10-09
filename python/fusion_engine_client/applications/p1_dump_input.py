#!/usr/bin/env python3

import os

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import *
from ..parsers import MixedLogReader
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser
from ..utils.log import locate_log, DEFAULT_LOG_BASE_DIR


def main():
    parser = ArgumentParser(description="""\
Extract the contents of InputDataWrapper messages contained in a FusionEngine 
data stream, and store the results in separate binary files, one for each data
type.
""")
    parser.add_argument(
        '-d', '--data-type', type=int, action='append',
        help="Specify one or more integer data types to be extracted. Only InputDataWrapper messages for the "
             "specified types will be processed.")
    parser.add_argument(
        '-o', '--output-dir',
        help="Specify a directory where extracted content will be stored. Defaults to the log directory.")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
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

    # Configure logging.
    logger = logging.getLogger('point_one.fusion_engine')
    if options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif options.verbose > 1:
        logger.setLevel(logging.getTraceLevel(depth=options.verbose - 1))

    # Locate the input file and set the output directory.
    input_path, output_dir, log_id = locate_log(input_path=options.log, log_base_dir=options.log_base_dir,
                                                return_log_id=True,
                                                extract_fusion_engine_data=False, return_output_dir=True)
    if input_path is None:
        # locate_log() will log an error.
        sys.exit(1)

    if options.output_dir is not None:
        output_dir = options.output_dir

    logger.info("Processing input file '%s'." % input_path)
    logger.info("Storing results in '%s'." % output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # List requested data types.
    if options.data_type is not None:
        data_types = set(options.data_type)
    else:
        data_types = None

    # Process all data in the file.
    reader = MixedLogReader(input_path, show_progress=options.progress, ignore_index=options.ignore_index,
                            message_types=MessageType.INPUT_DATA_WRAPPER)

    files = {}
    def _get_entry(data_type):
        entry = files.get(data_type, None)
        if entry is None:
            prefix = os.path.splitext(os.path.basename(input_path))[0]
            path = os.path.join(output_dir, f'{prefix}.data_type_0x{data_type:x}.bin')
            entry = {'path': path, 'file': open(path, 'wb'), 'total_bytes': 0}
            files[data_type] = entry
        return entry

    for header, message in reader:
        if data_types is None or message.data_type in data_types:
            entry = _get_entry(message.data_type)
            entry['file'].write(message.data)
            entry['total_bytes'] += len(message.data)

    format_string = '| {:<9} | {:>13} | {:>50} |'
    logger.info(format_string.format('Data Type', 'Bytes Written', 'Path'))
    logger.info(format_string.format('-' * 9, '-' * 13, '-' * 50))
    for data_type, entry in files.items():
        logger.info(format_string.format(f'0x{data_type:x}', entry['total_bytes'], entry['path']))


if __name__ == "__main__":
    main()
