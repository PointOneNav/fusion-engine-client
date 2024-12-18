#!/usr/bin/env python3

from typing import Union

from datetime import datetime
import math
import os
import re
import select
import socket
import sys
import time

import colorama

try:
    # pySerial is optional.
    import serial
    serial_supported = True
except ImportError:
    serial_supported = False
    # Dummy stand-in if pySerial is not installed.
    class serial:
        class Serial: pass
        class SerialException: pass

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..parsers import FusionEngineDecoder
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.print_utils import \
    DeviceSummary, add_print_format_argument, print_message, print_summary_table

_logger = logging.getLogger('point_one.fusion_engine.applications.p1_capture')


def create_transport(descriptor: str) -> Union[socket.socket, serial.Serial]:
    m = re.match(r'^tcp://([a-zA-Z0-9-_.]+)?:([0-9]+)$', descriptor)
    if m:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((socket.gethostbyname(m.group(1)), int(m.group(2))))
        return transport

    m = re.match(r'^udp://:([0-9]+)$', descriptor)
    if m:
        transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind(('', int(m.group(1))))
        return transport

    m = re.match(r'^unix://([a-zA-Z0-9-_./]+)$', descriptor)
    if m:
        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        transport.connect(m.group(1))
        return transport

    m = re.match(r'^(?:(?:serial|tty)://)?([^:]+):([0-9]+)$', descriptor)
    if m:
        if serial_supported:
            transport = serial.Serial(port=m.group(1), baudrate=int(m.group(2)))
            return transport
        else:
            raise RuntimeError(
                "This application requires pyserial. Please install (pip install pyserial) and run again.")

    raise ValueError('Unsupported transport descriptor.')


def main():
    # Parse command-line arguments.
    parser = ArgumentParser(description="""\
Connect to a Point One device and print out the incoming FusionEngine message
contents and/or log the messages to disk.
""")
    add_print_format_argument(parser, '--display-format')
    parser.add_argument(
        '--display', action=ExtendedBooleanAction, default=True,
        help="Print the incoming message contents to the console.")
    parser.add_argument(
        '-q', '--quiet', dest='quiet', action=ExtendedBooleanAction, default=False,
        help="Do not print anything to the console.")
    parser.add_argument(
        '-s', '--summary', action=ExtendedBooleanAction, default=False,
        help="Print a summary of the incoming messages instead of the message content.")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    file_group = parser.add_argument_group('File Capture')
    file_group.add_argument(
        '-f', '--output-format', default='raw', choices=('p1log', 'raw', 'csv'),
        help="""\
The format of the file to be generated when --output is enabled:
- p1log - Create a *.p1log file containing only FusionEngine messages (default)
- raw - Create a generic binary file containing all incoming data
- csv - Create a CSV file with the received message types and timestamps""")
    file_group.add_argument(
        '-o', '--output', type=str,
        help="The path to a file where incoming data will be stored.")

    parser.add_argument(
        'transport',
        help="""\
The method used to communicate with the target device:
- tcp://HOSTNAME:PORT - Connect to the specified hostname (or IP address) and
  port over TCP (e.g., tty://192.168.0.3:30201)
- udp://:PORT - Listen for incoming data on the specified UDP port (e.g.,
  udp://:12345)
  Note: When using UDP, you must configure the device to send data to your
  machine.
- unix://FILENAME - Connect to the specified UNIX domain socket file
- [tty://]DEVICE:BAUD - Connect to a serial device with the specified baud rate
  (e.g., tty:///dev/ttyUSB0:460800 or /dev/ttyUSB0:460800) 
""")

    options = parser.parse_args()

    if options.quiet:
        options.display = False

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=sys.stdout)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    # Connect to the device using the specified transport.
    try:
        transport = create_transport(options.transport)
    except Exception as e:
        _logger.error(str(e))
        sys.exit(1)

    # Open the output file if logging was requested.
    if options.output is not None:
        if options.output_format == 'p1log':
            p1i_path = os.path.splitext(options.output)[0] + '.p1i'
            if os.path.exists(p1i_path):
                os.remove(p1i_path)

        output_file = open(options.output, 'wb')
    else:
        output_file = None

    generating_raw_log = (output_file is not None and options.output_format == 'raw')
    generating_p1log = (output_file is not None and options.output_format == 'p1log')
    generating_csv = (output_file is not None and options.output_format == 'csv')

    if generating_csv:
        output_file.write(b'host_time,type,p1_time,sys_time\n')

    # If this is a TCP/UDP socket, configure it for non-blocking reads. We'll apply a read timeout with select() below.
    read_timeout_sec = 1.0
    if isinstance(transport, socket.socket):
        transport.setblocking(0)
    # If this is a serial port, configure its read timeout.
    else:
        transport.timeout = read_timeout_sec

    # Listen for incoming data.
    decoder = FusionEngineDecoder(warn_on_unrecognized=not options.quiet and not options.summary, return_bytes=True)

    bytes_received = 0
    messages_received = 0
    device_summary = DeviceSummary()

    start_time = datetime.now()
    last_print_time = start_time
    print_timeout_sec = 1.0 if options.summary else 5.0

    def _print_status(now):
        if options.summary:
            # Clear the terminal.
            print(colorama.ansi.CSI + 'H' + colorama.ansi.CSI + 'J', end='')
        _logger.info('Status: [bytes_received=%d, messages_received=%d, elapsed_time=%d sec]' %
                     (bytes_received, messages_received, (now - start_time).total_seconds()))
        if options.summary:
            print_summary_table(device_summary)

    try:
        while True:
            # Read some data.
            try:
                # If this is a TCP/UDP socket, use select() to implement a read timeout so we can wakeup periodically
                # and print status if there's no incoming data.
                if isinstance(transport, socket.socket):
                    ready = select.select([transport], [], [], read_timeout_sec)
                    if ready[0]:
                        received_data = transport.recv(1024)
                    else:
                        received_data = []
                # If this is a serial port, we set the read timeout above.
                else:
                    received_data = transport.read(1024)

                bytes_received += len(received_data)

                now = datetime.now()
                if not options.quiet:
                    if (now - last_print_time).total_seconds() > print_timeout_sec:
                        _print_status(now)
                        last_print_time = now
            except serial.SerialException as e:
                _logger.error('Unexpected error reading from device:\r%s' % str(e))
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

            if options.display or generating_p1log:
                for (header, message, raw_data) in messages:
                    device_summary.update(header, message)

                    if generating_p1log:
                        output_file.write(raw_data)

                    if generating_csv:
                        p1_time = message.get_p1_time()
                        sys_time = message.get_system_time_sec()
                        p1_str = str(p1_time.seconds) if p1_time is not None and not math.isnan(p1_time) else ''
                        sys_str = str(sys_time) if sys_time is not None and not math.isnan(sys_time) else ''
                        output_file.write(
                            f'{time.monotonic()},{header.message_type},{p1_str},{sys_str}\n'.encode('utf-8'))

                    if options.display:
                        if options.summary:
                            if (now - last_print_time).total_seconds() > 0.1:
                                _print_status(now)
                        else:
                            print_message(header, message, format=options.display_format)
    except KeyboardInterrupt:
        pass

    # Close the transport.
    transport.close()

    # Close the output file.
    if output_file is not None:
        output_file.close()

    if not options.quiet and not options.summary:
        now = datetime.now()
        _print_status(now)


if __name__ == "__main__":
    main()
