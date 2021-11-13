#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
import os
import sys

from construct import *

# Add the Python root directory (fusion-engine-client/python/) to the import search path.
if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.append(root_dir)
    __package__ = "fusion_engine_client.utils"

from ..utils.log import find_log_file

_logger = logging.getLogger('point_one.fusion_engine.utils.dump_p1bin')

timestamp = Struct(
    "time_seconds" / Int32ul,
    "time_fraction_ns" / Int32ul,
)

p1bin_file_header = Struct(
    "file_entry_header_version" / Const(1, Int8ul),
    "unix_serialization_time" / timestamp,
)

p1bin_message_header = Struct(
    "message_header_version" / Const(1, Int8ul),
    "message_type" / Int16ul,
    "payload_size_bytes" / Int32ul,
    "source_identifier" / Int32ul,
)

p1bin_entry = Struct(
    "file_header" / p1bin_file_header,
    "message_header" / p1bin_message_header,
    "contents" / Bytes(this.message_header.payload_size_bytes),
)

p1bin_file = Struct(
    "api_version" / Const(1, Int8ul),
    "records" / GreedyRange(p1bin_entry),
)


def dump_p1bin(input_path, output_dir=None, prefix=None):
    """!
    @brief Extract streaming binary data from a Point One `*.p1bin` file.

    This function creates one binary file for each Point One message IDs found in the file. Extracted data will be
    stored in `<output_dir>/<prefix>.<message_id>.bin`.

    @note
    `.p1bin` file message IDs are _not_ the same as FusionEngine message types.

    @param input_path The path to the binary file to be read.
    @param output_dir The directory where generated output files will be stored. If `None`, data will be stored in the
           same directory as `input_path`.
    @param prefix A prefix to include with each generated file. If `None`, will be set to the prefix of `input_path`.

    @return A tuple containing:
            - The number of decoded messages.
            - A `dict` containing the path to the output file for each message ID. Only provided if `return_files` is
              `True`.
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_path)
    if prefix is None:
        prefix = os.path.splitext(os.path.basename(input_path))[0]

    out_paths = {}
    out_files = {}
    valid_count = 0
    with open(input_path, 'rb') as in_fd:
        assert(in_fd.read(1) == b'\x01')
        while True:
            try:
                offset = in_fd.tell()
                record = p1bin_entry.parse_stream(in_fd)
                message_type = record.message_header.message_type
                if message_type not in out_files:
                    out_paths[message_type] = os.path.join(output_dir, f'{prefix}.{message_type}.bin')
                    out_files[message_type] = open(out_paths[message_type], 'wb')
                _logger.debug('Read %d bytes @ %d (0x%x). [message_type=%d, # messages=%d]' %
                      (len(record.contents), offset, offset, message_type, valid_count + 1))
                out_files[message_type].write(record.contents)
                valid_count += 1
            except:
                break

    for fd in out_files.values():
        fd.close()

    return valid_count, out_paths


def main():
    parser = ArgumentParser(description="""\
Dump contents of a .p1bin file to individual binary files, separated by message
type.
""")

    parser.add_argument('--log-base-dir', metavar='DIR', default='/logs',
                        help="The base directory containing FusionEngine logs to be searched if a log pattern is"
                             "specified.")
    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the parent directory of the input"
                             "file, or to the log directory if reading from a log.")
    parser.add_argument('-p', '--prefix', type=str,
                        help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                             "filename of the input data file.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('log',
                        help="The log to be read. May be one of:\n"
                             "- The path to a .p1bin file\n"
                             "- The path to a FusionEngine log directory\n"
                             "- A pattern matching a FusionEngine log directory under the specified base directory "
                             "(see find_fusion_engine_log() and --log-base-dir)")

    options = parser.parse_args()

    # Configure logging.
    if options.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s:%(lineno)d - %(message)s')
        logger = logging.getLogger('point_one.fusion_engine')
        logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Locate the input file and set the output directory.
    try:
        input_path, output_dir, log_id = find_log_file(options.log, candidate_files='input.p1bin',
                                                       return_output_dir=True, return_log_id=True,
                                                       log_base_dir=options.log_base_dir)

        if log_id is None:
            _logger.info('Loading %s.' % os.path.basename(input_path))
        else:
            _logger.info('Loading %s from log %s.' % (os.path.basename(input_path), log_id))

        if options.output is not None:
            output_dir = options.output
    except FileNotFoundError as e:
        _logger.error(str(e))
        sys.exit(1)

    # Parse each entry in the .p1bin file and extract its contents to 'output_dir/<prefix>.message_type.bin', where
    # message_type is the numeric type identifier.
    if options.prefix is not None:
        prefix = options.prefix
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]

    valid_count, out_files = dump_p1bin(input_path=input_path, output_dir=output_dir, prefix=prefix)
    _logger.info(f'Found {valid_count} messages of types {list(out_files.keys())}')
    _logger.info(f"Output stored in '{output_dir}'.")


if __name__ == "__main__":
    main()
