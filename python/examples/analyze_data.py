#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Compute the average LLA position for the data contained in a *.p1log file.
""")
    parser.add_argument('--log-base-dir', metavar='DIR', default=DEFAULT_LOG_BASE_DIR,
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is "
                             "specified.")
    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1log file or a file containing FusionEngine messages and other "
                             "content\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")
    options = parser.parse_args()

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.INFO)

    # Locate the input file and set the output directory.
    input_path, output_dir, log_id = locate_log(options.log, return_output_dir=True, return_log_id=True,
                                                log_base_dir=options.log_base_dir)
    if input_path is None:
        sys.exit(1)

    if log_id is None:
        logger.info('Loading %s.' % os.path.basename(input_path))
    else:
        logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

    # Read pose data from the file.
    #
    # Note that we explicitly ask the FileReader to return the data converted to numpy arrays so we can analyze it
    # below.
    reader = FileReader(input_path)
    result = reader.read(message_types=[PoseMessage], show_progress=True, return_numpy=True)

    # Print out the messages that were read.
    pose_data = result[PoseMessage.MESSAGE_TYPE]
    for message in pose_data.messages:
        logger.info(str(message))

    # Compute and print the average LLA value. Limit only to valid solutions.
    idx = pose_data.solution_type != SolutionType.Invalid
    mean_lla_deg = np.mean(pose_data.lla_deg[:, idx], axis=1)
    logger.info('Average position: %.6f, %.6f, %.3f' % tuple(mean_lla_deg))
