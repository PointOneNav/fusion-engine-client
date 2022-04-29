#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader, TimeAlignmentMode
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR

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

    # Read pose and satellite data from the file.
    #
    # Note that we are using insertion time alignment to align the requested message types by P1 timestamp. For any
    # timestamps where we have one message but not another, we will insert a default object. That way, even if we
    # started or stopped recording in between two messages, or if a message got dropped (CRC failure, etc.), there will
    # be an equal number of all message types and we can simply loop over them.
    reader = FileReader(input_path)
    result = reader.read(message_types=[PoseMessage, PoseAuxMessage, GNSSSatelliteMessage], show_progress=True,
                         time_align=TimeAlignmentMode.INSERT)
    pose_data = result[PoseMessage.MESSAGE_TYPE]
    pose_aux_data = result[PoseAuxMessage.MESSAGE_TYPE]
    satellite_data = result[GNSSSatelliteMessage.MESSAGE_TYPE]
    if len(pose_data.messages) == 0:
        logger.warning('No pose data found in log file.')
        sys.exit(2)

    # Generate a CSV file.
    path = os.path.join(output_dir, 'position.csv')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write('P1 Time (sec), GPS Time (sec), Solution Type, Lat (deg), Lon (deg), Ellipsoid Alt (m), # Satellites, '
                'Yaw (deg), Pitch, Roll, Velocity East (m/s), North, Up\n')
        for pose, pose_aux, gnss in zip(pose_data.messages, pose_aux_data.messages, satellite_data.messages):
            format = '%.6f, %.6f, %d, %.8f, %.8f, %.3f, %d, ' \
                     '%.1f, %.1f, %.1f, %.1f, %.1f, %.1f\n'
            f.write(format %
                    (pose.p1_time, pose.gps_time, pose.solution_type, *pose.lla_deg, len(gnss.svs),
                     *pose.ypr_deg, *pose_aux.velocity_enu_mps))

    # Generate a KML file.
    path = os.path.join(output_dir, 'position.kml')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write(KML_TEMPLATE %
                {'coordinates': '\n'.join(['%.8f,%.8f' % (message.lla_deg[1], message.lla_deg[0])
                                           for message in pose_data.messages
                                           if message.solution_type != SolutionType.Invalid])})

    logger.info("Storing output in '%s'." % os.path.abspath(output_dir))
