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
        os.exit(1)

    # Read pose data from the file.
    reader = FileReader(input_path)
    result = reader.read(message_types=[PoseMessage], show_progress=True)
    pose_data = result[PoseMessage.MESSAGE_TYPE]

    # Generate a CSV file.
    path = os.path.join(output_dir, 'position.csv')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write('GPS Time (sec), Solution Type, Lat (deg), Lon (deg), Ellipsoid Alt (m)\n')
        for message in pose_data.messages:
            if message.solution_type != SolutionType.Invalid and message.gps_time:
                f.write('%.3f, %d, %.8f, %.8f, %.3f\n' %
                        (float(message.gps_time), message.solution_type.value, *message.lla_deg))

    # Generate a KML file.
    path = os.path.join(output_dir, 'position.kml')
    logger.info("Generating '%s'." % path)
    with open(path, 'w') as f:
        f.write(KML_TEMPLATE %
                {'coordinates': '\n'.join(['%.8f,%.8f' % (message.lla_deg[1], message.lla_deg[0])
                                           for message in pose_data.messages
                                           if message.solution_type != SolutionType.Invalid])})

    logger.info("Storing output in '%s'." % os.path.abspath(output_dir))
