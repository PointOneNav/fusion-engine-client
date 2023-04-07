#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.analysis.data_loader import DataLoader
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR
from fusion_engine_client.utils.argument_parser import ArgumentParser

if __name__ == "__main__":
    # Parse arguments.
    parser = ArgumentParser(description="""\
Extract IMU accelerometer and gyroscope measurements.
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

    # Configure logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s', stream=sys.stdout)
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

    # Read satellite data from the file.
    reader = DataLoader(input_path)
    result = reader.read(message_types=[IMUOutput], show_progress=True)
    imu_data = result[IMUOutput.MESSAGE_TYPE]
    if len(imu_data.messages) == 0:
        logger.warning('No IMU data found in log file.')
        sys.exit(2)

    # Generate a CSV file.
    path = os.path.join(output_dir, 'imu_data.csv')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write('P1 Time (sec), Accel X (m/s^2), Y, Z, Gyro X (rad/s), Y, Z\n')
        for message in imu_data.messages:
            f.write('%.6f, %.6f, %.6f, %.6f, %.6f, %.6f, %.6f\n' %
                    (float(message.p1_time), *message.accel_mps2, *message.gyro_rps))

    logger.info("Output stored in '%s'." % os.path.abspath(output_dir))
