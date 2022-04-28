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
    # Parse arguments.
    parser = ArgumentParser(description="""\
Extract satellite azimuth, elevation, and L1 signal C/N0 data to a CSV file.
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

    # Read satellite data from the file.
    reader = FileReader(input_path)
    result = reader.read(message_types=[GNSSSatelliteMessage], show_progress=True)
    satellite_data = result[GNSSSatelliteMessage.MESSAGE_TYPE]
    if len(satellite_data.messages) == 0:
        logger.warning('No satellite data found in log file.')
        sys.exit(2)

    # Generate a CSV file.
    path = os.path.join(output_dir, 'satellite_info.csv')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write('P1 Time (sec), GPS Time (sec), System, PRN, Azimuth (deg), Elevation (deg), C/N0 (dB-Hz)\n')
        for message in satellite_data.messages:
            if message.gps_time:
                for sv in message.svs:
                    f.write('%.6f, %.6f, %d, %d, %.1f, %.1f, %f\n' %
                            (float(message.p1_time), float(message.gps_time),
                             int(sv.system), sv.prn, sv.azimuth_deg, sv.elevation_deg, sv.cn0_dbhz))

    logger.info("Output stored in '%s'." % os.path.abspath(output_dir))
