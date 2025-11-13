#!/usr/bin/env python3

from datetime import datetime
import math
import os
import select
import sys
from typing import Optional

import colorama

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import MessagePayload, message_type_by_name
from ..parsers import FusionEngineDecoder
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.print_utils import \
    DeviceSummary, add_print_format_argument, print_message, print_summary_table
from ..utils.socket_timestamping import (enable_socket_timestamping,
                                         HW_TIMESTAMPING_HELP,
                                         log_timestamped_data_offset,
                                         recv,
                                         TIMESTAMP_FILE_ENDING,)
from ..utils.transport_utils import *
from ..utils.trace import HighlightFormatter, BrokenPipeStreamHandler

_logger = logging.getLogger('point_one.fusion_engine.applications.p1_capture')


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
        '-m', '--message-type', type=str, action='append',
        help="An optional list of class names corresponding with the message types to be displayed. May be specified "
             "multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). All matches are"
             "case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
             "Note: This applies to the displayed messages only. All incoming data will still be stored on disk if "
             "--output is specified.\n"
             "\n"
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
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
- p1log - Create a *.p1log file containing only FusionEngine messages
- raw - Create a generic binary file containing all incoming data
- csv - Create a CSV file with the received message types and timestamps""")
    parser.add_argument(
        '--log-timestamp-source', default=None, choices=('user-sw', 'kernel-sw', 'hw'),
        help=f"""\
Create a mapping between the host timestamps and the output file data.
For CSV files, this will change the source of the host_time column.
For p1log or raw logs, the timestamps will be written as a binary file name <OUT_FILE>{TIMESTAMP_FILE_ENDING}.
The data is pairs of uint64. First, the timestamp in nanoseconds followed by the byte offset in the data file.
- user-sw - Log timestamps from python code. This is the only option available for serial data.
- kernel-sw - Log kernel SW timestamps. This is only available for socket connections.
- hw - Log HW timestamps from device driver. This needs HW driver support. Run `./fusion_engine_client/utils/socket_timestamping.py` to test.""")
    file_group.add_argument(
        '-o', '--output', type=str,
        help="If specified, save the incoming data in the specified file.")

    parser.add_argument(
        'transport', type=str,
        help=TRANSPORT_HELP_STRING)

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

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)
    BrokenPipeStreamHandler.install()

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = None
    if options.message_type is not None:
        # Pattern match to any of:
        #   -m Type1
        #   -m Type1 -m Type2
        #   -m Type1,Type2
        #   -m Type1,Type2 -m Type3
        #   -m Type*
        try:
            message_types = MessagePayload.find_matching_message_types(options.message_type)
            if len(message_types) == 0:
                # find_matching_message_types() will print an error.
                sys.exit(1)
        except ValueError as e:
            _logger.error(str(e))
            sys.exit(1)

    # Connect to the device using the specified transport.
    try:
        transport = create_transport(options.transport)
    except Exception as e:
        _logger.error(str(e))
        sys.exit(1)

    # Open the output file if logging was requested.
    timestamp_file = None
    if options.output is not None:
        if options.output_format == 'p1log':
            p1i_path = os.path.splitext(options.output)[0] + '.p1i'
            if os.path.exists(p1i_path):
                os.remove(p1i_path)

        output_file = open(options.output, 'wb')

        if options.log_timestamp_source and options.output_format != 'csv':
            timestamp_file = open(options.output + TIMESTAMP_FILE_ENDING, 'wb')
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
        # This function won't do anything if neither timestamp is enabled.
        enable_socket_timestamping(
            transport,
            enable_sw_timestamp=options.log_timestamp_source == 'kernel-sw',
            enable_hw_timestamp=options.log_timestamp_source == 'hw'
        )
    # If this is a serial port, configure its read timeout.
    else:
        if options.log_timestamp_source and options.log_timestamp_source != 'user-sw':
            _logger.error(f'--log-timestamp-source={options.log_timestamp_source} is not supported. Only "user-sw" timestamps are supported on serial port captures.')
            sys.exit(1)
        transport.timeout = read_timeout_sec

    # Listen for incoming data.
    decoder = FusionEngineDecoder(warn_on_unrecognized=not options.quiet and not options.summary, return_bytes=True)

    bytes_received = 0
    fe_bytes_received = 0
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
            kernel_ts: Optional[float] = None
            hw_ts: Optional[float] = None
            # Read some data.
            try:
                # If this is a TCP/UDP socket, use select() to implement a read timeout so we can wakeup periodically
                # and print status if there's no incoming data.
                if isinstance(transport, socket.socket):
                    ready = select.select([transport], [], [], read_timeout_sec)
                    if ready[0]:
                        received_data, kernel_ts, hw_ts = recv(transport, 1024)
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

            if options.log_timestamp_source == 'kernel-sw':
                if kernel_ts is None:
                    _logger.error(f'Unable to capture kernel SW timestamps on {options.transport}.')
                    sys.exit(1)
                timestamp_sec = kernel_ts
            elif options.log_timestamp_source == 'hw':
                if hw_ts is None:
                    _logger.error(f'Unable to capture HW timestamps on {options.transport}.\n{HW_TIMESTAMPING_HELP}')
                    sys.exit(1)
                timestamp_sec = hw_ts
            else:
                timestamp_sec = now.timestamp()
            timestamp_ns = int(round(timestamp_sec * 1e9))

            # If logging in raw format, write the data to disk as is.
            if generating_raw_log:
                output_file.write(received_data)
                if timestamp_file:
                    log_timestamped_data_offset(timestamp_file, timestamp_ns, bytes_received)


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
                    fe_bytes_received += len(raw_data)
                    device_summary.update(header, message)

                    if generating_p1log:
                        output_file.write(raw_data)
                        if timestamp_file:
                            log_timestamped_data_offset(timestamp_file, timestamp_ns, fe_bytes_received)

                    if generating_csv:
                        p1_time = message.get_p1_time()
                        sys_time = message.get_system_time_sec()
                        p1_str = str(p1_time.seconds) if p1_time is not None and not math.isnan(p1_time) else ''
                        sys_str = str(sys_time) if sys_time is not None and not math.isnan(sys_time) else ''
                        output_file.write(
                            f'{timestamp_sec},{header.message_type},{p1_str},{sys_str}\n'.encode('utf-8'))

                    if options.display:
                        if options.summary:
                            if (now - last_print_time).total_seconds() > 0.1:
                                _print_status(now)
                        elif message_types is None or header.message_type in message_types:
                            print_message(header, message, format=options.display_format)
    except (BrokenPipeError, KeyboardInterrupt) as e:
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
