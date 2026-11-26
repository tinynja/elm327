from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import pytest

from elm327.exceptions import TransportError
from elm327.transport import (
    DEFAULT_BAUDRATE,
    DEFAULT_TCP_PORT,
    LoopbackTransport,
    SerialTransport,
    TcpTransport,
    open_transport,
)

# ------------------------------------------------------------------ loopback


def test_loopback_passes_writes_to_callback() -> None:
    written: list[bytes] = []
    with LoopbackTransport(on_write=written.append) as transport:
        transport.write(b"ATZ\r")
    assert written == [b"ATZ\r"]


def test_loopback_returns_fed_bytes_up_to_size() -> None:
    with LoopbackTransport() as transport:
        transport.feed(b"OK\r\r>")
        assert transport.read(2, 0) == b"OK"
        assert transport.read(100, 0) == b"\r\r>"


def test_loopback_read_returns_empty_on_timeout() -> None:
    with LoopbackTransport() as transport:
        started = time.monotonic()
        assert transport.read(10, 0.05) == b""
        assert time.monotonic() - started >= 0.04


def test_loopback_reset_input_buffer_discards_pending_bytes() -> None:
    with LoopbackTransport() as transport:
        transport.feed(b"stale")
        assert transport.reset_input_buffer() == b"stale"
        assert transport.read(10, 0) == b""


def test_loopback_close_wakes_blocked_reader() -> None:
    transport = LoopbackTransport()
    transport.open()
    errors: list[Exception] = []

    def reader() -> None:
        try:
            transport.read(10, 5.0)
        except TransportError as exc:
            errors.append(exc)

    thread = threading.Thread(target=reader)
    thread.start()
    time.sleep(0.02)
    transport.close()
    thread.join(timeout=1.0)
    assert not thread.is_alive()
    assert len(errors) == 1


def test_loopback_rejects_io_when_closed() -> None:
    transport = LoopbackTransport()
    with pytest.raises(TransportError):
        transport.write(b"x")
    with pytest.raises(TransportError):
        transport.read(1, 0)


def test_loopback_rejects_non_positive_size() -> None:
    with LoopbackTransport() as transport, pytest.raises(ValueError, match="size"):
        transport.read(0, 0)


# ------------------------------------------------------------------ serial (pyserial loop://)


def test_serial_round_trip_over_pyserial_loop() -> None:
    with SerialTransport("loop://") as transport:
        assert transport.is_open
        transport.write(b"ATI\r")
        assert transport.read(100, 1.0) == b"ATI\r"
        assert transport.read(100, 0.01) == b""
    assert not transport.is_open


def test_serial_close_is_idempotent() -> None:
    transport = SerialTransport("loop://")
    transport.open()
    transport.open()  # already open: no-op
    transport.close()
    transport.close()
    assert not transport.is_open


def test_serial_open_failure_raises_transport_error() -> None:
    with pytest.raises(TransportError, match="cannot open serial port"):
        SerialTransport("/dev/does-not-exist-elm327").open()


def test_serial_io_when_closed_raises() -> None:
    transport = SerialTransport("loop://")
    with pytest.raises(TransportError, match="not open"):
        transport.write(b"x")
    with pytest.raises(TransportError, match="not open"):
        transport.read(1, 0)


@pytest.mark.parametrize(
    ("kwargs", "match"), [({"baudrate": 0}, "baudrate"), ({"write_timeout": 0}, "write_timeout")]
)
def test_serial_validates_arguments(kwargs: dict[str, int], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SerialTransport("loop://", **kwargs)


def test_serial_repr_shows_state() -> None:
    assert (
        repr(SerialTransport("COM3", baudrate=115200))
        == "<SerialTransport 'COM3' 115200 bit/s closed>"
    )


# ------------------------------------------------------------------ tcp


@pytest.fixture
def echo_server() -> Iterator[tuple[str, int]]:
    """A one-connection TCP server that echoes everything back, then closes."""
    server = socket.create_server(("127.0.0.1", 0))
    host, port = server.getsockname()[:2]

    def serve() -> None:
        conn, _ = server.accept()
        with conn:
            while data := conn.recv(1024):
                conn.sendall(data)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield host, port
    server.close()
    thread.join(timeout=1.0)


def test_tcp_round_trip(echo_server: tuple[str, int]) -> None:
    host, port = echo_server
    with TcpTransport(host, port) as transport:
        transport.write(b"ATZ\r")
        assert transport.read(100, 1.0) == b"ATZ\r"
        assert transport.read(100, 0) == b""
        assert transport.read(100, 0.01) == b""


def test_tcp_raises_when_peer_closes() -> None:
    server = socket.create_server(("127.0.0.1", 0))
    host, port = server.getsockname()[:2]
    transport = TcpTransport(host, port)
    transport.open()
    conn, _ = server.accept()
    conn.close()
    server.close()
    with pytest.raises(TransportError, match="closed by"):
        transport.read(10, 1.0)
    transport.close()


def test_tcp_connect_failure_raises_transport_error() -> None:
    with socket.create_server(("127.0.0.1", 0)) as probe:
        port = probe.getsockname()[1]
    # The port is now closed, so the connection is refused.
    with pytest.raises(TransportError, match="cannot connect"):
        TcpTransport("127.0.0.1", port, connect_timeout=1.0).open()


def test_tcp_io_when_closed_raises() -> None:
    transport = TcpTransport("127.0.0.1")
    with pytest.raises(TransportError, match="not open"):
        transport.write(b"x")
    with pytest.raises(TransportError, match="not open"):
        transport.read(1, 0)
    transport.close()  # no-op


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"port": 0}, "port"),
        ({"port": 70000}, "port"),
        ({"connect_timeout": 0}, "connect_timeout"),
    ],
)
def test_tcp_validates_arguments(kwargs: dict[str, int], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        TcpTransport("localhost", **kwargs)


# ------------------------------------------------------------------ open_transport


def test_open_transport_tcp_with_default_port() -> None:
    transport = open_transport("tcp://192.168.0.10")
    assert isinstance(transport, TcpTransport)
    assert (transport.host, transport.port) == ("192.168.0.10", DEFAULT_TCP_PORT)


def test_open_transport_tcp_with_explicit_port() -> None:
    transport = open_transport("tcp://adapter.local:23")
    assert isinstance(transport, TcpTransport)
    assert (transport.host, transport.port) == ("adapter.local", 23)


@pytest.mark.parametrize(
    ("url", "port", "baudrate"),
    [
        ("/dev/ttyUSB0", "/dev/ttyUSB0", DEFAULT_BAUDRATE),
        ("COM3", "COM3", DEFAULT_BAUDRATE),
        ("serial:///dev/rfcomm0", "/dev/rfcomm0", DEFAULT_BAUDRATE),
        ("serial:///dev/ttyUSB0?baudrate=115200", "/dev/ttyUSB0", 115200),
        ("serial://COM4?baudrate=9600", "COM4", 9600),
        ("rfc2217://10.0.0.5:4000", "rfc2217://10.0.0.5:4000", DEFAULT_BAUDRATE),
    ],
)
def test_open_transport_serial_forms(url: str, port: str, baudrate: int) -> None:
    transport = open_transport(url)
    assert isinstance(transport, SerialTransport)
    assert (transport.port, transport.baudrate) == (port, baudrate)


def test_open_transport_baudrate_argument_applies_without_query() -> None:
    transport = open_transport("/dev/ttyUSB0", baudrate=500000)
    assert isinstance(transport, SerialTransport)
    assert transport.baudrate == 500000


@pytest.mark.parametrize(
    "url",
    [
        "",
        "tcp://",
        "tcp://host:notaport",
        "serial://",
        "serial:///dev/x?baudrate=fast",
        "serial:///dev/x?baudrate",
    ],
)
def test_open_transport_rejects_malformed_urls(url: str) -> None:
    with pytest.raises(ValueError, match=r"empty|missing|invalid"):
        open_transport(url)
