#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.dump_p1bin import dump_p1bin
from fusion_engine_client.utils.log import find_log_file, DEFAULT_LOG_BASE_DIR


def main():
    parser = ArgumentParser(description="""\
Dump contents of a .p1bin file to individual binary files, separated by message
type.
""")

    parser.add_argument('--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
                             "specified.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the parent directory of the input"
                             "file, or to the log directory if reading from a log.")
    parser.add_argument('-p', '--prefix', type=str,
                        help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                             "filename of the input data file.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1bin file\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    # Configure logging.
    logger = logging.getLogger('point_one.fusion_engine')
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logger.setLevel(logging.DEBUG)
        elif options.verbose > 1:
            logger.setLevel(logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    # Locate the input file and set the output directory.
    try:
        input_path, output_dir, log_id = find_log_file(options.log, candidate_files='input.p1bin',
                                                       return_output_dir=True, return_log_id=True,
                                                       log_base_dir=options.log_base_dir)

        if log_id is None:
            logger.info('Loading %s.' % os.path.basename(input_path))
        else:
            logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if options.output is not None:
            output_dir = options.output
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Parse each entry in the .p1bin file and extract its contents to 'output_dir/<prefix>.message_type.bin', where
    # message_type is the numeric type identifier.
    if options.prefix is not None:
        prefix = options.prefix
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]

    valid_count, out_files = dump_p1bin(input_path=input_path, output_dir=output_dir, prefix=prefix)
    logger.info(f'Found {valid_count} messages of types {list(out_files.keys())}')
    logger.info(f"Output stored in '{output_dir}'.")


if __name__ == "__main__":
    main()
