#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.analysis.file_reader import FileReader
from fusion_engine_client.messages.core import *

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
    parser = ArgumentParser()
    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    input_path = options.file
    output_dir = os.path.dirname(input_path)

    # Configure logging.
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    logger = logging.getLogger('point_one.fusion_engine')
    logger.setLevel(logging.INFO)

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
