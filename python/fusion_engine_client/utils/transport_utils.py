import re
import socket
from typing import Union

try:
    # pySerial is optional.
    import serial
    serial_supported = True
except ImportError:
    serial_supported = False
    # Dummy stand-in if pySerial is not installed.
    class serial:
        class Serial: pass
        class SerialException: pass

TRANSPORT_HELP_STRING = """\
The method used to communicate with the target device:
- tcp://HOSTNAME[:PORT] - Connect to the specified hostname (or IP address) and
  port over TCP (e.g., tty://192.168.0.3:30202); defaults to port 30200
- udp://:PORT - Listen for incoming data on the specified UDP port (e.g.,
  udp://:12345)
  Note: When using UDP, you must configure the device to send data to your
  machine.
- unix://FILENAME - Connect to the specified UNIX domain socket file
- [tty://]DEVICE:BAUD - Connect to a serial device with the specified baud rate
  (e.g., tty:///dev/ttyUSB0:460800 or /dev/ttyUSB0:460800) 
"""


def create_transport(descriptor: str) -> Union[socket.socket, serial.Serial]:
    m = re.match(r'^tcp://([a-zA-Z0-9-_.]+)?(?::([0-9]+))?$', descriptor)
    if m:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hostname = m.group(1)
        port = 30200 if m.group(2) is None else int(m.group(2))
        transport.connect((socket.gethostbyname(hostname), port))
        return transport

    m = re.match(r'^udp://:([0-9]+)$', descriptor)
    if m:
        transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = int(m.group(1))
        transport.bind(('', port))
        return transport

    m = re.match(r'^unix://([a-zA-Z0-9-_./]+)$', descriptor)
    if m:
        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        path = m.group(1)
        transport.connect(path)
        return transport

    m = re.match(r'^(?:(?:serial|tty)://)?([^:]+):([0-9]+)$', descriptor)
    if m:
        if serial_supported:
            path = m.group(1)
            baud_rate= int(m.group(2))
            transport = serial.Serial(port=path, baudrate=baud_rate)
            return transport
        else:
            raise RuntimeError(
                "This application requires pyserial. Please install (pip install pyserial) and run again.")

    raise ValueError('Unsupported transport descriptor.')
