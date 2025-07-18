#! /usr/bin/env python
"""
Utilities for handling socket timestamping on Linux systems.
See: https://docs.kernel.org/networking/timestamping.html

These values and functions target 64-bit Debian systems kernel version 6.12.25 and may be different on different
platforms.
"""

from pathlib import Path
import socket
import struct
import sys
from typing import BinaryIO, Optional, TypeAlias


_CMSG: TypeAlias = tuple[int, int, bytes]

TIMESTAMP_FILE_ENDING = '.data_times.bin'

HW_TIMESTAMPING_HELP = """\
To check if your network interface supports hardware timestamping:
  sudo ethtool -T <interface_name>"
  Example: sudo ethtool -T eth0
Look for 'hardware-transmit' and 'hardware-receive' capabilities.

In addition, HW timestamping needs to be explicitly enabled. This can be done by
tools like hwstamp_ctl or tcpdump.
  Example: sudo hwstamp_ctl -i eth0 -r 1
  Example: timeout 1 sudo tcpdump -j adapter_unsynced -i eth0 > /dev/null
"""

_TIMESTAMP_STRUCT = struct.Struct('QQ')

#################### Linux socket constants ###################
# These values were taken from a Debian kernel version 6.12.25 system and may be different on different platforms.

# Generates timestamps on reception, transmission or both. Supports multiple timestamp sources, including hardware.
# Supports generating timestamps for stream sockets.
SO_TIMESTAMPING = 37

# Some bits are requests to the stack to try to generate timestamps. Any combination of them is valid. Changes to these
# bits apply to newly created packets, not to packets already in the stack. As a result, it is possible to selectively
# request timestamps for a subset of packets (e.g., for sampling) by embedding an send() call within two setsockopt
# calls, one to enable timestamp generation and one to disable it. Timestamps may also be generated for reasons other
# than being requested by a particular socket, such as when receive timestamping is enabled system wide.
#
# Request tx timestamps generated by the network adapter. This flag can be enabled via both socket options and control
# messages.
SOF_TIMESTAMPING_TX_HARDWARE = 1 << 0
# Request tx timestamps when data leaves the kernel. These timestamps are generated in the device driver as close as
# possible, but always prior to, passing the packet to the network interface. Hence, they require driver support and may
# not be available for all devices. This flag can be enabled via both socket options and control messages.
SOF_TIMESTAMPING_TX_SOFTWARE = 1 << 1
# Request rx timestamps generated by the network adapter.
SOF_TIMESTAMPING_RX_HARDWARE = 1 << 2
# Request rx timestamps when data enters the kernel. These timestamps are generated just after a device driver hands a
# packet to the kernel receive stack.
SOF_TIMESTAMPING_RX_SOFTWARE = 1 << 3

# The other three bits control which timestamps will be reported in a generated control message. Changes to the bits
# take immediate effect at the timestamp reporting locations in the stack. Timestamps are only reported for packets that
# also have the relevant timestamp generation request set.
#
# Report any software timestamps when available.
SOF_TIMESTAMPING_SOFTWARE = 1 << 4
# This option is deprecated and ignored.
SOF_TIMESTAMPING_SYS_HARDWARE = 1 << 5
# Report hardware timestamps as generated by SOF_TIMESTAMPING_TX_HARDWARE or SOF_TIMESTAMPING_RX_HARDWARE when
# available.
SOF_TIMESTAMPING_RAW_HARDWARE = 1 << 6


def parse_timestamps_from_ancdata(ancdata: list[_CMSG]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Parse timestamps from ancillary data.
    See: https://docs.kernel.org/networking/timestamping.html#scm-timestamping-records

    SO_TIMESTAMPING provides up to 3 timestamps:
    [0] Software timestamp
    [1] Hardware timestamp (deprecated)
    [2] Raw hardware timestamp
    """
    timestamps = []

    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == SO_TIMESTAMPING:
            # Each timestamp is 16 bytes (2 * 8 bytes for sec + nsec)
            for i in range(0, min(len(cmsg_data), 48), 16):  # Max 3 timestamps
                if i + 16 <= len(cmsg_data):
                    sec, nsec = _TIMESTAMP_STRUCT.unpack_from(cmsg_data, i)
                    if sec > 0:  # Valid timestamp
                        timestamp = sec + (nsec / 1e9)
                        timestamps.append(timestamp)
                    else:
                        timestamps.append(None)

    # Pad with None if we have fewer than 3 timestamps
    while len(timestamps) < 3:
        timestamps.append(None)

    return tuple(timestamps)


def enable_socket_timestamping(sock: socket.socket, enable_sw_timestamp: bool, enable_hw_timestamp: bool):
    if enable_sw_timestamp or enable_hw_timestamp:
        flags = 0
        if enable_sw_timestamp:
            flags |= SOF_TIMESTAMPING_RX_SOFTWARE | SOF_TIMESTAMPING_SOFTWARE

        if enable_hw_timestamp:
            flags |= SOF_TIMESTAMPING_RX_HARDWARE | SOF_TIMESTAMPING_RAW_HARDWARE

        sock.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPING, flags)


def log_timestamped_data_offset(fd: BinaryIO, timestamp_ns: int, byte_offset: int):
    '''
    Log the host timestamp associated with the reception of the byte at byte_offset.

    For example, after startup if the first packet is 10 bytes at time 1.0, timestamp_ns would be 1e9 and byte_offset
    would be 10.

    This implies that for each update the bytes between each entry are associated with later entry.

    For example if the second entry was 20 bytes at time 3.0:
      - bytes 0-9 would have timestamp 1.0
      - bytes 10-29 would have timestamp 3.0
    '''
    fd.write(_TIMESTAMP_STRUCT.pack(timestamp_ns, byte_offset))


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "google.com"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    send_get = port == 80
    get_request = f"GET / HTTP/1.1\r\nHost: {host}\r\n\r\n".encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    enable_socket_timestamping(sock, True, True)
    sock.connect((host, port))
    if send_get:
        sock.send(get_request)

    data, ancdata, flags, addr = sock.recvmsg(1024, 1024)
    sock.close()

    sw_timestamp, _, hw_timestamp = parse_timestamps_from_ancdata(ancdata)
    if sw_timestamp:
        print("[AVAILABLE] SW timestamps")
    else:
        print("  [MISSING] SW timestamps")

    if hw_timestamp:
        print("[AVAILABLE] HW timestamps")
    else:
        print("  [MISSING] HW timestamps")
        print("\n" + HW_TIMESTAMPING_HELP)


if __name__ == "__main__":
    main()
