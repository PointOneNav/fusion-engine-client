#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import sys

# Add the Python root directory (fusion-engine-client/python/) to the import search path.
root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.defs import MessageHeader, MessageType
# Note: This import isn't actually used explicitly, but by importing it all the internal message types will be added to
# the MessageType enum and can be printed out in the verbose print below.
from fusion_engine_client.messages.internal import InternalMessageType
from fusion_engine_client.utils.log import find_log_file


def advance_to_next_sync(in_fd):
    try:
        while True:
            byte0 = in_fd.read(1)[0]
            while True:
                if byte0 == MessageHeader._SYNC0:
                    byte1 = in_fd.read(1)[0]
                    if byte1 == MessageHeader._SYNC1:
                        in_fd.seek(-2, os.SEEK_CUR)
                        return True
                    byte0 = byte1
                else:
                    break
    except IndexError:
        return False


def main():
    parser = ArgumentParser(description="""\
Extract FusionEngine message contents from a binary file containing mixed data (e.g., interleaved RTCM and FusionEngine
messages).
""")

    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
                             "specified.")
    parser.add_argument('-c', '--candidate-files', type=str, metavar='DIR',
                        help="An optional comma-separated list of candidate input filenames to search within the log "
                             "directory.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the parent directory of the input"
                             "file, or to the log directory if reading from a log.")
    parser.add_argument('-p', '--prefix', type=str,
                        help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                             "filename of the input data file (e.g., `input.p1log`), or `fusion_engine` if reading "
                             "from a log (e.g., `fusion_engine.p1log`).")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a binary data file\n"
                             "- The path to a FusionEngine log directory containing an `input.p1bin` file\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    # Locate the input file and set the output directory.
    try:
        if options.candidate_files is None:
            # Note that we prioritize the input.66.bin file over the others. For logs containing a single mixed serial
            # data stream as a single message type within the .p1bin file (e.g., Quectel platforms), individual
            # FusionEngine messages may be interrupted by .p1bin message headers since the .p1bin entires are just
            # arbitrary byte blocks. In that case, we must first strip the .p1bin headers using dump_p1bin.py. ID 66 is
            # the value assigned to Quectel/Teseo data within .p1bin files.
            candidate_files = ['input.66.bin', 'input.p1bin', 'input.rtcm3']
        else:
            candidate_files = options.candidate_files.split(',')

        input_path, output_dir, log_id = find_log_file(options.log, candidate_files=candidate_files,
                                                       return_output_dir=True, return_log_id=True,
                                                       log_base_dir=options.log_base_dir)

        if log_id is None:
            print('Loading %s.' % os.path.basename(input_path))
        else:
            print('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if options.output is not None:
            output_dir = options.output
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    # Read through the data file, searching for valid FusionEngine messages to extract and store in
    # 'output_dir/<prefix>.p1log'.
    if options.prefix is not None:
        prefix = options.prefix
    elif log_id is not None:
        prefix = 'fusion_engine'
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, prefix + '.p1log')

    header = MessageHeader()
    valid_count = 0
    message_counts = {}
    with open(input_path, 'rb') as in_fd:
        with open(output_path, 'wb') as out_path:
            while True:
                if not advance_to_next_sync(in_fd):
                    break

                offset = in_fd.tell()
                if options.verbose >= 2:
                    print('Reading candidate message @ %d (0x%x).' % (offset, offset))

                data = in_fd.read(MessageHeader.calcsize())
                read_len = len(data)
                try:
                    header.unpack(data, warn_on_unrecognized=False)
                    if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                        raise ValueError('Payload size (%d) too large.' % header.payload_size_bytes)

                    payload = in_fd.read(header.payload_size_bytes)
                    read_len += len(payload)
                    if len(payload) != header.payload_size_bytes:
                        raise ValueError('Not enough data - likely not a valid FusionEngine header.')

                    data += payload
                    header.validate_crc(data)

                    if options.verbose >= 1:
                        print('Read %s message @ %d (0x%x). [length=%d B, # messages=%d]' %
                              (header.get_type_string(), offset, offset,
                               MessageHeader.calcsize() + header.payload_size_bytes, valid_count + 1))

                    out_path.write(data)
                    valid_count += 1
                    message_counts.setdefault(header.message_type, 0)
                    message_counts[header.message_type] += 1
                except ValueError as e:
                    offset += 1
                    if options.verbose >= 2:
                        print('%s Rewinding to offset %d (0x%x).' % (str(e), offset, offset))
                    in_fd.seek(offset, os.SEEK_SET)

    print(f'Found {valid_count} valid FusionEngine messages.')
    if options.verbose >= 1:
        for type, count in message_counts.items():
            print('  %s: %d' % (MessageType.get_type_string(type), count))
    print(f"Output stored in '{output_path}'.")


if __name__ == "__main__":
    main()
