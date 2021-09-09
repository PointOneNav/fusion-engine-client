#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

import numpy as np

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.log import find_p1log_file

KML_TEMPLATE = """\
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Position</name>
      <Style>
        <LineStyle>
          <width>8</width>
          <color>#ff0000ff</color>
        </LineStyle>
      </Style>
      <LineString>
        <extrude>0</extrude>
        <tesselate>1</tesselate>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>
%(coordinates)s
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""

if __name__ == "__main__":
    # Parse arguments.
    parser = ArgumentParser(description="""\
Extract position data to both CSV and KML files.  
""")
    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
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

    # Read pose and satellite data from the file.
    #
    # Note that we explicitly tell the reader to convert the data to numpy for use below. We also tell it to keep the
    # original PoseMessage and GNSSSatelliteMessage objects.
    reader = FileReader(input_path)
    result = reader.read(message_types=[PoseMessage, GNSSSatelliteMessage], show_progress=True,
                         return_numpy=True, keep_messages=True)
    pose_data = result[PoseMessage.MESSAGE_TYPE]
    satellite_data = result[GNSSSatelliteMessage.MESSAGE_TYPE]
    if len(pose_data.messages) == 0:
        logger.warning('No pose data found in log file.')
        sys.exit(2)

    # Generate a CSV file.
    path = os.path.join(output_dir, 'position.csv')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write('P1 Time (sec), GPS Time (sec), Solution Type, Lat (deg), Lon (deg), Ellipsoid Alt (m), # Satellites\n')

        # If we do not have satellite data present in the log, we'll simply loop over the pose messages and write them
        # to the file.
        if len(satellite_data.messages) == 0:
            for message in pose_data.messages:
                if message.solution_type != SolutionType.Invalid:
                    # Note we set # satellites to 0 here since it is unknown.
                    f.write('%.6f, %.6f, %d, %.8f, %.8f, %.3f, %d\n' %
                            (float(message.p1_time), float(message.gps_time),
                             message.solution_type.value, *message.lla_deg, 0))
        # If we do have satellite data, we can then time-align the two message types using their P1 timestamps. That
        # way, the generated CSV file can include both position and satellite count for each time.
        else:
            # First, find the intersection of the pose and satellite data. Note that we do not assume we have the same
            # number of messages for both types since, if the data was recorded remotely, we may have connected to the
            # device between messages.
            _, pose_idx, satellite_idx = np.intersect1d(pose_data.p1_time, satellite_data.p1_time, return_indices=True)

            # Generate a set of satellite counts for each position epoch.
            num_svs = np.full_like(pose_data.p1_time, 0, dtype=int)
            num_svs[pose_idx] = satellite_data.num_svs[satellite_idx]

            # Write out the position data with corresponding SV counts, or 0 where not available.
            for i in range(len(pose_data.p1_time)):
                f.write('%.6f, %.6f, %d, %.8f, %.8f, %.3f, %d\n' %
                        (pose_data.p1_time[i], pose_data.gps_time[i],
                         pose_data.solution_type[i], *pose_data.lla_deg[:, i], num_svs[i]))

    # Generate a KML file.
    path = os.path.join(output_dir, 'position.kml')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write(KML_TEMPLATE %
                {'coordinates': '\n'.join(['%.8f,%.8f' % (message.lla_deg[1], message.lla_deg[0])
                                           for message in pose_data.messages
                                           if message.solution_type != SolutionType.Invalid])})

    logger.info("Storing output in '%s'." % os.path.abspath(output_dir))
