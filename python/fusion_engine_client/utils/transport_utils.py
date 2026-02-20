import re
import socket
import sys
from typing import BinaryIO, Callable, TextIO, Union

# WebSocket support is optional. To use, install with:
#   pip install websockets
try:
    import websockets.sync.client as ws
    ws_supported = True
except ImportError:
    ws_supported = False
    # Dummy stand-ins for type hinting if websockets is not installed.
    class ws:
        class ClientConnection: pass

# Serial port support is optional. To use, install with:
#   pip install pyserial
try:
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

# Virtual serial port support is optional. To use, install with:
#   pip install pyvirtualserialports pyserial
try:
    if not serial_supported:
        raise ImportError()

    from virtualserialports import VirtualSerialPorts
    virtual_serial_supported = True

    class VirtualSerial(serial.Serial):
        def __init__(self):
            # Virtual ports work as a pair:
            # - ports[0] is used internally by the application to send to/receive from ports[1]
            # - ports[1] is what the user actually connects to
            #
            # Note that baud rate doesn't matter for virtual serial ports. The user can connect to ports[1] with any
            # baud rate and it'll work.
            self.virtual_serial = VirtualSerialPorts(2)
            self.virtual_serial.open()
            self.virtual_serial.start()
            self.internal_port = self.virtual_serial.ports[0]
            self.external_port = self.virtual_serial.ports[1]
            super().__init__(port=self.internal_port)

        def close(self):
            super().close()
            self.virtual_serial.stop()
            self.virtual_serial.close()

        def __str__(self):
            return f'tty://{self.external_port}'
except ImportError:
    virtual_serial_supported = False
    class VirtualSerial: pass


class FileTransport:
    def __init__(self, input: Union[str, BinaryIO, TextIO] = None, output: Union[str, BinaryIO, TextIO] = None):
        # If input is a path, open the specified file. If '-', read from stdin.
        self.close_input = False
        if isinstance(input, str):
            if input in ('', '-'):
                self.input = sys.stdin.buffer
                self.input_path = 'stdin'
            else:
                self.input = open(input, 'rb')
                self.input_path = input
                self.close_input = True
        # Otherwise, assume input is a file-like object and use it as is.
        elif isinstance(input, TextIO):
            self.input = input.buffer
            self.input_path = input.name if input else None
        elif isinstance(input, BinaryIO):
            self.input = input
            self.input_path = input.name if input else None
        elif input is None:
            self.input = None
            self.input_path = None
        else:
            raise ValueError('Unsupported input type.')

        # If output is a path, open the specified file. If '-', write to stdout.
        self.close_output = False
        if isinstance(output, str):
            if output in ('', '-'):
                self.output = sys.stdout.buffer
                self.output_path = 'stdout'
            else:
                self.output = open(output, 'wb')
                self.output_path = output
                self.close_output = True
        # Otherwise, assume output is a file-like object and use it as is.
        elif isinstance(output, TextIO):
            self.output = output.buffer
            self.output_path = output.name if output else None
        elif isinstance(output, BinaryIO):
            self.output = output
            self.output_path = output.name if output else None
        elif output is None:
            self.output = None
            self.output_path = None
        else:
            raise ValueError('Unsupported input type.')

    def close(self):
        if self.close_input:
            self.input.close()
        if self.close_output:
            self.output.close()

    def read(self, size: int = -1) -> bytes:
        if self.input:
            return self.input.read(size)
        else:
            raise RuntimeError('Input file not opened.')

    def write(self, data: Union[bytes, bytearray]) -> int:
        if self.output:
            return self.output.write(data)
        else:
            raise RuntimeError('Output file not opened.')


class WebsocketTransport:
    """!
    @brief Websocket wrapper class, mimicking the Python socket API.

    This class defers all function calls and attribute to the underlying `ws.ClientConnection` websocket instance. Any
    function defined for `ClientConnection` should work on this class (e.g., `close()`).
    """

    def __init__(self, *args, **kwargs):
        # Note: Omitting "_sec" from argument name for consistent with connect() arguments.
        self._read_timeout_sec = kwargs.pop('read_timeout', None)

        self._websocket = kwargs.pop('websocket', None)
        if self._websocket is None:
            self._websocket = ws.connect(*args, **kwargs)

    def set_timeout(self, timeout_sec: float):
        if timeout_sec < 0.0:
            self._read_timeout_sec = None
        else:
            self._read_timeout_sec = timeout_sec

    def recv(self, unused_size_bytes: int = None) -> bytes:
        """!
        @brief Receive data from the websocket.

        @note
        This function wraps the `ws.ClientConnection.recv()` function. WebSockets are not streaming transports, they are
        message-oriented. The Python websocket library does not support reading a specified number of bytes. The
        `unused_size_bytes` parameter is listed here for consistency with `socket.recv()`.

        @param unused_size_bytes Unused.

        @return The received bytes, or NOne on timeout.
        """
        try:
            return self._websocket.recv(self._read_timeout_sec)
        except TimeoutError as e:
            # recv() raises a TimeoutError. We'll raise a socket.timeout exception instead for consistency with socket.
            raise socket.timeout(str(e))

    def __getattr__(self, item):
        # Defer all queries for attributes and functions that are not members of this class to self._websocket.
        # __getattribute__() will handle requests for members of this class (recv(), _read_timeout_sec, etc.), and
        # __getattr() will not be called.
        return getattr(self._websocket, item)

    def __setattr__(self, item, value):
        # There is no __setattribute__() like there is for get. See details in __getattr__().
        if item in ('_read_timeout_sec', '_websocket'):
            object.__setattr__(self, item, value)
        else:
            setattr(self._websocket, item, value)


TRANSPORT_HELP_OPTIONS = """\
- <empty string> - Read from stdin and/or write to stdout
- [file://](PATH|-) - Read from/write to the specified file, or to stdin/stdout
  if PATH is '-'.
- tcp://HOSTNAME[:PORT] - Connect to the specified hostname (or IP address) and
  port over TCP (e.g., tty://192.168.0.3:30202); defaults to port 30200.
- udp://:PORT - Listen for incoming data on the specified UDP port (e.g.,
  udp://:12345).
  Note: When using UDP, you must configure the device to send data to your
  machine.
- unix://FILENAME - Connect to the specified UNIX domain socket file.
- ws://HOSTNAME:PORT - Connect to the specified hostname (or IP address) and
  port over WebSocket (e.g., ws://192.168.0.3:30300).
- [(serial|tty)://]DEVICE:BAUD - Connect to a serial device with the specified
  baud rate (e.g., tty:///dev/ttyUSB0:460800 or /dev/ttyUSB0:460800).
- (serial|tty)://virtual - Create a virtual serial port (PTS) that another
  application can connect to.
"""

TRANSPORT_HELP_STRING = f"""\
The method used to communicate with the target device:
{TRANSPORT_HELP_OPTIONS}
"""

TransportType = Union[socket.socket, serial.Serial, WebsocketTransport, FileTransport]


def create_transport(descriptor: str, timeout_sec: float = None, print_func: Callable = None, mode: str = 'both',
                     stdout=sys.stdout) -> TransportType:
    # File: path, '-' (stdin/stdout), empty string (stdin/stdout)
    if descriptor in ('', '-'):
        descriptor = 'file://-'

    m = re.match(r'^(?:file://)?([a-zA-Z0-9-_./]+)$', descriptor)
    if m:
        path = m.group(1)
        if mode == 'both':
            if path != '-':
                raise ValueError("Cannot open a file for both read and write access.")

            if print_func is not None:
                print_func(f'Connecting to stdin/stdout.')
            transport = FileTransport(input='-', output='-')
        elif mode == 'input':
            if print_func is not None:
                if path == '-':
                    print_func(f'Reading from stdin.')
                else:
                    print_func(f'Reading from {path}.')
            transport = FileTransport(input=path, output=None)
        elif mode == 'output':
            if print_func is not None:
                if path == '-':
                    print_func(f'Writing to stdout.')
                else:
                    print_func(f'Writing to {path}.')
            transport = FileTransport(input=None, output=stdout.buffer)
        else:
            raise ValueError(f"Unsupported file mode '{mode}'.")
        return transport

    # TCP client
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

    # UDP client
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

    # Websocket client
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
            transport = WebsocketTransport(url, open_timeout=timeout_sec)
        except TimeoutError:
            raise TimeoutError(f'Timed out connecting to {url}.')
        return transport

    # UNIX domain socket
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

    # Virtual serial port
    m = re.match(r'^(?:serial|tty)://virtual$', descriptor)
    if m:
        if not virtual_serial_supported:
            raise RuntimeError(f'Virtual serial port support not found.'
                               f'Please install (pip install pyvirtualserialports pyserial) and run again.')

        transport = VirtualSerial()
        if print_func is not None:
            print_func(f'Connecting to {str(transport)}.')
        return transport

    # Serial port
    m = re.match(r'^(?:(?:serial|tty)://)?([^:]+)(?::([0-9]+))$', descriptor)
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

    raise ValueError(f"Unsupported transport descriptor '{descriptor}'.")
