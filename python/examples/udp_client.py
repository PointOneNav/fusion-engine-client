from argparse import ArgumentParser
import os
import socket
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.core import *

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=12345,
                        help="The UDP port to which messages are being sent.")
    options = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', options.port))

    while True:
        # Read the next packet.
        data = sock.recv(1024)

        # Deserialize the header.
        header = MessageHeader()
        offset = header.unpack(buffer=data)

        # Validate the message length and CRC.
        if len(data) != header.calcsize() + header.payload_size_bytes:
            break
        else:
            header.validate_crc(data)

        # Deserialize and print the message contents.
        if header.message_type == PoseMessage.MESSAGE_TYPE:
            contents = PoseMessage()
            contents.unpack(buffer=data, offset=offset)

            print('Pose message @ P1 time %s' % str(contents.p1_time))
            print('  GPS time: %s' % str(contents.gps_time.as_gps()))
            print('  LLA: %.6f, %.6f, %.3f (deg, deg, m)' % tuple(contents.lla_deg))
            print('  YPR: %.2f, %.2f, %.2f (deg, deg, deg)' % tuple(contents.ypr_deg))
        elif header.message_type == GNSSInfoMessage.MESSAGE_TYPE:
            contents = GNSSInfoMessage()
            contents.unpack(buffer=data, offset=offset)

            print('GNSS info message @ P1 time %s' % str(contents.p1_time))
            print('  GPS time: %s' % str(contents.gps_time.as_gps()))
            print('  GDOP: %.1f' % contents.gdop)
            print('  %d SVs:' % len(contents.svs))
            for sv in contents.svs:
                print('    %s PRN %d:' % (sv.system.name, sv.prn))
                print('      Used in solution: %s' % ('yes' if sv.used_in_solution else 'no'))
                print('      Az/el: %.1f, %.1f deg' % (sv.azimuth_deg, sv.elevation_deg))
