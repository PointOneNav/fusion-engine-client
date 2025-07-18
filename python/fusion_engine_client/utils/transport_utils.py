import re
import socket
from typing import Callable, Union

try:
    # WebSocket support is optional. To use, install with:
    #   pip install websockets
    import websockets.sync.client as ws
    ws_supported = True
except ImportError:
    ws_supported = False
    # Dummy stand-ins for type hinting if websockets is not installed.
    class ws:
        class ClientConnection: pass

try:
    # Serial port support is optional. To use, install with:
    #   pip install pyserial
    import serial
    serial_supported = True

    # The Serial class has read() and write() functions. For convenience, we add recv() and send() aliases, consistent
    # with the Python socket class.
    def __recv(self, size, flags=None):
        data = self.read(size)
        if len(data) == 0 and size > 0:
            raise socket.timeout('Serial read timed out.')
        else:
            return data
    def __send(self, data, flags=None):
        self.write(data)
    serial.Serial.recv = __recv
    serial.Serial.send = __send
except ImportError:
    serial_supported = False
    # Dummy stand-in for type hinting if pySerial is not installed.
    class serial:
        class Serial: pass
        class SerialException(Exception): pass

TRANSPORT_HELP_STRING = """\
The method used to communicate with the target device:
- tcp://HOSTNAME[:PORT] - Connect to the specified hostname (or IP address) and
  port over TCP (e.g., tty://192.168.0.3:30202); defaults to port 30200
- udp://:PORT - Listen for incoming data on the specified UDP port (e.g.,
  udp://:12345)
  Note: When using UDP, you must configure the device to send data to your
  machine.
- ws://HOSTNAME:PORT - Connect to the specified hostname (or IP address) and
  port over WebSocket (e.g., ws://192.168.0.3:30300)
- unix://FILENAME - Connect to the specified UNIX domain socket file
- [(serial|tty)://]DEVICE:BAUD - Connect to a serial device with the specified
  baud rate (e.g., tty:///dev/ttyUSB0:460800 or /dev/ttyUSB0:460800)
"""


def create_transport(descriptor: str, timeout_sec: float = None, print_func: Callable = None) -> \
        Union[socket.socket, serial.Serial, ws.ClientConnection]:
    m = re.match(r'^tcp://([a-zA-Z0-9-_.]+)?(?::([0-9]+))?$', descriptor)
    if m:
        hostname = m.group(1)
        ip_address = socket.gethostbyname(hostname)
        port = 30200 if m.group(2) is None else int(m.group(2))
        if print_func is not None:
            print_func(f'Connecting to tcp://{ip_address}:{port}.')

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if timeout_sec is not None:
            transport.settimeout(timeout_sec)
        try:
            transport.connect((ip_address, port))
        except socket.timeout:
            raise socket.timeout(f'Timed out connecting to tcp://{ip_address}:{port}.')
        return transport

    m = re.match(r'^udp://:([0-9]+)$', descriptor)
    if m:
        port = int(m.group(1))
        if print_func is not None:
            print_func(f'Connecting to udp://:{port}.')

        transport = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if timeout_sec is not None:
            transport.settimeout(timeout_sec)
        transport.bind(('', port))
        return transport

    m = re.match(r'^ws://([a-zA-Z0-9-_.]+):([0-9]+)$', descriptor)
    if m:
        hostname = m.group(1)
        ip_address = socket.gethostbyname(hostname)
        port = int(m.group(2))

        url = f'ws://{ip_address}:{port}'

        if not ws_supported:
            raise RuntimeError(f'Websocket support not found. Cannot connect to {url}. '
                               f'Please install (pip install websockets) and run again.')

        if print_func is not None:
            print_func(f'Connecting to {url}.')

        try:
            transport = ws.connect(url, open_timeout=timeout_sec)
        except TimeoutError:
            raise TimeoutError(f'Timed out connecting to {url}.')
        return transport

    m = re.match(r'^unix://([a-zA-Z0-9-_./]+)$', descriptor)
    if m:
        path = m.group(1)
        if print_func is not None:
            print_func(f'Connecting to unix://{path}.')

        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if timeout_sec is not None:
            transport.settimeout(timeout_sec)
        transport.connect(path)
        return transport

    m = re.match(r'^(?:(?:serial|tty)://)?([^:]+)(?::([0-9]+))?$', descriptor)
    if m:
        path = m.group(1)
        if m.group(2) is None:
            raise ValueError('Serial baud rate not specified.')
        else:
            baud_rate = int(m.group(2))

        if not serial_supported:
            raise RuntimeError(f'Serial port support not found. Cannot connect to tty://{path}:{baud_rate}. '
                               f'Please install (pip install pyserial) and run again.')
        if print_func is not None:
            print_func(f'Connecting to tty://{path}:{baud_rate}.')

        transport = serial.Serial(port=path, baudrate=baud_rate, timeout=timeout_sec)
        return transport

    raise ValueError('Unsupported transport descriptor.')
