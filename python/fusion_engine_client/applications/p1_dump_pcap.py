#!/usr/bin/env python3

import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, List, Tuple

import numpy as np
from scapy.all import PcapReader

if __package__ is None or __package__ == "":
    from import_utils import enable_relative_imports
    __package__ = enable_relative_imports(__name__, __file__)

# isort:split

from ..parsers.host_time_byte_mapper import HostTimeByteMapper
from ..utils import trace as logging
from ..utils.argument_parser import ArgumentParser, ExtendedBooleanAction


@dataclass
class DataStream:
    data_fd: BinaryIO
    bytes = 0
    index = 0


def main():
    parser = ArgumentParser(description="""\
Extract data streams from a pcap file.

Each network port sending data is broken into a separate file. Either:
`udp_{port}_`
or
`tcp_{port}_{num_reconnects}`

To capture a *.pcap file use a command like:
`sudo tcpdump -i any -nn -w /tmp/capture.pcap src 192.168.1.124`
which would capture all data sent from `192.168.1.124` to the host.

To simulate an application connecting over TCP, you can run:
`netcat 192.168.1.124 30200 > /dev/null`
to open a TCP connection.
""")

    parser.add_argument('-o', '--output', type=str, metavar='DIR',
                        help="The directory where output will be stored. Defaults to the parent directory of the input"
                             "file.")
    parser.add_argument('-p', '--prefix', type=str,
                        help="Use the specified prefix for the output file: `<prefix>.p1log`. Otherwise, use the "
                             "filename of the input data file (e.g., `input.p1log`), or `fusion_engine` if reading "
                             "from a log (e.g., `fusion_engine.p1log`).")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")
    parser.add_argument('--save-host-time-map', action=ExtendedBooleanAction, default=True,
                        help='For each extracted data stream save a map data offsets to host time.')
    parser.add_argument('pcap_file',
                        help="The pcap file to be read.")

    options = parser.parse_args()

    # Configure logging.
    logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)
    logger = logging.getLogger('point_one.fusion_engine')
    if options.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif options.verbose > 1:
        logger.setLevel(logging.getTraceLevel(depth=options.verbose - 1))

    input_path = Path(options.pcap_file)

    # Set the output directory.
    if options.output is not None:
        output_dir = Path(options.output)
    else:
        output_dir = input_path.parent

    # Read through the data file, searching for valid FusionEngine messages to extract and store in
    # 'output_dir/<prefix>.p1log'.
    if options.prefix is not None:
        prefix = options.prefix
    else:
        prefix = os.path.splitext(os.path.basename(input_path))[0]

    streams: Dict[str, DataStream] = {}

    num_reconnects = defaultdict(int)

    if options.save_host_time_map:
        host_times: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    else:
        host_times = None

    for packet in PcapReader(str(input_path)):
        logger.trace(packet.show(dump=True))

        if 'TCP' in packet:
            # Assumes TCPServer, not TCPClient
            port = packet["TCP"].sport
            # SYN flag indicates new connection
            if 'S' in packet["TCP"].flags:
                num_reconnects[port] += 1
            key = f'tcp_{packet["TCP"].sport}_{num_reconnects[port]}'
        elif 'UDP' in packet:
            key = f'udp_{packet["UDP"].dport}'
        else:
            continue

        if 'Raw' in packet:
            if key not in streams:
                new_path = os.path.join(output_dir, f'{prefix}_{key}.bin')
                streams[key] = DataStream(open(new_path, 'wb'))

            payload = packet['Raw'].load
            streams[key].bytes += len(payload)
            streams[key].data_fd.write(payload)

            if host_times is not None:
                host_times[key].append((packet.time, streams[key].bytes))

    if host_times is not None:
        for k, v in host_times.items():
            host_mapper = HostTimeByteMapper(streams[k].data_fd.name)
            host_mapper.load_list(v)
            host_mapper.write_to_file()

    for stream in streams.values():
        logger.info(f"{stream.bytes} B stored in '{stream.data_fd.name}'.")
        stream.data_fd.close()


if __name__ == "__main__":
    main()
