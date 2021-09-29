#!/usr/bin/env python3

import os
import sys

root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from fusion_engine_client.messages.defs import MessageHeader

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
    if len(sys.argv) != 2 or '--help' == sys.argv[1]:
        print(f'usage: {sys.argv[0]} INPUT_FILE')
        print(f'Recover fusion engine log from log with mixed contents')
        print(f'Creates a INPUT_FILE.p1log in directory of INPUT_FILE')

    in_path = sys.argv[1]
    out_path = in_path + ".p1log"

    header = MessageHeader()
    valid_count = 0
    with open(in_path, 'rb') as in_fd:
        with open(out_path, 'wb') as out_path:
            while True:
                if not advance_to_next_sync(in_fd):
                    break
                data = in_fd.read(MessageHeader.calcsize())
                read_len = len(data)
                try:
                    header.unpack(data, warn_on_unrecognized=False)
                    if header.payload_size_bytes > MessageHeader._MAX_EXPECTED_SIZE_BYTES:
                        raise ValueError('payload_size_bytes too large')
                    data += in_fd.read(header.payload_size_bytes)
                    read_len = len(data)
                    header.validate_crc(data)
                    out_path.write(data)
                    valid_count += 1
                except ValueError:
                    in_fd.seek(-read_len + 1, os.SEEK_CUR)
    print(f'Found {valid_count} valid fusion engine messages')

if __name__ == "__main__":
    main()
