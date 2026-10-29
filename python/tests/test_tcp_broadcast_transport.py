import socket
import time

import pytest

from fusion_engine_client.utils.transport_utils import TCPBroadcastServerTransport, create_transport


def _free_port():
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def _wait_for_clients(transport, count, timeout_sec=2.0):
    end = time.time() + timeout_sec
    while transport.num_clients != count and time.time() < end:
        time.sleep(0.01)
    assert transport.num_clients == count


def _connect(port):
    client = socket.create_connection(('127.0.0.1', port), timeout=2.0)
    return client


@pytest.fixture
def transport():
    port = _free_port()
    t = create_transport(f'tcp://:{port}', mode='output')
    assert isinstance(t, TCPBroadcastServerTransport)
    t.port = port
    yield t
    t.close()


def test_send_without_clients_is_dropped(transport):
    assert transport.send(b'abc') == 0


def test_all_clients_receive(transport):
    clients = [_connect(transport.port) for _ in range(3)]
    _wait_for_clients(transport, 3)
    transport.send(b'hello')
    for c in clients:
        assert c.recv(16) == b'hello'
        c.close()


def test_clients_come_and_go(transport):
    a = _connect(transport.port)
    _wait_for_clients(transport, 1)
    transport.send(b'1')
    assert a.recv(16) == b'1'

    b = _connect(transport.port)
    _wait_for_clients(transport, 2)
    a.close()
    # The disconnect is detected on a subsequent send.
    for _ in range(5):
        transport.send(b'2')
        time.sleep(0.05)
    _wait_for_clients(transport, 1)
    assert b.recv(16).startswith(b'2')
    b.close()


def test_input_mode_still_single_client():
    port = _free_port()
    t = create_transport(f'tcp://:{port}', mode='input')
    try:
        assert not isinstance(t, TCPBroadcastServerTransport)
    finally:
        t.close()
