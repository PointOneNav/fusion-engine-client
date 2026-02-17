#!/usr/bin/env python3

from datetime import datetime
import os
import sys
import time

# Since stdout is used for data stream, don't write any print statements to stdout.
# Done here to avoid any log/print statements triggered by imports.
original_stdout = sys.stdout
sys.stdout = sys.stderr

# Add the Python root directory (fusion-engine-client/python/) to the import search path to enable FusionEngine imports
# if this application is being run directly out of the repository and is not installed as a pip package.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from fusion_engine_client.messages import InputDataType, MessagePayload, MessageType, message_type_by_name
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.argument_parser import ArgumentParser, ExtendedBooleanAction
from fusion_engine_client.utils.transport_utils import *


def main():
    parser = ArgumentParser(description="""\
Filter FusionEngine data coming from a device, or via stdin, and send the
filtered result to stdout.

Examples:
  # Remove GNSSSatellite from the data stream of a device connected over TCP.
  ./p1_filter.py tcp://192.168.1.138:30202 \
      --invert -m GNSSSatellite --display > /tmp/out.p1log

  # Same as above, but capture data using netcat.
  netcat 192.168.1.138 30202 | \
      ./p1_filter.py --invert -m GNSSSatellite --display > /tmp/out.p1log

  # Only keep Pose messages from a recorded data file.
  cat /tmp/out.p1log | ./p1_filter.py -m Pose > /tmp/pose_out.p1log

  # Only keep Pose messages from an incoming serial data stream.
  ./p1_filter.py tty:///dev/ttyUSB0:460800 \
      -m Pose > /tmp/pose_out.p1log

  # Similar to above, but open the serial port manually using stty and cat.
  stty -F /dev/ttyUSB0 speed 460800 cs8 \
      -cstopb -parenb -icrnl -ixon -ixoff -opost -isig -icanon -echo && \
      cat /dev/ttyUSB0 | \
      ./p1_filter.py -m Pose > /tmp/pose_out.p1log

  # Extract GNSS receiver data in its native format (RTCM, SBF, etc.) from a
  # remote Point One device, and pass the data to another application to be
  # parsed and displayed.
  ./p1_filter.py tcp://192.168.1.138:30202 \
      --unwrap --data-type EXTERNAL_UNFRAMED_GNSS | \
      rtcm_print
""")

    parser.add_argument(
        '-V', '--invert', action=ExtendedBooleanAction, default=False,
        help="""\
If specified, discard all message types specified with --message-type and output everything else.

By default, all specified message types are output and all others are discarded.""")
    parser.add_argument(
        '--display', action=ExtendedBooleanAction, default=False,
        help="Periodically print status on stderr.")
    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An list of class names corresponding with the message types to forward or discard (see --invert).\n"
             "\n"
             "May be specified multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). "
             "All matches are case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
    parser.add_argument(
        '-o', '--output', metavar='PATH', type=str,
        help=f"""\
If specified, write output to the specified file. Otherwise, output is sent to
stdout by default.

Supported formats include:
{TRANSPORT_HELP_OPTIONS}""")

    wrapper_group = parser.add_argument_group('InputDataWrapper Support')
    wrapper_group.add_argument(
        '-d', '--data-type', type=str, action='append',
        help="If specified, discard InputDataWrapper messages for data types other than the listed values.")
    wrapper_group.add_argument(
        '-u', '--unwrap', action=ExtendedBooleanAction, default=False,
        help="""\
Unwrap incoming InputDataWrapper messages and output their contents without FusionEngine framing. Discard all other
FusionEngine messages.

Note that we strongly recommend using this option with a single --data-type specified. When --data-type is not
specified, or when multiple data types are specified, the unwrapped stream will contain multiple interleaved binary
data streams with no frame alignment enforced.""")

    parser.add_argument(
        'input', metavar='PATH', type=str, nargs='?', default='-',
        help=TRANSPORT_HELP_STRING)
    options = parser.parse_args()

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
            print(str(e))
            sys.exit(1)

    # For InputDataWrapper messages, if the user specified desired data types, limit the output to only those.
    input_data_types = set()
    if options.data_type is not None:
        try:
            input_data_types = InputDataType.find_matching_values(options.data_type, prefix='M_TYPE_', print_func=print)
            if len(input_data_types) == 0:
                # find_matching_values() will print an error.
                sys.exit(1)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    # Open the output stream/data file.
    if options.output is None:
        options.output = 'file://-'
    output_transport = create_transport(options.output, mode='output', stdout=original_stdout)
    if isinstance(output_transport, VirtualSerial):
        print(f'Writing output to: {output_transport}')

    # Open the input stream/data file.
    input_transport = create_transport(options.input, mode='input')

    # Listen for incoming data.
    start_time = datetime.now()
    last_print_time = datetime.now()
    bytes_received = 0
    bytes_forwarded = 0
    messages_received = 0
    messages_forwarded = 0

    decoder = FusionEngineDecoder(return_bytes=True)
    try:
        while True:
            # Need to specify read size or read waits for end of file character.
            # This returns immediately even if 0 bytes are available.
            if isinstance(input_transport, socket.socket):
                received_data = input_transport.recv(64)
            else:
                received_data = input_transport.read(64)

            if len(received_data) == 0:
                time.sleep(0.1)
            else:
                bytes_received += len(received_data)
                messages = decoder.on_data(received_data)
                for (header, message, raw_data) in messages:
                    # In unwrap mode, discard all but InputDataWrapper messages.
                    if options.unwrap and header.message_type != MessageType.INPUT_DATA_WRAPPER:
                        continue

                    messages_received += 1

                    # In unwrap mode, the input message is always an InputDataWrapper.
                    if options.unwrap:
                        pass_through_message = True
                    # Otherwise, see if this is in the list of user-specified message types to keep. If the list is
                    # empty, keep all messages.
                    else:
                        pass_through_message = (
                            len(message_types) == 0 or
                            (options.invert and header.message_type not in message_types) or
                            (not options.invert and header.message_type in message_types)
                        )

                    # If this is an InputDataWrapper and the user specified a list of data types to keep, keep only the
                    # messages with that kind of data. If the list is empty, keep all messages.
                    if pass_through_message and header.message_type == MessageType.INPUT_DATA_WRAPPER:
                        pass_through_message = (
                            len(input_data_types) == 0 or
                            (options.invert and message.data_type not in input_data_types) or
                            (not options.invert and message.data_type in input_data_types)
                        )

                    # If the message passed the filters above, output it now.
                    if pass_through_message:
                        messages_forwarded += 1
                        if options.unwrap:
                            bytes_forwarded += len(message.data)
                            output_transport.write(message.data)
                        else:
                            bytes_forwarded += len(raw_data)
                            output_transport.write(raw_data)

            if options.display:
                now = datetime.now()
                if (now - last_print_time).total_seconds() > 5.0:
                    print('Status: [bytes_in=%d, msgs_in=%d, bytes_out=%d, msgs_out=%d, elapsed_time=%d sec]' %
                          (bytes_received, messages_received, bytes_forwarded,
                           messages_forwarded, (now - start_time).total_seconds()))
                    last_print_time = now

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
