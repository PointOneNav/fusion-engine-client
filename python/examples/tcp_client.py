#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import datetime
import os
import socket
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.parsers import FusionEngineDecoder

from examples.message_decode import print_message


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to an Atlas device over TCP and print out the incoming message
contents and/or log the messages to disk.
""")

    parser.add_argument('-n', '--no-display', dest='display', action='store_false',
                        help="Do not display the incoming message contents.")
    parser.add_argument('-o', '--output', type=str,
                        help="The path to a *.p1log file where incoming data will be stored.")
    parser.add_argument('-p', '--port', type=int, default=30201,
                        help="The FusionEngine TCP port on the Atlas device.")
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                        help="Do not print anything to the console.")

    parser.add_argument('ip_address',
                        help="The IP address of the Atlas device.")
    options = parser.parse_args()

    if options.quiet:
        options.display = False

    # Open the output file if logging was requested.
    if options.output is not None:
        p1i_path = os.path.splitext(options.output)[0] + '.p1i'
        if os.path.exists(p1i_path):
            os.remove(p1i_path)

        output_file = open(options.output, 'wb')
    else:
        output_file = None

    # Connect to the device.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((options.ip_address, options.port))

    # Listen for incoming data.
    decoder = FusionEngineDecoder(warn_on_unrecognized=not options.quiet)
    bytes_received = 0
    messages_received = 0
    last_print_time = None
    while True:
        # Read some data.
        try:
            received_data = sock.recv(1024)
            bytes_received += len(received_data)

            if not options.quiet:
                now = datetime.now()
                elapsed_sec = (now - last_print_time).total_seconds() if last_print_time else 0.0
                if last_print_time is None or elapsed_sec > 5.0:
                    print('Status: [bytes_received=%d, messages_received=%d elapsed_time=%d sec]' %
                          (bytes_received, messages_received, elapsed_sec))
                    last_print_time = now
        except KeyboardInterrupt:
            break

        # Write the data to disk.
        if output_file is not None:
            output_file.write(received_data)

        # Decode the incoming data and print the contents of any complete messages.
        #
        # Note that we pass the data to the decoder, even if --no-display was requested, so that we get a count of the
        # number of incoming messages, and so we print warnings if the CRC fails on any of the incoming data.
        messages = decoder.on_data(received_data)
        messages_received += len(messages)

        if options.display:
            for (header, message) in messages:
                print_message(header, message)

    # Close the socket.
    sock.close()

    # Close the output file.
    if output_file is not None:
        output_file.close()

    if not options.quiet:
        now = datetime.now()
        elapsed_sec = (now - last_print_time).total_seconds() if last_print_time else 0.0
        print('Status: [bytes_received=%d, messages_received=%d elapsed_time=%d sec]' %
              (bytes_received, messages_received, elapsed_sec))
