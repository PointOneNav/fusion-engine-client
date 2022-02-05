#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.log import find_p1log_file

if __name__ == "__main__":
    # Parse arguments.
    parser = ArgumentParser(description="""\
Extract IMU accelerometer and gyroscope measurements.

Note that the specified file must contain only FusionEngine messages. For logs
containing mixed content, see separate_mixed_log.py.
""")
    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is "
                             "specified.")
    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1log file\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")
    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.INFO)

    # Locate the input file and set the output directory.
    try:
        input_path, output_dir, log_id = find_p1log_file(options.log, return_output_dir=True, return_log_id=True,
                                                         log_base_dir=options.log_base_dir)

        if log_id is None:
            logger.info('Loading %s.' % os.path.basename(input_path))
        else:
            logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Read satellite data from the file.
    reader = FileReader(input_path)
    result = reader.read(message_types=[IMUMeasurement], show_progress=True)
    imu_data = result[IMUMeasurement.MESSAGE_TYPE]
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
