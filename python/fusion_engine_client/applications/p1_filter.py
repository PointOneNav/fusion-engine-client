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

from fusion_engine_client.messages import MessagePayload, message_type_by_name
from fusion_engine_client.parsers import FusionEngineDecoder
from fusion_engine_client.utils.argument_parser import ArgumentParser, ExtendedBooleanAction


if __name__ == "__main__":
    parser = ArgumentParser(description="""\
Filter FusionEngine data coming through stdin. Examples:
  netcat 192.168.1.138 30210 | \
     ./p1_filter.py --blacklist -m GNSSSatellite --display > /tmp/out.p1log
  cat /tmp/out.p1log | ./p1_filter.py -m Pose > /tmp/pose_out.p1log
  stty -F /dev/ttyUSB0 speed 460800 cs8 \
     -cstopb -parenb -icrnl -ixon -ixoff -opost -isig -icanon -echo && \
     cat /dev/ttyUSB0 | \
     ./p1_filter.py -m Pose > /tmp/pose_out.p1log
""")

    parser.add_argument(
        '-m', '--message-type', type=str, action='append',
        help="An list of class names corresponding with the message types to forward or discard (see --blacklist).\n"
             "\n"
             "May be specified multiple times (-m Pose -m PoseAux), or as a comma-separated list (-m Pose,PoseAux). "
             "All matches are case-insensitive.\n"
             "\n"
             "If a partial name is specified, the best match will be returned. Use the wildcard '*' to match multiple "
             "message types.\n"
             "\n"
             "Supported types:\n%s" % '\n'.join(['- %s' % c for c in message_type_by_name.keys()]))
    parser.add_argument(
        '--blacklist', action=ExtendedBooleanAction,
        help="""\
If specified, discard all message types specified with --message-type and output everything else.

By default, all specified message types are output and all others are discarded.""")
    parser.add_argument(
        '--display', action=ExtendedBooleanAction,
        help="Periodically print status on stderr.")
    options = parser.parse_args()

    # If the user specified a set of message names, lookup their type values. Below, we will limit the printout to only
    # those message types.
    message_types = set()
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
            print(str(e))
            sys.exit(1)

    start_time = datetime.now()
    last_print_time = datetime.now()
    bytes_received = 0
    bytes_forwarded = 0
    messages_received = 0
    messages_forwarded = 0

    # Listen for incoming data.
    decoder = FusionEngineDecoder(return_bytes=True)
    try:
        while True:
            # Need to specify read size or read waits for end of file character.
            # This returns immediately even if 0 bytes are available.
            received_data = sys.stdin.buffer.read(64)
            if len(received_data) == 0:
                time.sleep(0.1)
            else:
                bytes_received += len(received_data)
                messages = decoder.on_data(received_data)
                for (header, message, raw_data) in messages:
                    messages_received += 1
                    pass_through_message = (options.blacklist and header.message_type not in message_types) or (
                        not options.blacklist and header.message_type in message_types)
                    if pass_through_message:
                        messages_forwarded += 1
                        bytes_forwarded += len(raw_data)
                        original_stdout.buffer.write(raw_data)

            if options.display:
                now = datetime.now()
                if (now - last_print_time).total_seconds() > 5.0:
                    print('Status: [bytes_in=%d, msgs_in=%d, bytes_out=%d, msgs_out=%d, elapsed_time=%d sec]' %
                          (bytes_received, messages_received, bytes_forwarded,
                           messages_forwarded, (now - start_time).total_seconds()))
                    last_print_time = now

    except KeyboardInterrupt:
        pass
