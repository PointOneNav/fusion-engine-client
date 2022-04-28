#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils import trace
from fusion_engine_client.utils.log import extract_fusion_engine_log, find_log_file, CANDIDATE_MIXED_FILES, \
    DEFAULT_LOG_BASE_DIR


def main():
    parser = ArgumentParser(description="""\
Extract FusionEngine message contents from a binary file containing mixed data
(e.g., interleaved RTCM and FusionEngine messages).
""")

    parser.add_argument('--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
                             "specified.")
    parser.add_argument('-c', '--candidate-files', type=str, metavar='DIR',
                        help="An optional comma-separated list of candidate input filenames to search within the log "
                             "directory.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the parent directory of the input"
                             "file, or to the log directory if reading from a log.")
    parser.add_argument('-p', '--prefix', type=str,
                        help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                             "filename of the input data file (e.g., `input.p1log`), or `fusion_engine` if reading "
                             "from a log (e.g., `fusion_engine.p1log`).")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a binary data file\n"
                             "- The path to a FusionEngine log directory containing a candidate binary data file\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    if options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif options.verbose > 1:
        logger.setLevel(logging.TRACE)

    # Locate the input file and set the output directory.
    try:
        if options.candidate_files is None:
            candidate_files = CANDIDATE_MIXED_FILES
        else:
            candidate_files = options.candidate_files.split(',')

        input_path, output_dir, log_id = find_log_file(options.log, candidate_files=candidate_files,
                                                       return_output_dir=True, return_log_id=True,
                                                       log_base_dir=options.log_base_dir)

        if log_id is None:
            print('Loading %s.' % os.path.basename(input_path))
        else:
            print('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if options.output is not None:
            output_dir = options.output
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    # Read through the data file, searching for valid FusionEngine messages to extract and store in
    # 'output_dir/<prefix>.p1log'.
    if options.prefix is not None:
        prefix = options.prefix
    elif log_id is not None:
        prefix = 'fusion_engine'
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, prefix + '.p1log')

    valid_count = extract_fusion_engine_log(input_path, output_path)
    if options.verbose == 0:
        # If verbose > 0, extract_fusion_engine_log() will log messages.
        if valid_count > 0:
            logger.info('Found %d valid FusionEngine messages.' % valid_count)
        else:
            logger.debug('No FusionEngine messages found.')

    logger.info(f"Output stored in '{output_path}'.")


if __name__ == "__main__":
    main()
