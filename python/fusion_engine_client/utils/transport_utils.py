import os
import re
import socket
import sys
import threading
import time
from typing import Any, BinaryIO, Callable, TextIO, Union

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
        self.is_stdin = False
        if isinstance(input, str):
            if input in ('', '-'):
                self.input = sys.stdin.buffer
                self.input_path = 'stdin'
                self.is_stdin = True
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
        self.is_stdout = False
        if isinstance(output, str):
            if output in ('', '-'):
                self.output = sys.stdout.buffer
                self.output_path = 'stdout'
                self.is_stdout = True
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


class SocketTransport:
    """!
    @brief Socket wrapper class, protecting against multiple close() calls.

    All other member or function accesses are deferred to the underlying `socket.socket` instance.
    """
    def __init__(self, *args, sock: socket.socket = None, **kwargs):
        self._socket = sock if sock is not None else socket.socket(*args, **kwargs)
        self._closed = False

    @property
    def socket(self):
        return self._socket

    def close(self):
        if not self._closed:
            self._closed = True
            self._socket.close()

    def __getattr__(self, name):
        return getattr(self._socket, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TCPServerTransport(SocketTransport):
    """!
    @brief TCP transport that accepts incoming connections on a background thread.

    Unlike connecting as a TCP client, an application acting as a TCP server does not know when (or if) a client will
    connect. This class starts listening immediately and accepts connections on a background thread so construction
    does not block, allowing the application to continue starting up while it waits. If the connected client
    disconnects, the transport goes back to listening.

    `setblocking()`/`settimeout()`/`setsockopt()` are recorded and replayed on each newly accepted connection if
    called while no client is connected. `recv()` and other calls block until a client has connected, since there is
    nothing to receive until then; if the client disconnects mid-`recv()`, this waits for a new client rather than
    raising. `send()` does not block; if there is no connected client (including right after a disconnect), the data
    is silently dropped.

    `close()` may be called at any time, including before a client has connected, and stops the background thread
    within `_POLL_INTERVAL_SEC` rather than blocking indefinitely on the OS-level `accept()` call.
    """

    _DEFERRABLE_METHODS = ('setblocking', 'settimeout', 'setsockopt')

    # How often the background thread wakes up to check whether it should stop (or whether the current client has
    # disconnected and it should accept a new one). This bounds how long close() can take if no client is connected.
    _POLL_INTERVAL_SEC = 0.2

    def __init__(self, port: int, timeout_sec: float = None, print_func: Callable = None):
        self._closed = False
        self._connect_timeout_sec = timeout_sec
        self._print_func = print_func
        self._connected_event = threading.Event()
        self._lock = threading.Lock()
        self._pending_opts = []
        self._socket = None

        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.settimeout(self._POLL_INTERVAL_SEC)
        self._listener.bind(('', port))
        self._listener.listen(1)

        self._accept_thread = threading.Thread(
            target=self._accept_loop, name=f'tcp-server-accept-{port}', daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        while True:
            with self._lock:
                if self._closed:
                    return
                have_client = self._socket is not None
            if have_client:
                # A client is already connected. Wait for it to disconnect before accepting another.
                time.sleep(self._POLL_INTERVAL_SEC)
                continue

            try:
                client_socket, client_address = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return  # Listener was closed out from under us by close().

            with self._lock:
                if self._closed:
                    client_socket.close()
                    return

                if self._connect_timeout_sec is not None:
                    client_socket.settimeout(self._connect_timeout_sec)
                for name, args, kwargs in self._pending_opts:
                    getattr(client_socket, name)(*args, **kwargs)

                self._socket = client_socket
                self._connected_event.set()

            if self._print_func is not None:
                self._print_func(f'Accepted connection from {client_address[0]}:{client_address[1]}.')

    def _handle_disconnect(self, sock: socket.socket):
        with self._lock:
            if self._socket is sock:
                self._socket = None
                self._connected_event.clear()
        sock.close()
        if self._print_func is not None:
            self._print_func('Client disconnected. Waiting for a new connection.')

    def recv(self, *args, **kwargs) -> bytes:
        """!
        @brief Receive data from the connected client.

        Blocks until a client is connected. If the client disconnects, waits for a new client to connect instead of
        raising an exception.
        """
        while True:
            self._connected_event.wait()
            sock = self._socket
            if sock is None:
                continue
            try:
                data = sock.recv(*args, **kwargs)
            except (socket.timeout, TimeoutError):
                raise
            except OSError:
                self._handle_disconnect(sock)
                continue
            if len(data) == 0:
                # The client performed an orderly shutdown.
                self._handle_disconnect(sock)
                continue
            return data

    def send(self, data, *args, **kwargs) -> int:
        """!
        @brief Send data to the connected client.

        Unlike `recv()`, this does not block waiting for a client to connect. If there is no connected client
        (including right after a disconnect), the data is silently dropped.

        @param data The data to be sent.

        @return The number of bytes sent, or 0 if no client is connected.
        """
        sock = self._socket
        if sock is None:
            return 0
        try:
            return sock.send(data, *args, **kwargs)
        except OSError:
            self._handle_disconnect(sock)
            return 0

    def wait_for_connection(self, timeout_sec: float = None) -> bool:
        """!
        @brief Block until a client has connected.

        @param timeout_sec Maximum time to wait (in seconds), or `None` to wait forever.

        @return `True` once a client is connected, or `False` if `timeout_sec` elapses first.
        """
        return self._connected_event.wait(timeout_sec)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            sock = self._socket
        self._listener.close()
        self._accept_thread.join(timeout=self._POLL_INTERVAL_SEC * 2)
        if sock is not None:
            sock.close()

    def __getattr__(self, name):
        if name in self._DEFERRABLE_METHODS:
            def _deferred(*args, **kwargs):
                with self._lock:
                    if self._socket is None:
                        self._pending_opts.append((name, args, kwargs))
                        return None
                return getattr(self._socket, name)(*args, **kwargs)
            return _deferred

        self._connected_event.wait()
        return getattr(self._socket, name)


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

    def __getattr__(self, item: str) -> Any:
        # Defer all queries for attributes and functions that are not members of this class to self._websocket.
        # __getattribute__() will handle requests for members of this class (recv(), _read_timeout_sec, etc.), and
        # __getattr() will not be called.
        return getattr(self._websocket, item)

    def __setattr__(self, item: str, value: Any) -> None:
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
- tcp://:PORT - Listen for an incoming TCP connection on the specified port
  (e.g., tcp://:30200).
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

TransportClass = Union[SocketTransport, serial.Serial, WebsocketTransport, FileTransport]


def create_transport(descriptor: str, timeout_sec: float = None, print_func: Callable = None, mode: str = 'both',
                     stdout=sys.stdout) -> TransportClass:
    # File: path, '-' (stdin/stdout), empty string (stdin/stdout)
    if descriptor in ('', '-'):
        descriptor = 'file://-'

    m = re.match(r'^(?:file://)?((?:~/)?[a-zA-Z0-9-_./]+)$', descriptor)
    if m:
        path = os.path.expanduser(m.group(1))
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
            transport = FileTransport(input=None, output=path)
        else:
            raise ValueError(f"Unsupported file mode '{mode}'.")
        return transport

    # TCP server
    m = re.match(r'^tcp://(?:0\.0\.0\.0)?:([0-9]+)$', descriptor)
    if m:
        port = int(m.group(1))
        if print_func is not None:
            print_func(f'Listening for TCP connections on port {port}.')

        # Note: timeout_sec is applied to the accepted connection (once a client connects), not to
        # how long we wait for that connection. We wait in the background indefinitely so the
        # caller is not blocked before a client connects.
        return TCPServerTransport(port, timeout_sec=timeout_sec, print_func=print_func)

    # TCP client
    m = re.match(r'^tcp://([a-zA-Z0-9-_.]+)(?::([0-9]+))?$', descriptor)
    if m:
        hostname = m.group(1)
        ip_address = socket.gethostbyname(hostname)
        port = 30200 if m.group(2) is None else int(m.group(2))
        if print_func is not None:
            print_func(f'Connecting to tcp://{ip_address}:{port}.')

        transport = SocketTransport(socket.AF_INET, socket.SOCK_STREAM)
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

        transport = SocketTransport(socket.AF_INET, socket.SOCK_DGRAM)
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

        transport = SocketTransport(socket.AF_UNIX, socket.SOCK_STREAM)
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


def recv_from_transport(transport: TransportClass, size_bytes: int) -> bytes:
    '''!
    @brief Helper function for reading from any type of transport.

    This function abstracts `recv()` vs `read()` calls regardless of transport type.

    @param transport The transport to read from.
    @param size_bytes The maximum number of bytes to read.

    @return A `bytes` array.
    '''
    try:
        if isinstance(transport, (SocketTransport, WebsocketTransport)):
            return transport.recv(size_bytes)
        else:
            return transport.read(size_bytes)
    except (socket.timeout, TimeoutError):
        return bytes()


def set_read_timeout(transport: TransportClass, timeout_sec: float):
    if isinstance(transport, SocketTransport):
        if timeout_sec == 0:
            transport.setblocking(False)
        else:
            transport.setblocking(True)
            transport.settimeout(timeout_sec)
    elif isinstance(transport, WebsocketTransport):
        transport.set_timeout(timeout_sec)
    elif isinstance(transport, serial.Serial):
        transport.timeout = timeout_sec
    else:
        # Read timeout not applicable for files.
        pass
