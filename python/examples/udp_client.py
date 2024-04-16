#!/usr/bin/env python3

from datetime import datetime
import os
import math
import socket
import sys
import time

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.applications.p1_print import add_print_format_argument, print_message
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.argument_parser import ArgumentParser


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Connect to a Point One device over UDP and print out the incoming message
contents and/or log the messages to disk.

When using UDP, you must configure the device to send data to your machine.
""")

    add_print_format_argument(parser, '--display-format')
    parser.add_argument('-f', '--format', default='p1log', choices=('p1log', 'raw', 'csv'),
                        help="""\
The format of the file to be generated when --output is enabled:
- p1log - (default), create a *.p1log file containing only FusionEngine messages."
- raw - create a generic binary file containing all incoming data."
- csv - create a csv of time vs message type.""")
    parser.add_argument('-n', '--no-display', dest='display', action='store_false',
                        help="Do not display the incoming message contents.")
    parser.add_argument('-o', '--output', type=str,
                        help="The path to a file where incoming data will be stored.")
    parser.add_argument('-p', '--port', type=int, default=30400,
                        help="The FusionEngine UDP port on the data source.")
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                        help="Do not print anything to the console.")
    options = parser.parse_args()

    if options.quiet:
        options.display = False

    # Open the output file if logging was requested.
    if options.output is not None:
        if options.format == 'p1log':
            p1i_path = os.path.splitext(options.output)[0] + '.p1i'
            if os.path.exists(p1i_path):
                os.remove(p1i_path)

        output_file = open(options.output, 'wb')
    else:
        output_file = None

    generating_raw_log = (output_file is not None and options.format == 'raw')
    generating_p1log = (output_file is not None and options.format == 'p1log')
    generating_csv = (output_file is not None and options.format == 'csv')

    if generating_csv:
        output_file.write(b'host_time,type,p1_time,sys_time\n')

    # Connect to the device.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', options.port))

    # Listen for incoming data.
    decoder = FusionEngineDecoder(warn_on_unrecognized=not options.quiet, return_bytes=True)
    bytes_received = 0
    messages_received = 0
    start_time = datetime.now()
    last_print_time = start_time
    while True:
        # Read some data.
        try:
            received_data = sock.recv(1024)
            bytes_received += len(received_data)

            if not options.quiet:
                now = datetime.now()
                if (now - last_print_time).total_seconds() > 5.0:
                    print('Status: [bytes_received=%d, messages_received=%d, elapsed_time=%d sec]' %
                          (bytes_received, messages_received, (now - start_time).total_seconds()))
                    last_print_time = now
        except KeyboardInterrupt:
            break

        # If logging in raw format, write the data to disk as is.
        if generating_raw_log:
            output_file.write(received_data)

        # Decode the incoming data and print the contents of any complete messages.
        #
        # Note that we pass the data to the decoder, even if --no-display was requested, for three reasons:
        # - So that we get a count of the number of incoming messages
        # - So we print warnings if the CRC fails on any of the incoming data
        # - If we are logging in *.p1log format, so the decoder can extract the FusionEngine data from any
        #   non-FusionEngine data in the stream
        messages = decoder.on_data(received_data)
        messages_received += len(messages)

        if options.display or generating_p1log or generating_csv:
            for (header, message, raw_data) in messages:
                if generating_p1log:
                    output_file.write(raw_data)

                if options.display:
                    print_message(header, message, format=options.display_format)

                if generating_csv:
                    p1_time = message.get_p1_time()
                    sys_time = message.get_system_time_sec()
                    p1_str = str(p1_time.seconds) if p1_time is not None and not math.isnan(p1_time) else ''
                    sys_str = str(sys_time) if sys_time is not None and not math.isnan(sys_time) else ''
                    output_file.write(f'{time.monotonic()},{header.message_type},{p1_str},{sys_str}\n'.encode('utf-8'))


    # Close the socket.
    sock.close()

    # Close the output file.
    if output_file is not None:
        output_file.close()

    if not options.quiet:
        now = datetime.now()
        elapsed_sec = (now - last_print_time).total_seconds() if last_print_time else 0.0
        print('Status: [bytes_received=%d, messages_received=%d, elapsed_time=%d sec]' %
              (bytes_received, messages_received, elapsed_sec))
