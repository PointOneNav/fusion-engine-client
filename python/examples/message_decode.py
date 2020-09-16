from argparse import ArgumentParser
import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('file', type=str, help="The path to a binary file to be read.")
    options = parser.parse_args()

    f = open(options.file, 'rb')

    expected_sequence_number = 0
    while True:
        # Read the next message header.
        data = f.read(MessageHeader.calcsize())
        if len(data) == 0:
            break

        # Deserialize the header.
        header = MessageHeader()
        offset = header.unpack(buffer=data)

        # Read the message payload and append it to the header.
        data += f.read(header.payload_size_bytes)

        # Validate the message length and CRC.
        if len(data) != header.calcsize() + header.payload_size_bytes:
            break
        else:
            header.validate_crc(data)

        # Check that the sequence number increments as expected.
        if header.sequence_number != expected_sequence_number:
            print('Warning: unexpected sequence number. [expected=%d, received=%d]' %
                  (expected_sequence_number, header.sequence_number))

        expected_sequence_number = header.sequence_number + 1

        # Deserialize and print the message contents.
        if header.message_type == PoseMessage.MESSAGE_TYPE:
            contents = PoseMessage()
            contents.unpack(buffer=data, offset=offset)

            print('Pose message @ P1 time %s [sequence=%d, size=%d B]' %
                  (str(contents.p1_time), header.sequence_number, len(data)))
            print('  GPS time: %s' % str(contents.gps_time.as_gps()))
            print('  Position (LLA): %.6f, %.6f, %.3f (deg, deg, m)' % tuple(contents.lla_deg))
            print('  Attitude (YPR): %.2f, %.2f, %.2f (deg, deg, deg)' % tuple(contents.ypr_deg))
            print('  Velocity (ENU): %.2f, %.2f, %.2f (m/s, m/s, m/s)' % tuple(contents.velocity_enu_mps))
            print('  Position std (ECEF): %.2f, %.2f, %.2f (m, m, m)' % tuple(contents.position_std_ecef_m))
            print('  Attitude std (YPR): %.2f, %.2f, %.2f (deg, deg, deg)' % tuple(contents.ypr_std_deg))
            print('  Velocity std (ENU): %.2f, %.2f, %.2f (m/s, m/s, m/s)' % tuple(contents.velocity_std_enu_mps))
            print('  Protection levels:')
            print('    Aggregate: %.2f m' % contents.aggregate_protection_level_m)
            print('    Horizontal: %.2f m' % contents.horizontal_protection_level_m)
            print('    Vertical: %.2f m' % contents.vertical_protection_level_m)
        elif header.message_type == GNSSInfoMessage.MESSAGE_TYPE:
            contents = GNSSInfoMessage()
            contents.unpack(buffer=data, offset=offset)

            print('GNSS info message @ P1 time %s [sequence=%d, size=%d B]' %
                  (str(contents.p1_time), header.sequence_number, len(data)))
            print('  GPS time: %s' % str(contents.gps_time.as_gps()))
            print('  GDOP: %.1f' % contents.gdop)
            print('  %d SVs:' % len(contents.svs))
            for sv in contents.svs:
                print('    %s PRN %d:' % (sv.system.name, sv.prn))
                print('      Used in solution: %s' % ('yes' if sv.used_in_solution else 'no'))
                print('      Az/el: %.1f, %.1f deg' % (sv.azimuth_deg, sv.elevation_deg))
