#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils.log import find_p1bin

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
    parser.add_argument('file', type=str,
                        help="The path to a binary file to be read, or to an Atlas log containing FusionEngine output.")
    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.INFO)

    # Locate the input file and set the output directory.
    try:
        input_path, output_dir, log_id = find_p1bin(options.file, return_output_dir=True, return_log_id=True)

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

    # Generate a CVS file.
    pose_data = result[PoseMessage.MESSAGE_TYPE]
    with open(os.path.join(output_dir, 'position.csv'), 'w') as f:
        f.write('GPS Time (sec), Solution Type, Lat (deg), Lon (deg), Ellipsoid Alt (m)\n')
        for message in pose_data.messages:
            if message.solution_type != SolutionType.Invalid and message.gps_time:
                f.write('%.3f, %d, %.8f, %.8f, %.3f\n' %
                        (float(message.gps_time), message.solution_type.value, *message.lla_deg))

    # Generate a KML file.
    with open(os.path.join(output_dir, 'position.kml'), 'w') as f:
        f.write(KML_TEMPLATE %
                {'coordinates': '\n'.join(['%.8f,%.8f' % (message.lla_deg[1], message.lla_deg[0])
                                           for message in pose_data.messages
                                           if message.solution_type != SolutionType.Invalid])})

    logger.info("Output stored in '%s'." % os.path.abspath(output_dir))
