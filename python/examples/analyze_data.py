#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Compute the average LLA position for the data contained in a *.p1log file.

Note that the specified file must contain only FusionEngine messages. For logs
containing mixed content, see separate_mixed_log.py.
""")
    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.DEBUG)

    # Read pose data from the file.
    reader = FileReader(options.file)
    result = reader.read(message_types=[PoseMessage], show_progress=True)

    # Print out the messages that were read.
    pose_data = result[PoseMessage.MESSAGE_TYPE]
    for message in pose_data.messages:
        logger.info(str(message))

    # Convert the data to numpy arrays for analysis, then compute and print the average LLA value.
    pose_data.to_numpy()
    mean_lla_deg = np.mean(pose_data.lla_deg, axis=1)
    logger.info('Average position: %.6f, %.6f, %.3f' % tuple(mean_lla_deg))
