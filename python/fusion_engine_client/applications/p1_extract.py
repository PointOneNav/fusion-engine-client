#!/usr/bin/env python3

import os
import sys

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import MessagePayload, message_type_by_name
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser
from ..utils.log import extract_fusion_engine_log, find_log_file, CANDIDATE_LOG_FILES, DEFAULT_LOG_BASE_DIR


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
    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be extracted. May be specified "
             "multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). All matches are"
             "case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
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
    logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)
    logger = logging.getLogger('point_one.fusion_engine')
    if options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif options.verbose > 1:
        logger.setLevel(logging.getTraceLevel(depth=options.verbose - 1))

    # Locate the input file and set the output directory.
    try:
        if options.candidate_files is None:
            candidate_files = CANDIDATE_LOG_FILES
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
            logger.error(str(e))
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

    valid_count = extract_fusion_engine_log(input_path=input_path, output_path=output_path, message_types=message_types)
    if options.verbose == 0:
        # If verbose > 0, extract_fusion_engine_log() will log messages.
        if valid_count > 0:
            logger.info('Found %d valid FusionEngine messages.' % valid_count)
        else:
            logger.debug('No FusionEngine messages found.')

    logger.info(f"Output stored in '{output_path}'.")


if __name__ == "__main__":
    main()
