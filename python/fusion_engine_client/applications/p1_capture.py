#!/usr/bin/env python3

from datetime import datetime
import math
import os
import select
import sys
import time
from typing import Optional, Union

import colorama

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

from ..messages import InputDataType, MessageHeader, MessagePayload, MessageType, message_type_by_name
from ..parsers import FusionEngineDecoder, MixedLogReader
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, CSVAction, ExtendedBooleanAction
from ..utils.log import define_cli_arguments as define_log_search_arguments, is_possible_log_pattern, locate_log
from ..utils.print_utils import \
    DeviceSummary, add_print_format_argument, add_wrapped_data_mode_argument, print_message, print_summary_table
from ..utils.socket_timestamping import (enable_socket_timestamping,
                                         HW_TIMESTAMPING_HELP,
                                         log_timestamped_data_offset,
                                         recv,
                                         TIMESTAMP_FILE_ENDING,)
from ..utils.transport_utils import *
from ..utils.time_range import TimeRange
from ..utils.trace import HighlightFormatter, BrokenPipeStreamHandler

_logger = logging.getLogger('point_one.fusion_engine.applications.p1_capture')


class Application:
    def __init__(self, options, logging_stream=None):
        self.options = options
        self.logging_stream = logging_stream

        # Determine what to display.
        self.show_summary_live = self.options.display == 'summary'
        self.show_summary = self.options.display in ('summary', 'messages+summary')
        self.show_status = self.options.display == 'status'
        self.show_message_contents = self.options.display in ('messages', 'messages+summary')
        self.quiet = self.options.display == 'none'

        # Message filtering.
        self.message_types = set()
        self.input_data_types = set()
        self.wrapped_data_format = self.options.wrapped_data_format
        self.include_input_data_wrapper = False
        self.source_ids = set()
        self.time_range = None

        # Input.
        self.input_transport = None
        self.log_id = None
        self.log_reader = None

        self.read_timeout_sec = None
        self.read_size_bytes = None

        # Output.
        self.output_transport = None
        self.timestamp_file = None
        self.generating_raw_log = False
        self.generating_p1log = False
        self.generating_csv = False

        # Status/incoming data summary.
        self.bytes_received = 0
        self.fe_bytes_received = 0
        self.messages_received = 0
        self.skipped_messages = 0
        self.bytes_sent = 0
        self.messages_sent = 0
        self.device_summary = DeviceSummary()

        self.first_p1_time_sec = None
        self.last_p1_time_sec = None

        self.first_system_time_sec = None
        self.last_system_time_sec = None

        self.start_time = None
        self.last_print_time = None
        self.print_timeout_sec = 1.0 if self.show_summary_live else 5.0

        # Configure everything.
        self._init_message_type_filter()
        self._init_input_data_type_filter()
        self._init_source_id_filter()
        self._init_time_range_filter()
        self._configure_input()
        self._configure_output()
        self._set_read_timeout()

        # If we're reading from a file (and not stdin), just display the summary at the end and don't clear the
        # terminal.
        if isinstance(self.input_transport, FileTransport) and not self.input_transport.is_stdin:
            self.show_summary_live = False

        # Create the FusionEngine decoder after configuring, in case we need to change show_summary_live, etc.
        self.decoder = FusionEngineDecoder(warn_on_unrecognized=not self.quiet and not self.show_summary_live,
                                           return_bytes=True, return_offset=True)

    def _init_message_type_filter(self):
        # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to
        # only those message types.
        if self.options.unwrap:
            if self.options.message_type is not None:
                _logger.error('Error: You cannot specify both --unwrap and --message-type.')
                sys.exit(1)

            self.message_types = {MessageType.INPUT_DATA_WRAPPER}
        elif self.options.message_type is not None:
            # Pattern match to any of:
            #   -m Type1
            #   -m Type1 -m Type2
            #   -m Type1,Type2
            #   -m Type1,Type2 -m Type3
            #   -m Type*
            try:
                self.message_types = MessagePayload.find_matching_message_types(self.options.message_type)
                if len(self.message_types) == 0:
                    # find_matching_message_types() will print an error.
                    sys.exit(1)
            except ValueError as e:
                _logger.error(str(e))
                sys.exit(1)

        # If the user requested specific FusionEngine messages, we'll also add InputDataWrapper to that list. That way
        # we can search for wrapped content within those messages.
        if (len(self.message_types) != 0 and MessageType.INPUT_DATA_WRAPPER not in self.message_types and
            self.wrapped_data_format != 'parent'):
            self.include_input_data_wrapper = True
            if self.wrapped_data_format == 'auto':
                self.wrapped_data_format = 'content'

    def _init_input_data_type_filter(self):
        # For InputDataWrapper messages, if the user specified desired data types, limit the output to only those.
        if self.options.wrapped_data_type is not None:
            try:
                self.input_data_types = InputDataType.find_matching_values(self.options.wrapped_data_type, prefix='M_TYPE_',
                                                                      print_func=_logger.error)
                if len(self.input_data_types) == 0:
                    # find_matching_values() will print an error.
                    sys.exit(1)
                elif self.options.unwrap and len(self.input_data_types) > 1:
                    _logger.error('You can only unwrap one data type in real time. To extract multiple data streams, '
                                  'consider logging all data and then running p1_dump_input.')
                    sys.exit(1)
            except ValueError as e:
                _logger.error(str(e))
                sys.exit(1)

    def _init_source_id_filter(self):
        # If the user specified a set of source IDs, limit messages to only those sources.
        if self.options.source_identifier is not None:
            try:
                self.source_ids = set([int(s) for s in self.options.source_identifier])
            except ValueError:
                _logger.error('Source identifiers must be integers.')
                sys.exit(1)

    def _init_time_range_filter(self):
        try:
            self.time_range = TimeRange.parse(self.options.time)
        except ValueError as e:
            _logger.error(str(e))
            sys.exit(1)

    def _configure_input(self):
        # Connect to the device using the specified transport, or read from a file or log.
        try:
            # If the user specified a partial or complete log hash, or the path to a directory, try to locate a P1 log.
            # Log patterns are mutually exclusive with transport descriptors, so it can only be one or the other. No
            # need to check both.
            if is_possible_log_pattern(self.options.input):
                input_path, self.log_id = locate_log(
                    input_path=self.options.input, log_base_dir=self.options.log_base_dir,
                    return_log_id=True, extract_fusion_engine_data=False)
                if input_path is None:
                    # locate_log() will log an error.
                    sys.exit(1)
                else:
                    self.input_transport = create_transport(input_path, mode='input', print_func=self._print)
                    self._print("")
            else:
                self.input_transport = create_transport(self.options.input, mode='input', print_func=self._print)
                self._print("")

            # If we're reading from a normal file on disk, use MixedLogReader instead of reading directly. That is more
            # efficient since it will index the file for faster reads.
            if isinstance(self.input_transport, FileTransport) and not self.input_transport.is_stdin:
                message_types_plus_wrapper = set(self.message_types)
                invert = self.options.invert
                if self.include_input_data_wrapper and MessageType.INPUT_DATA_WRAPPER not in self.message_types:
                    # If the user specifies message types that they want to _exclude_, but we also need to _include_
                    # InputDataWrapper, MixedLogReader can't do both. We'll have it pass all messages and handle the
                    # filtering later.
                    if invert:
                        message_types_plus_wrapper = None
                        invert = False
                    else:
                        message_types_plus_wrapper.add(MessageType.INPUT_DATA_WRAPPER)

                self.input_transport.input.close()
                self.log_reader = MixedLogReader(
                    self.input_transport.input_path, ignore_index=self.options.ignore_index,
                    return_bytes=True, return_offset=True, show_progress=self.options.progress,
                    message_types=message_types_plus_wrapper, invert_message_types=invert,
                    time_range=self.time_range, source_ids=self.source_ids)

                # MixedLogReader will apply the time range, message type, and source ID filters, so we will clear them
                # here so they are not applied twice by _apply_filters().
                self.time_range = None
                if message_types_plus_wrapper is not None:
                    self.message_types = set()
                self.source_ids = set()
        except Exception as e:
            _logger.error(str(e))
            sys.exit(1)

    def _configure_output(self):
        # Open the output file or real-time output transport if enabled.
        if self.options.output is not None:
            # If writing to a .p1log file, if there's an existing index file (.p1i) for that filename, delete it.
            if self.options.output_format == 'p1log':
                p1i_path = os.path.splitext(self.options.output)[0] + '.p1i'
                if os.path.exists(p1i_path):
                    os.remove(p1i_path)

            # Now open the transport/file.
            self.output_transport = create_transport(self.options.output, mode='output', print_func=self._print)

            # If requested when logging to disk, also capture host OS timestamps as messages arrive.
            if self.options.log_timestamp_source:
                if not isinstance(self.output_transport, FileTransport) or self.output_transport.is_stdout:
                    _logger.error('--log-timestamp-source can only be used when --output is a file.')
                    sys.exit(1)
                elif self.options.output_format == 'csv':
                    _logger.error('--log-timestamp-source only supported for binary output files.')
                    sys.exit(1)
                else:
                    self.timestamp_file = open(self.options.output + TIMESTAMP_FILE_ENDING, 'wb')

        # Note: We intentionally set --output-format=None by default instead of raw to avoid printing the warning below
        # unnecessarily. If not specified, default to raw (i.e., capture all incoming data).
        self.generating_raw_log = (self.output_transport is not None and
                                   (self.options.output_format == 'raw' or self.options.output_format is None))
        self.generating_p1log = (self.output_transport is not None and self.options.output_format == 'p1log')
        self.generating_csv = (self.output_transport is not None and self.options.output_format == 'csv')

        if self.generating_csv:
            self.output_transport.write(b'host_time,type,p1_time,sys_time\n')

        # If the user wants to unwrap InputDataWrapper messages and they set anything other than --output-format=raw,
        # fail.
        #
        # If the user requested --output-format=raw but also set specific message types, warn them that we will only be
        # outputting the requested FusionEngine messages and not any non-FusionEngine binary data in the input stream.
        #
        # There is no requirement to use the .p1log file extension for a stream containing only FusionEngine messages.
        if self.options.unwrap:
            if self.output_transport is None:
                _logger.error("You must specify an output file or transport when using --unwrap.")
                sys.exit(1)
            elif not self.generating_raw_log:
                _logger.error("Output format must 'raw' when unwrapping InputDataWrapper content.")
                sys.exit(1)

        if self.generating_raw_log and self.options.output_format is not None and len(self.message_types) != 0:
            _logger.warning('Raw log format requested, but --message-type specified. Output will not contain any '
                            'non-FusionEngine binary, if present in the input stream.')
            self.generating_raw_log = False
            self.generating_p1log = True

    def _set_read_timeout(self):
        # In the read loop, if we're filtering data and forwarding it in real time, we'll read a small amount of data at
        # a time to reduce latency. Otherwise, if we're just displaying stuff or writing to disk, we'll read more data
        # at a time to be more efficient.
        is_real_time = (self.output_transport is not None and
                        (not isinstance(self.output_transport, FileTransport) or self.output_transport.is_stdout))
        if is_real_time:
            self.read_timeout_sec = 1.0
            self.read_size_bytes = 64
        else:
            self.read_timeout_sec = 1.0
            self.read_size_bytes = 1024

        # If this is a TCP/UDP/UNIX socket, configure it for non-blocking reads. We'll apply a read timeout with
        # select() in the read loop.
        if isinstance(self.input_transport, socket.socket):
            self.input_transport.setblocking(0)
            # This function won't do anything if neither timestamp is enabled.
            enable_socket_timestamping(
                self.input_transport,
                enable_sw_timestamp=self.options.log_timestamp_source == 'kernel-sw',
                enable_hw_timestamp=self.options.log_timestamp_source == 'hw'
            )
        # If this is a serial port or websocket, configure its read timeout. If this is a file, set_read_timeout() is a
        # no-op.
        else:
            if self.options.log_timestamp_source and self.options.log_timestamp_source != 'user-sw':
                _logger.error(
                    f'--log-timestamp-source={self.options.log_timestamp_source} is not supported. Only "user-sw" '
                    f'timestamps are supported on non-socket captures.')
                sys.exit(1)

            set_read_timeout(self.input_transport, self.read_timeout_sec)

    def process_input(self):
        self.start_time = datetime.now()
        self.last_print_time = self.start_time

        # Listen for incoming data.
        try:
            while True:
                # If using a MixedLogReader, read one message from the log.
                if self.log_reader:
                    try:
                        next_message = next(self.log_reader)
                        received_data = next_message[2]
                        messages = [next_message]
                        now = datetime.now()
                        timestamp_sec = now.timestamp()
                    except StopIteration:
                        break
                # Otherwise, read some data from the transport/file.
                else:
                    kernel_ts: Optional[float] = None
                    hw_ts: Optional[float] = None
                    try:
                        # If this is a TCP/UDP socket, use select() to implement a read timeout so we can wake up
                        # periodically and print status if there's no incoming data.
                        if isinstance(self.input_transport, socket.socket):
                            ready = select.select([self.input_transport], [], [], self.read_timeout_sec)
                            if ready[0]:
                                received_data, kernel_ts, hw_ts = recv(self.input_transport, self.read_size_bytes)
                            else:
                                received_data = []
                        # If this is a serial port or file, we set the read timeout above.
                        else:
                            received_data = recv_from_transport(self.input_transport, self.read_size_bytes)

                            # Check if we reached EOF.
                            if len(received_data) == 0 and isinstance(self.input_transport, FileTransport):
                                break

                        now = datetime.now()

                        self.bytes_received += len(received_data)

                        if self.show_summary_live or self.show_status:
                            if (now - self.last_print_time).total_seconds() > self.print_timeout_sec:
                                self._print_display(now)
                    except serial.SerialException as e:
                        _logger.error('Unexpected error reading from device:\r%s' % str(e))
                        break

                    if self.options.log_timestamp_source == 'kernel-sw':
                        if kernel_ts is None:
                            _logger.error(f'Unable to capture kernel SW timestamps on {self.options.transport}.')
                            sys.exit(1)
                        timestamp_sec = kernel_ts
                    elif self.options.log_timestamp_source == 'hw':
                        if hw_ts is None:
                            _logger.error(
                                f'Unable to capture HW timestamps on {self.options.transport}.\n{HW_TIMESTAMPING_HELP}')
                            sys.exit(1)
                        timestamp_sec = hw_ts
                    else:
                        timestamp_sec = now.timestamp()

                # If logging in raw format, write the data to disk as is.
                if self.generating_raw_log:
                    self.output_transport.write(received_data)
                    self.bytes_sent += len(received_data)
                    if self.timestamp_file:
                        timestamp_ns = int(round(timestamp_sec * 1e9))
                        log_timestamped_data_offset(self.timestamp_file, timestamp_ns, self.bytes_received)

                # Decode the incoming data and print the contents of any complete messages.
                #
                # Note that we pass the data to the decoder at all times, even if --display=false, --summary=false, and
                # --quiet=true were set, so that:
                # - So that we get a count of the number of incoming and outgoing messages
                # - So we print warnings if the CRC fails on any of the incoming data
                # - If we are logging in *.p1log format, so the decoder can separate the FusionEngine data from any
                #   non-FusionEngine data in the stream
                if not self.log_reader:
                    messages = self.decoder.on_data(received_data)

                # Now process the message.
                finished = not self._process_fe_messages(messages, timestamp_sec)

                if self.show_summary_live:
                    if (now - self.last_print_time).total_seconds() > 0.5:
                        self._print_display(now)

                if finished:
                    break
        except (BrokenPipeError, KeyboardInterrupt) as e:
            pass

        # Close the transport.
        self.input_transport.close()

        # Close the output file.
        if self.output_transport is not None:
            self.output_transport.close()

        # Update the summary one last time if enabled.
        if self.show_summary:
            now = datetime.now()
            self._print_display(now)

    def _process_fe_messages(self, messages, timestamp_sec):
        for (header, message, raw_data, offset_bytes) in messages:
            # Count _all_ incoming FusionEngine messages. We apply the user-specified message_types filter below to the
            # outgoing message count.
            self.messages_received += 1
            self.fe_bytes_received += len(raw_data)

            # Capture elapsed P1 and (device) system time.
            if isinstance(message, MessagePayload):
                p1_time = message.get_p1_time()
                if p1_time is not None:
                    if self.first_p1_time_sec is None:
                        self.first_p1_time_sec = float(p1_time)
                    self.last_p1_time_sec = float(p1_time)

                system_time = message.get_system_time_sec()
                if system_time is not None:
                    if self.first_system_time_sec is None:
                        self.first_system_time_sec = float(system_time)
                    self.last_system_time_sec = float(system_time)
            else:
                p1_time = None
                system_time = None

            if self._apply_filters(header=header, message=message):
                # If requested, skip the first N messages that pass the filter (e.g., skip the first 10 pose messages).
                if self.skipped_messages < self.options.skip:
                    self.skipped_messages += 1
                    continue

                self.device_summary.update(header, message)
                self.messages_sent += 1
                if not self.generating_raw_log:
                    self.bytes_sent += len(raw_data)

                if self.generating_p1log:
                    self.output_transport.write(raw_data)
                    if self.timestamp_file:
                        timestamp_ns = int(round(timestamp_sec * 1e9))
                        log_timestamped_data_offset(self.timestamp_file, timestamp_ns, self.fe_bytes_received)

                if self.generating_csv:
                    p1_str = str(p1_time.seconds) if p1_time is not None and not math.isnan(p1_time) else ''
                    sys_str = str(system_time) if system_time is not None and not math.isnan(system_time) else ''
                    self.output_transport.write(
                        f'{timestamp_sec},{header.message_type},{p1_str},{sys_str}\n'.encode('utf-8'))

                if self.show_message_contents:
                    print_message(header=header, contents=message, offset_bytes=offset_bytes, bytes=raw_data,
                                  format=self.options.display_format,
                                  message_types=self.message_types, wrapped_data_mode=self.wrapped_data_format,
                                  logger=_logger)

                if self.options.max is not None and self.messages_sent == self.options.max:
                    return False

            if self.time_range is not None and self.time_range.in_range_ended():
                return False

        return True

    def _apply_filters(self, header: MessageHeader, message: Union[MessagePayload, bytes]):
        # Check if this message is in the specified time range or if we're reached the end of the time range and should
        # stop processing.
        if self.time_range is not None and isinstance(message, MessagePayload):
            if not self.time_range.is_in_range(message):
                return False

        # See if this is in the list of user-specified message types to keep. If the list is empty, keep all messages.
        #
        # In unwrap mode, we explicitly set message_types to InputDataWrapper messages and ignore all other incoming
        # messages.
        #
        # When not in unwrap mode, the user may or may not have requested InputDataWrapper. However, if they set
        # --wrapped-data-format=auto|all|content, we will pass wrappers through here and filter them out below.
        if len(self.message_types) > 0:
            if header.message_type == MessageType.INPUT_DATA_WRAPPER and self.include_input_data_wrapper:
                pass
            elif not self.options.invert and header.message_type not in self.message_types:
                return False
            elif self.options.invert and header.message_type in self.message_types:
                return False

        # If this is an InputDataWrapper and the user specified a list of data types to keep, keep only the messages
        # with that kind of data. If the list is empty, keep all messages.
        if header.message_type == MessageType.INPUT_DATA_WRAPPER and len(self.input_data_types) > 0:
            if not self.options.invert and message.data_type not in self.input_data_types:
                return False
            elif self.options.invert and message.data_type in self.input_data_types:
                return False

        # If the user listed specific sources IDs, restrict to that.
        if len(self.source_ids) > 0:
            if header.source_identifier not in self.source_ids:
                return False

        return True

    def _print_display(self, now):
        if self.show_status:
            self._print_status(now)
        elif self.show_summary:
            self._print_summary(now)
        self.last_print_time = now

    def _print_status(self, now):
        self._print(
            'Status: [elapsed_time=%d sec, received: %d B (%d messages = %d B) -> sent: %d B (%d messages)]' %
            ((now - self.start_time).total_seconds(),
             self.bytes_received, self.messages_received, self.fe_bytes_received,
             self.bytes_sent, self.messages_sent))

    def _print_summary(self, now):
        if self.show_summary_live:
            # Clear the terminal.
            print(colorama.ansi.CSI + 'H' + colorama.ansi.CSI + 'J', end='', file=self.logging_stream)

        # Log/data details.
        if isinstance(self.input_transport, FileTransport):
            if self.input_transport.is_stdin:
                self._print('Input file: <stdin>')
            else:
                self._print(f'Input file: {self.input_transport.input_path}')

            if self.log_id is not None:
                self._print(f'Log ID: {self.log_id}')

            if self.first_p1_time_sec is not None:
                elapsed_sec = self.last_p1_time_sec - self.first_p1_time_sec
                self._print(f'P1 time: {self.first_p1_time_sec} -> {self.last_p1_time_sec} ({elapsed_sec:.1f} sec)')
            else:
                self._print(f'P1 time: -')

            if self.first_system_time_sec is not None:
                elapsed_sec = self.last_system_time_sec - self.first_system_time_sec
                self._print(f'System time: {self.first_system_time_sec} -> {self.last_system_time_sec} '
                            f'({elapsed_sec:.1f} sec)')
            else:
                self._print(f'System time: -')

            self._print("")

        # Real-time processing details.
        self._print(f'Elapsed time: {(now - self.start_time).total_seconds():.1f} sec')
        self._print(f'Received: {self.bytes_received} B ({self.messages_received} messages = '
                    f'{self.fe_bytes_received} B)')
        self._print(f'Sent: {self.bytes_sent} B ({self.messages_sent} messages)')

        # Message summary table.
        self._print("")
        print_summary_table(self.device_summary)

    def _print(self, msg, *args, **kwargs):
        if self.quiet:
            pass
        else:
            _logger.info(msg, *args, **kwargs)


def main(default_display_mode: str = 'summary', default_output: str = None):
    # Parse command-line arguments.
    parser = ArgumentParser(description="""\
Connect to a Point One device in real time over TCP, UDP, UNIX socket, etc.,
or read logged data from a file for post-processing, then filter/display the
incoming FusionEngine messages. The data may also be logged to disk or sent to
another application, either over stdout or a specified transport.

Examples:
  # Connect to a device over TCP and display a summary of the incoming data.
  #
  # --display=summary is the default setting.
  ./p1_capture.py tcp://192.168.1.138:30202
    or
  ./p1_capture.py tcp://192.168.1.138:30202 --display=summary
    or
  ./p1_capture.py tcp://192.168.1.138:30202 --summary

  # Connect to a device over a serial port.
  ./p1_capture.py tty:///dev/ttyUSB0:460800

  # Display the contents of all messages received from a device in real time,
  # instead of summarizing.
  ./p1_capture.py tcp://192.168.1.138:30202 --display=messages

  # Log output from a device to disk.
  ./p1_capture.py tcp://192.168.1.138:30202 --output=my_log.p1log

  # Display a data capture status instead of the larger summary table.
  ./p1_capture.py tcp://192.168.1.138:30202 --output=my_log.p1log --display=status

  # Display the contents of all Pose messages captured in a log file.
  ./p1_capture.py my_log.p1log --message-type=Pose --display=messages

  # Filter a recorded log file and only keep the Pose messages.
  ./p1_capture.py my_log.p1log --message-type=Pose --output=pose_output.p1log

  # Print the contents of the first 10 Pose messages in a recorded data file.
  ./p1_capture.py my_log.p1log --message-type=Pose --max=10 \
      --display=messages

  # Print the contents of the 10 Pose messages in a recorded data file,
  # starting with the 45th Pose message.
  ./p1_capture.py my_log.p1log --message-type=Pose --skip=44 --max=10 \
      --display=messages

  # Filter the incoming data from a device connected over TCP and remove
  # GNSSSignals messages. Log the remaining FusionEngine messages to disk.
  ./p1_capture.py tcp://192.168.1.138:30202 \
      --output=my_log_no_gnss_signals.p1log \
      --invert --message-type=GNSSSignals

  # Same as above, but capture data from stdin using netcat.
  netcat 192.168.1.138 30202 | \
      ./p1_capture.py \
      --output=my_log_no_gnss_signals.p1log \
      --invert --message-type=GNSSSignals

  # Similar to above, but open a serial port manually using stty and cat.
  stty -F /dev/ttyUSB0 speed 460800 cs8 \
      -cstopb -parenb -icrnl -ixon -ixoff -opost -isig -icanon -echo && \
      cat /dev/ttyUSB0 | \
      ./p1_capture.py \
      --output=my_log_no_gnss_signals.p1log \
      --invert --message-type=GNSSSignals

  # Extract GNSS receiver data in its native format (RTCM, SBF, etc.) from a
  # remote device, and pass the data to another application to be parsed and
  # displayed.
  #
  # Note that --output=- sends the data to stdout. All status/display prints
  # will be redirected to stderr, or in this case, disabled using
  # --display=quiet.
  ./p1_capture.py tcp://192.168.1.138:30202 \
      --unwrap --wrapped-data-type=EXTERNAL_UNFRAMED_GNSS \
      --output=- --display=quiet | \
      example_rtcm_print_utility
""")

    add_print_format_argument(parser, '--display-format')
    parser.add_argument(
        '-d', '--display', type=str, default=default_display_mode,
        choices=('messages', 'messages+summary', 'none', 'quiet', 'status', 'summary'),
        help="""\
Specify the level of detail to be displayed on the console. Output will be printed to stdout, unless configured to write
incoming data to stdout (--output=-).
- messages - Print the content of all incoming FusionEngine messages
- messages+summary - Print the content of all incoming FusionEngine messages, plus a summary on exit
- none - Only print warnings/errors, do not print any contents to the console
- quiet - Alias for 'none'
- status - Periodically print the amount of data received (byte count, number of messages) but not contents
- summary - Print a table summarizing the incoming data""")
    parser.add_argument(
        '-s', '--summary', action=ExtendedBooleanAction, default=False,
        help="Alias for --display=summary.")
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Print verbose/trace debugging messages.")

    input_parser = parser.add_argument_group('Input Control')
    define_log_search_arguments(input_parser, define_log=False)
    input_parser.add_argument(
        '--progress', action=ExtendedBooleanAction,
        help="If input is a file, print file read progress to the console periodically.")
    input_parser.add_argument(
        'input', type=str, nargs='?', default='-',
        help=f"""\
{TRANSPORT_HELP_STRING}
- The path to a FusionEngine log directory
- A pattern matching a FusionEngine log directory under the specified base directory (see find_fusion_engine_log() and
  --log-base-dir)
""")

    filter_group = parser.add_argument_group('Message Filtering')
    filter_group.add_argument(
        '-V', '--invert', action=ExtendedBooleanAction, default=False,
        help="""\
If specified, discard all message types specified with --message-type and output everything else.

By default, all specified message types are output and all others are discarded.""")
    filter_group.add_argument(
        '-n', '--max', type=int, default=None,
        help="Process up to a maximum of N messages. If --message-type is specified, only count messages matching the "
             "specified type(s).")
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
    filter_group.add_argument(
        '--skip', type=int, default=0,
        help="Skip the first N messages. If --message-type is specified, only count messages matching the specified "
             "type(s).")
    filter_group.add_argument(
        '--source-identifier', '--source-id', action=CSVAction, nargs='*',
        help="Only include messages with the listed source identifier(s). Must be integers. May be specified multiple "
             "times (--source-id 0 --source-id 1), as a space-separated list (--source-id 0 1), or as a "
             "comma-separated list (--source-id 0,1). If not specified, all available source identifiers present in "
             "the data will be used.")
    filter_group.add_argument(
        '-t', '--time', type=str, metavar='[START][:END][:{rel,abs}]',
        help="Only process messages in the specified time range. Both start and end may be omitted to read from the "
             "beginning or to the end of the file. By default, timestamps are treated as relative to the first message "
             "in the file, unless an 'abs' type is specified.")

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
        '-o', '--output', metavar='PATH', type=str, default=default_output,
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

    # --summary is an alias for --display=summary.
    if options.summary:
        options.display = 'summary'

    if options.display == 'quiet':
        options.display = 'none'

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
        if quiet:
            logging.getLogger('point_one.utils.log').setLevel(logging.ERROR)
            logging.getLogger('point_one.fusion_engine.parsers').setLevel(logging.ERROR)

    HighlightFormatter.install(color=True, standoff_level=logging.WARNING)
    BrokenPipeStreamHandler.install()

    # Configure the application.
    app = Application(options=options, logging_stream=logging_stream)
    app.process_input()


if __name__ == "__main__":
    main()
