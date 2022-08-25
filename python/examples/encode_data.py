#!/usr/bin/env python3

import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages.core import *
from fusion_engine_client.parsers import FusionEngineEncoder
from fusion_engine_client.utils.argument_parser import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Generate a .p1log file containing a few fixed FusionEngine messages as an
example of using the FusionEngineEncoder class to serialize data. Serialized
messages can be saved to disk, or sent to a FusionEngine device in real time.

The generated file can be used with any of the example analysis or extraction
scripts.
""")

    parser.add_argument('output', metavar='FILE', nargs='?', default='test_data.p1log',
                        help='The path to the .p1log file to be generated.')

    options = parser.parse_args()

    p1i_path = os.path.splitext(options.output)[0] + '.p1i'
    if os.path.exists(p1i_path):
        os.remove(p1i_path)

    print("Creating '%s'." % options.output)
    f = open(options.output, 'wb')

    encoder = FusionEngineEncoder()

    # P1 time 1.0
    message = PoseMessage()
    message.p1_time = Timestamp(1.0)
    message.solution_type = SolutionType.DGPS
    message.lla_deg = np.array([37.776417, -122.417711, 0.0])
    message.ypr_deg = np.array([45.0, 0.0, 0.0])
    f.write(encoder.encode_message(message))

    message = PoseAuxMessage()
    message.p1_time = Timestamp(1.0)
    message.velocity_enu_mps = np.array([0.1, 0.2, 0.3])
    f.write(encoder.encode_message(message))

    message = GNSSSatelliteMessage()
    message.p1_time = Timestamp(1.0)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 3
    message.svs.append(sv)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 4
    message.svs.append(sv)
    f.write(encoder.encode_message(message))

    # P1 time 2.0
    message = PoseMessage()
    message.p1_time = Timestamp(2.0)
    message.solution_type = SolutionType.DGPS
    message.lla_deg = np.array([37.776466, -122.417502, 0.1])
    message.ypr_deg = np.array([0.0, 0.0, 0.0])
    f.write(encoder.encode_message(message))

    # Note: Intentionally skipping this message so the file may be used when demonstrating time-aligned file reading.
    # message = PoseAuxMessage()
    # message.p1_time = Timestamp(2.0)
    # message.velocity_enu_mps = np.array([0.2, 0.3, 0.4])
    # f.write(encoder.encode_message(message))

    message = GNSSSatelliteMessage()
    message.p1_time = Timestamp(2.0)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 3
    message.svs.append(sv)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 4
    message.svs.append(sv)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 5
    message.svs.append(sv)
    f.write(encoder.encode_message(message))

    # P1 time 3.0
    message = PoseMessage()
    message.p1_time = Timestamp(3.0)
    message.solution_type = SolutionType.RTKFixed
    message.lla_deg = np.array([37.776407, -122.417369, 0.2])
    message.ypr_deg = np.array([-45.0, 0.0, 0.0])
    f.write(encoder.encode_message(message))

    message = PoseAuxMessage()
    message.p1_time = Timestamp(3.0)
    message.velocity_enu_mps = np.array([0.4, 0.5, 0.6])
    f.write(encoder.encode_message(message))

    # Note: Intentionally skipping this message so the file may be used when demonstrating time-aligned file reading.
    # message = GNSSSatelliteMessage()
    # message.p1_time = Timestamp(3.0)
    # sv = SatelliteInfo()
    # sv.system = SatelliteType.GPS
    # sv.prn = 3
    # message.svs.append(sv)
    # sv = SatelliteInfo()
    # sv.system = SatelliteType.GPS
    # sv.prn = 4
    # message.svs.append(sv)
    # sv = SatelliteInfo()
    # sv.system = SatelliteType.GPS
    # sv.prn = 5
    # message.svs.append(sv)
    # f.write(encoder.encode_message(message))

    # P1 time 4.0
    message = PoseMessage()
    message.p1_time = Timestamp(4.0)
    message.solution_type = SolutionType.RTKFixed
    message.lla_deg = np.array([37.776331, -122.417256, 0.3])
    message.ypr_deg = np.array([-45.0, 0.0, 0.0])
    f.write(encoder.encode_message(message))

    message = PoseAuxMessage()
    message.p1_time = Timestamp(4.0)
    message.velocity_enu_mps = np.array([0.5, 0.6, 0.7])
    f.write(encoder.encode_message(message))

    message = GNSSSatelliteMessage()
    message.p1_time = Timestamp(4.0)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 3
    message.svs.append(sv)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 4
    message.svs.append(sv)
    sv = SatelliteInfo()
    sv.system = SatelliteType.GPS
    sv.prn = 5
    message.svs.append(sv)
    f.write(encoder.encode_message(message))

    f.close()
