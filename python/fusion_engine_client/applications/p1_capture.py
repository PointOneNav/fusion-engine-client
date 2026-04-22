#!/usr/bin/env python3

from datetime import datetime
import math
import os
import select
import sys
import time
from typing import Optional

import colorama

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import InputDataType, MessagePayload, MessageType, message_type_by_name
from ..parsers import FusionEngineDecoder
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from ..utils.print_utils import \
    DeviceSummary, add_print_format_argument, add_wrapped_data_mode_argument, print_message, print_summary_table
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
Connect to a Point One device in real time over TCP, UDP, UNIX socket, etc.,
or read logged data from a file for post-processing, then filter/display the
incoming FusionEngine messages. The data may also be logged to disk or sent to
another application, either over stdout or a specified transport.

Examples:
  # Connect to a device over TCP and display a summary of the incoming data.
  ./p1_capture.py tcp://192.168.1.138:30202 --summary

  # Display the contents of all messages received from a device in real time.
  ./p1_capture.py tcp://192.168.1.138:30202 --display

  # Log device output to disk.
  ./p1_capture.py tcp://192.168.1.138:30202 --output=/tmp/output.p1log

  # Remove GNSSSignals messages from the data stream of a device connected over
  # TCP, and log the results to disk.
  ./p1_capture.py tcp://192.168.1.138:30202 \
      --invert --message-type=GNSSSignals --output=/tmp/output.p1log

  # Same as above, but capture data using netcat.
  netcat 192.168.1.138 30202 | \
      ./p1_capture.py --invert --message-type=GNSSSignals \
      --output=/tmp/output.p1log

  # Filter a recorded data file and only keep Pose messages.
  ./p1_capture.py /tmp/output.p1log --message-type=Pose \
      --output=/tmp/pose_output.p1log

  # Filter an incoming serial data stream in real time and only keep Pose
  # messages.
  ./p1_capture.py tty:///dev/ttyUSB0:460800 --message-type=Pose \
      --output=/tmp/pose_output.p1log

  # Similar to above, but open the serial port manually using stty and cat.
  stty -F /dev/ttyUSB0 speed 460800 cs8 \
      -cstopb -parenb -icrnl -ixon -ixoff -opost -isig -icanon -echo && \
      cat /dev/ttyUSB0 | \
      ./p1_capture.py --message-type=Pose --output=/tmp/pose_output.p1log

  # Extract GNSS receiver data in its native format (RTCM, SBF, etc.) from a
  # remote Point One device, and pass the data to another application to be
  # parsed and displayed.
  #
  # Note that --output=- sends the data to stdout. All status/display prints
  # will be redirected to stderr.
  ./p1_capture.py tcp://192.168.1.138:30202 \
      --unwrap --wrapped-data-type=EXTERNAL_UNFRAMED_GNSS \
      --output=- | \
      example_rtcm_print_utility
""")

    add_print_format_argument(parser, '--display-format')
    parser.add_argument(
        '-d', '--display', type=str, default='summary',
        choices=('messages', 'messages+summary', 'none', 'status', 'summary'),
        help="""\
Specify the level of detail to be displayed on the console. Output will be printed to stdout, unless configured to write
incoming data to stdout (--output=-).
- messages - Print the content of all incoming FusionEngine messages
- messages+summary - Print the content of all incoming FusionEngine messages, plus a summary on exit
- none - Only print warnings/errors, do not print any contents to the console
- status - Periodically print the amount of data received (byte count, number of messages) but not contents
- summary - Print a table summarizing the incoming data""")
    parser.add_argument(
        '-s', '--summary', action=ExtendedBooleanAction, default=False,
        help="Alias for --display=summary.")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    parser.add_argument(
        'input', type=str,
        help=TRANSPORT_HELP_STRING)

    filter_group = parser.add_argument_group('Message Filtering')
    filter_group.add_argument(
        '-V', '--invert', action=ExtendedBooleanAction, default=False,
        help="""\
If specified, discard all message types specified with --message-type and output everything else.

By default, all specified message types are output and all others are discarded.""")
    filter_group.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="""
An optional list of class names corresponding with the message types to be displayed. May be specified multiple times
(-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). All matches are case-insensitive.

If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple message types.

Note: This applies to the displayed messages only. All incoming data will still be stored on disk if --output is
specified.

Supported types:
%s""" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))

    wrapper_group = parser.add_argument_group('InputDataWrapper Support')
    wrapper_group.add_argument(
        '-u', '--unwrap', action=ExtendedBooleanAction, default=False,
        help="""\
Unwrap incoming InputDataWrapper messages and output their contents without FusionEngine framing. Discard all other
FusionEngine messages.

Note that we strongly recommend using this option with a single --data-type specified. When --data-type is not
specified, or when multiple data types are specified, the unwrapped stream will contain multiple interleaved binary
data streams with no frame alignment enforced.""")
    add_wrapped_data_mode_argument(wrapper_group, '--wrapped-data-format', default='parent')
    wrapper_group.add_argument(
        '--wrapped-data-type', type=str, action='append',
        help="If specified, discard InputDataWrapper messages for data types other than the listed values.")

    file_group = parser.add_argument_group('Output Capture')
    parser.add_argument(
        '--log-timestamp-source', default=None, choices=('user-sw', 'kernel-sw', 'hw'),
        help=f"""\
Create a mapping between the host timestamps and the output file data.
For CSV files, this will change the source of the host_time column.
For p1log or raw logs, the timestamps will be written as a binary file name <OUT_FILE>{TIMESTAMP_FILE_ENDING}.
The data is pairs of uint64. First, the timestamp in nanoseconds followed by the byte offset in the data file.
- user-sw - Log timestamps from python code. This is the only option available for serial data.
- kernel-sw - Log kernel SW timestamps. This is only available for socket connections.
- hw - Log HW timestamps from device driver. This needs HW driver support. Run
  `./fusion_engine_client/utils/socket_timestamping.py` to test.""")
    file_group.add_argument(
        '-o', '--output', metavar='PATH', type=str,
        help=f"""\
If specified, save the incoming data in the specified file, or send it to the
specified transport.

Supported formats include:
{TRANSPORT_HELP_OPTIONS}""")
    file_group.add_argument(
        '-f', '--output-format', default=None, choices=('p1log', 'raw', 'csv'),
        help="""\
The format of the file to be generated when --output is enabled:
- p1log - Create a *.p1log file containing only FusionEngine messages
- raw - Create a generic binary file containing all incoming data (default)
- csv - Create a CSV file with the received message types and timestamps""")

    options = parser.parse_args()

    # Determine what to display.
    if options.summary:
        options.display = 'summary'

    show_summary_live = options.display == 'summary'
    show_summary = options.display in ('summary', 'messages+summary')
    show_status = options.display == 'status'
    show_message_contents = options.display in ('messages', 'messages+summary')
    quiet = options.display == 'none'

    # Configure logging.
    #
    # If the user is sending output to stdout, route all other messages to stderr so the logging prints and the data
    # don't get mixed up. Otherwise, print to stdout.
    if options.output in ('', '-', 'file://-'):
        logging_stream = sys.stderr
    else:
        logging_stream = sys.stdout

    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s',
                            stream=logging_stream)
        if options.verbose == 1:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.DEBUG)
        else:
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(
                logging.getTraceLevel(depth=options.verbose - 1))
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s', stream=logging_stream)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)
    BrokenPipeStreamHandler.install()

    if quiet:
        def _print_info(msg, *args, **kwargs):
            pass
    else:
        def _print_info(msg, *args, **kwargs):
            _logger.info(msg, *args, **kwargs)

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = set()
    if options.unwrap:
        if options.message_type is not None:
            print('Error: You cannot specify both --unwrap and --message-type.')
            sys.exit(1)

        message_types = {MessageType.INPUT_DATA_WRAPPER}
    elif options.message_type is not None:
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

    # For InputDataWrapper messages, if the user specified desired data types, limit the output to only those.
    input_data_types = set()
    if options.wrapped_data_type is not None:
        try:
            input_data_types = InputDataType.find_matching_values(options.wrapped_data_type, prefix='M_TYPE_',
                                                                  print_func=_logger.error)
            if len(input_data_types) == 0:
                # find_matching_values() will print an error.
                sys.exit(1)
            elif options.unwrap and len(input_data_types) > 1:
                _logger.error('You can only unwrap one data type in real time. To extract multiple data streams, '
                              'consider logging all data and then running p1_dump_input.')
                sys.exit(1)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    # If the user requested specific FusionEngine messages, we'll also add InputDataWrapper to that list. That way we
    # can search for wrapped content within those messages.
    wrapped_data_format = options.wrapped_data_format
    include_input_data_wrapper = False
    if (len(message_types) != 0 and MessageType.INPUT_DATA_WRAPPER not in message_types and
        wrapped_data_format != 'parent'):
        include_input_data_wrapper = True
        if wrapped_data_format == 'auto':
            wrapped_data_format = 'content'

    # Connect to the device using the specified transport, or read from a file or log.
    try:
        log_id = None
        input_transport = create_transport(options.input, mode='input', print_func=_print_info)
    except Exception as e:
        _logger.error(str(e))
        sys.exit(1)

    # Open the output file or real-time output transport if enabled.
    output_transport = None
    timestamp_file = None
    if options.output is not None:
        # If writing to a .p1log file, if there's an existing index file (.p1i) for that filename, delete it.
        if options.output_format == 'p1log':
            p1i_path = os.path.splitext(options.output)[0] + '.p1i'
            if os.path.exists(p1i_path):
                os.remove(p1i_path)

        # Now open the transport/file.
        output_transport = create_transport(options.output, mode='output', print_func=_print_info)
        _print_info(f'Writing output to: {output_transport}')

        # If requested when logging to disk, also capture host OS timestamps as messages arrive.
        if options.log_timestamp_source:
            if not isinstance(output_transport, FileTransport) or output_transport.output_path == 'stdout':
                _logger.error('--log-timestamp-source can only be used when --output is a file.')
                sys.exit(1)
            elif options.output_format == 'csv':
                _logger.error('--log-timestamp-source only supported for binary output files.')
                sys.exit(1)
            else:
                timestamp_file = open(options.output + TIMESTAMP_FILE_ENDING, 'wb')

    # Note: We intentionally set --output-format=None by default instead of raw to avoid printing the warning below
    # unnecessarily. If not specified, default to raw (i.e., capture all incoming data).
    generating_raw_log = (output_transport is not None and
                          (options.output_format == 'raw' or options.output_format is None))
    generating_p1log = (output_transport is not None and options.output_format == 'p1log')
    generating_csv = (output_transport is not None and options.output_format == 'csv')

    if generating_csv:
        output_transport.write(b'host_time,type,p1_time,sys_time\n')

    # If the user wants to unwrap InputDataWrapper messages and they set anything other than --output-format=raw, fail.
    #
    # If the user requested --output-format=raw but also set specific message types, warn them that we will only be
    # outputting the requested FusionEngine messages and not any non-FusionEngine binary data in the input stream.
    #
    # There is no requirement to use the .p1log file extension for a stream containing only FusionEngine messages.
    if options.unwrap and output_transport is not None and not generating_raw_log:
        _logger.error("Output format must 'raw' when unwrapping InputDataWrapper content.")
        sys.exit(1)
    if generating_raw_log and options.output_format is not None and len(message_types) != 0:
        _logger.warning('Raw log format requested, but --message-type specified. Output will not contain any '
                        'non-FusionEngine binary, if present in the input stream.')
        generating_raw_log = False
        generating_p1log = True

    # In the read loop below, if we're filtering data and forwarding it in real time, we'll read a small amount of data
    # at a time to reduce latency. Otherwise, if we're just displaying stuff or writing to disk, we'll read more data at
    # a time to be more efficient.
    is_real_time = (output_transport is not None and
                    (not isinstance(output_transport, FileTransport) or output_transport.output_path == 'stdout'))
    if is_real_time:
        read_timeout_sec = 1.0
        read_size_bytes = 64
    else:
        read_timeout_sec = 1.0
        read_size_bytes = 1024

    # If this is a TCP/UDP/UNIX socket, configure it for non-blocking reads. We'll apply a read timeout with select()
    # below.
    if isinstance(input_transport, socket.socket):
        input_transport.setblocking(0)
        # This function won't do anything if neither timestamp is enabled.
        enable_socket_timestamping(
            input_transport,
            enable_sw_timestamp=options.log_timestamp_source == 'kernel-sw',
            enable_hw_timestamp=options.log_timestamp_source == 'hw'
        )
    # If this is a serial port or websocket, configure its read timeout. If this is a file, set_read_timeout() is a
    # no-op.
    else:
        if options.log_timestamp_source and options.log_timestamp_source != 'user-sw':
            _logger.error(f'--log-timestamp-source={options.log_timestamp_source} is not supported. Only "user-sw" '
                          f'timestamps are supported on non-socket captures.')
            sys.exit(1)

        set_read_timeout(input_transport, read_timeout_sec)

    # Create a decoder to parse incoming FusionEngine data.
    decoder = FusionEngineDecoder(warn_on_unrecognized=not quiet and not show_summary_live, return_bytes=True)

    # Setup status variables used below.
    bytes_received = 0
    fe_bytes_received = 0
    messages_received = 0
    bytes_sent = 0
    messages_sent = 0
    device_summary = DeviceSummary()

    first_p1_time_sec = None
    last_p1_time_sec = None

    first_system_time_sec = None
    last_system_time_sec = None

    start_time = datetime.now()
    last_print_time = start_time
    print_timeout_sec = 1.0 if show_summary_live else 5.0

    # Helper function to print out one-line status periodically.
    def _print_status(now):
        nonlocal last_print_time
        _print_info(
            'Status: [elapsed_time=%d sec, received: %d B (%d messages = %d B) -> sent: %d B (%d messages)]' %
            ((now - start_time).total_seconds(),
             bytes_received, messages_received, fe_bytes_received,
             bytes_sent, messages_sent))
        last_print_time = now

    # Helper function to print out a detailed data summary periodically.
    def _print_summary(now):
        nonlocal last_print_time

        if show_summary_live:
            # Clear the terminal.
            print(colorama.ansi.CSI + 'H' + colorama.ansi.CSI + 'J', end='', file=logging_stream)

        # Log/data details.
        if isinstance(input_transport, FileTransport):
            if input_transport.is_stdin:
                _print_info('Input file: <stdin>')
            else:
                _print_info(f'Input file: {input_transport.input_path}')

            if log_id is not None:
                _print_info(f'Log ID: {log_id}')

            if first_p1_time_sec is not None:
                elapsed_sec = last_p1_time_sec - first_p1_time_sec
                if elapsed_sec > 0.0:
                    _print_info(f'Duration (P1): {elapsed_sec:.1f} sec')
                else:
                    _print_info(f'Duration (P1): -')
            else:
                _print_info(f'Duration (P1): -')

            if first_system_time_sec is not None:
                elapsed_sec = last_system_time_sec - first_system_time_sec
                if elapsed_sec > 0.0:
                    _print_info(f'Duration (system): {elapsed_sec:.1f} sec')
                else:
                    _print_info(f'Duration (system): -')
            else:
                _print_info(f'Duration (system): -')

            _print_info("")

        # Real-time processing details.
        _print_info(f'Elapsed time: {(now - start_time).total_seconds():.1f} sec')
        _print_info(f'Received: {bytes_received} B ({messages_received} messages = {fe_bytes_received} B)')
        _print_info(f'Sent: {bytes_sent} B ({messages_sent} messages)')

        # Message summary table.
        _print_info("")
        print_summary_table(device_summary)

        last_print_time = now

    if show_status:
        _print_display_func = _print_status
    elif show_summary:
        _print_display_func = _print_summary
    else:
        _print_display_func = lambda now: None

    # Listen for incoming data.
    try:
        while True:
            # Read some data from the device/file.
            kernel_ts: Optional[float] = None
            hw_ts: Optional[float] = None
            try:
                # If this is a TCP/UDP socket, use select() to implement a read timeout so we can wakeup periodically
                # and print status if there's no incoming data.
                if isinstance(input_transport, socket.socket):
                    ready = select.select([input_transport], [], [], read_timeout_sec)
                    if ready[0]:
                        received_data, kernel_ts, hw_ts = recv(input_transport, read_size_bytes)
                    else:
                        received_data = []
                # If this is a serial port or file, we set the read timeout above.
                else:
                    received_data = recv_from_transport(input_transport, read_size_bytes)

                    # Check if we reached EOF.
                    if len(received_data) == 0 and isinstance(input_transport, FileTransport):
                        break

                now = datetime.now()

                bytes_received += len(received_data)

                if show_summary_live or show_status:
                    if (now - last_print_time).total_seconds() > print_timeout_sec:
                        _print_display_func(now)
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
                output_transport.write(received_data)
                bytes_sent += len(received_data)
                if timestamp_file:
                    log_timestamped_data_offset(timestamp_file, timestamp_ns, bytes_received)


            # Decode the incoming data and print the contents of any complete messages.
            #
            # Note that we pass the data to the decoder at all times, even if --display=false, --summary=false, and
            # --quiet=true were set, so that:
            # - So that we get a count of the number of incoming and outgoing messages
            # - So we print warnings if the CRC fails on any of the incoming data
            # - If we are logging in *.p1log format, so the decoder can separate the FusionEngine data from any
            #   non-FusionEngine data in the stream
            messages = decoder.on_data(received_data)

            # Count _all_ incoming FusionEngine messages. We apply the user-specified message_types filter below to the
            # outgoing message count.
            messages_received += len(messages)

            for (header, message, raw_data) in messages:
                fe_bytes_received += len(raw_data)

                # Capture elapsed P1 and (device) system time.
                p1_time = message.get_p1_time()
                if p1_time is not None:
                    if first_p1_time_sec is None:
                        first_p1_time_sec = float(p1_time)
                    last_p1_time_sec = float(p1_time)

                system_time = message.get_system_time_sec()
                if system_time is not None:
                    if first_system_time_sec is None:
                        first_system_time_sec = float(system_time)
                    last_system_time_sec = float(system_time)

                # See if this is in the list of user-specified message types to keep. If the list is empty, keep all
                # messages.
                #
                # In unwrap mode, we explicitly set message_types to InputDataWrapper messages and ignore all other
                # incoming messages.
                #
                # When not in unwrap mode, the user may or may not have requested InputDataWrapper. However, if the they
                # set --wrapped-data-format=auto|all|content, we will pass wrappers through here and filter them out
                # below.
                pass_through_message = (
                    len(message_types) == 0 or
                    (options.invert and header.message_type not in message_types) or
                    (not options.invert and header.message_type in message_types) or
                    header.message_type == MessageType.INPUT_DATA_WRAPPER and include_input_data_wrapper
                )

                # If this is an InputDataWrapper and the user specified a list of data types to keep, keep only the
                # messages with that kind of data. If the list is empty, keep all messages.
                if pass_through_message and header.message_type == MessageType.INPUT_DATA_WRAPPER:
                    pass_through_message = (
                        len(input_data_types) == 0 or
                        (options.invert and message.data_type not in input_data_types) or
                        (not options.invert and message.data_type in input_data_types)
                    )

                if not pass_through_message:
                    continue

                device_summary.update(header, message)
                messages_sent += 1
                if not generating_raw_log:
                    bytes_sent += len(raw_data)

                if generating_p1log:
                    output_transport.write(raw_data)
                    if timestamp_file:
                        log_timestamped_data_offset(timestamp_file, timestamp_ns, fe_bytes_received)

                if generating_csv:
                    p1_time = message.get_p1_time()
                    sys_time = message.get_system_time_sec()
                    p1_str = str(p1_time.seconds) if p1_time is not None and not math.isnan(p1_time) else ''
                    sys_str = str(sys_time) if sys_time is not None and not math.isnan(sys_time) else ''
                    output_transport.write(
                        f'{timestamp_sec},{header.message_type},{p1_str},{sys_str}\n'.encode('utf-8'))

                if show_message_contents:
                    print_message(header, message, format=options.display_format, bytes=raw_data,
                                  message_types=message_types, wrapped_data_mode=wrapped_data_format,
                                  logger=_logger)

            if show_summary_live:
                if (now - last_print_time).total_seconds() > 0.5:
                    _print_display_func(now)
    except (BrokenPipeError, KeyboardInterrupt) as e:
        pass

    # Close the transport.
    input_transport.close()

    # Close the output file.
    if output_transport is not None:
        output_transport.close()

    if show_summary:
        now = datetime.now()
        _print_display_func(now)


if __name__ == "__main__":
    main()
