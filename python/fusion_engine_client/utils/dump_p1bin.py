import logging

from construct import *

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
