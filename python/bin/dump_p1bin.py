#!/usr/bin/env python3

import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

#!/usr/bin/env python3
from construct import *

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

def main():
    if len(sys.argv) != 2 or '--help' == sys.argv[1]:
        print(f'usage: {sys.argv[0]} INPUT_P1BIN_FILE')
        print(f'Dump contents of p1bin to files by msg_type')
        print(f'Creates a INPUT_P1BIN_FILE.[TYPE].bin in directory of INPUT_P1BIN_FILE')

    in_path = sys.argv[1]
    out_files = {}

    valid_count = 0
    with open(in_path, 'rb') as in_fd:
        assert(in_fd.read(1) == b'\x01')
        while True:
            try:
                record = p1bin_entry.parse_stream(in_fd)
                message_type = record.message_header.message_type
                if message_type not in out_files:
                    out_files[message_type] = open(f'{in_path}.{message_type}.bin','wb')
                out_files[message_type].write(record.contents)
                valid_count += 1
            except:
                break
    print(f'Found {valid_count} messages of types {list(out_files.keys())}')

if __name__ == "__main__":
    main()
