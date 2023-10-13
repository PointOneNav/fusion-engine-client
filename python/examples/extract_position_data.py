#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.analysis.data_loader import DataLoader, TimeAlignmentMode
from fusion_engine_client.messages.core import *
from fusion_engine_client.utils import trace as logging
from fusion_engine_client.utils.argument_parser import ArgumentParser
from fusion_engine_client.utils.log import locate_log, DEFAULT_LOG_BASE_DIR

KML_TEMPLATE_START = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
  <Document>
    <name>FusionEngine Trajectory</name>
    <Style id="type-0">
      <IconStyle>
        <scale>0.3</scale>
        <color>FF000000</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="type-1">
      <IconStyle>
        <scale>0.3</scale>
        <color>FF0000FF</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="type-2">
      <IconStyle>
        <scale>0.3</scale>
        <color>FFFF0000</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="type-4">
      <IconStyle>
        <scale>0.3</scale>
        <color>FF00A5FF</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="type-5">
      <IconStyle>
        <scale>0.3</scale>
        <color>FF008000</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <Style id="type-6">
      <IconStyle>
        <scale>0.3</scale>
        <color>FFFFFF00</color>
        <Icon>
          <href>https://maps.google.com/mapfiles/kml/shapes/road_shield3.png</href>
        </Icon>
      </IconStyle>
    </Style>
"""

KML_TEMPLATE_END = """\
  </Document>
</kml>
"""

KML_TEMPLATE = """\
    <Placemark>
      <TimeStamp><when>%(timestamp)s</when></TimeStamp>
      <styleUrl>#type-%(solution_type)d</styleUrl>
      <Point>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>%(coordinates)s</coordinates>
      </Point>
    </Placemark>
"""

KML_TEMPLATE_LOOKAT = """\
    <LookAt>
      <latitude>%(latitude).8f</latitude>
      <longitude>%(longitude).8f</longitude>
      <altitude>%(altitude).8f</altitude>
      <altitudeMode>absolute</altitudeMode>
      <range>250</range>
      <gx:TimeSpan>
        <begin>%(begin_time)s</begin>
        <end>%(end_time)s</end>
      </gx:TimeSpan>
    </LookAt>
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

    # Read pose and satellite data from the file.
    #
    # Note that we are using insertion time alignment to align the requested message types by P1 timestamp. For any
    # timestamps where we have one message but not another, we will insert a default object. That way, even if we
    # started or stopped recording in between two messages, or if a message got dropped (CRC failure, etc.), there will
    # be an equal number of all message types and we can simply loop over them.
    reader = DataLoader(input_path)
    result = reader.read(message_types=[PoseMessage, PoseAuxMessage, GNSSSatelliteMessage], show_progress=True,
                         time_align=TimeAlignmentMode.INSERT, return_numpy=True, keep_messages=True)
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
        f.write(KML_TEMPLATE_START)
        # Extract the first and last valid position.
        valid_solutions = np.where(pose_data.solution_type != SolutionType.Invalid)[0]
        first_valid_pose = pose_data.messages[valid_solutions[0]]
        last_valid_pose = pose_data.messages[valid_solutions[-1]]

        f.write(KML_TEMPLATE_LOOKAT %
          {'latitude': first_valid_pose.lla_deg[0],
          'longitude': first_valid_pose.lla_deg[1],
          'altitude': first_valid_pose.lla_deg[2] - first_valid_pose.undulation_m,
          'begin_time': str(first_valid_pose.gps_time.as_utc().isoformat()),
          'end_time': str(last_valid_pose.gps_time.as_utc().isoformat())}
        )
        for pose in pose_data.messages:
          # IMPORTANT: KML heights are specified in MSL, so we convert the ellipsoid heights to orthometric below using
          # the reported geoid undulation (geoid height). Undulation values come from a geoid model, and are not
          # typically precise. When analyzing position performance compared with another device, we strongly recommend
          # that you do the performance using ellipsoid heights. When comparing in MSL, if the geoid models used by the
          # two devices are not exactly the same, the heights may differ by multiple meters.
          f.write(KML_TEMPLATE %
                  {'timestamp': '\n'.join([str(pose.gps_time.as_utc().isoformat())]),
                  'solution_type': int(pose.solution_type),
                  'coordinates': '\n'.join(['%.8f,%.8f,%.8f' % (pose.lla_deg[1], pose.lla_deg[0], pose.lla_deg[2] - pose.undulation_m)])})

        f.write(KML_TEMPLATE_END)

    logger.info("Storing output in '%s'." % os.path.abspath(output_dir))
