"""Byte transports to ELM327 adapters: serial, TCP and in-memory loopback."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from elm327.transport._base import Transport
from elm327.transport._loopback import LoopbackTransport
from elm327.transport._serial import DEFAULT_BAUDRATE, SerialTransport
from elm327.transport._tcp import DEFAULT_TCP_PORT, TcpTransport

__all__ = [
    "DEFAULT_BAUDRATE",
    "DEFAULT_TCP_PORT",
    "LoopbackTransport",
    "SerialTransport",
    "TcpTransport",
    "Transport",
    "open_transport",
]

_SERIAL_SCHEME = "serial://"
_TCP_SCHEME = "tcp://"


def open_transport(url: str, *, baudrate: int = DEFAULT_BAUDRATE) -> Transport:
    """Create a (closed) transport from a connection URL.

    Accepted forms:

    * ``tcp://host[:port]``: Wi-Fi adapter, port defaults to 35000.
    * ``serial://<port>[?baudrate=N]``: serial port, e.g. ``serial:///dev/ttyUSB0?baudrate=115200``.
    * Anything else is passed to pyserial as-is: ``/dev/ttyUSB0``, ``COM3``, ``rfc2217://...``.

    Args:
        url: The connection URL.
        baudrate: UART speed for serial ports. A ``baudrate`` query parameter takes precedence.

    Returns:
        A transport that still has to be opened.

    Raises:
        ValueError: If the URL is malformed.

    Example:
        >>> open_transport("tcp://192.168.0.10")
        <TcpTransport 192.168.0.10:35000 closed>
    """
    if not url:
        raise ValueError("connection URL must not be empty")

    if url.startswith(_TCP_SCHEME):
        parts = urlsplit(url)
        if not parts.hostname:
            raise ValueError(f"missing host in {url!r}")
        try:
            port = parts.port or DEFAULT_TCP_PORT
        except ValueError as exc:
            raise ValueError(f"invalid port in {url!r}") from exc
        return TcpTransport(parts.hostname, port)

    if url.startswith(_SERIAL_SCHEME):
        port_name, _, query = url[len(_SERIAL_SCHEME) :].partition("?")
        if not port_name:
            raise ValueError(f"missing serial port in {url!r}")
        try:
            params = parse_qs(query, strict_parsing=bool(query))
        except ValueError as exc:
            raise ValueError(f"invalid query in {url!r}") from exc
        if "baudrate" in params:
            try:
                baudrate = int(params["baudrate"][-1])
            except ValueError as exc:
                raise ValueError(f"invalid baudrate in {url!r}") from exc
        return SerialTransport(port_name, baudrate=baudrate)

    return SerialTransport(url, baudrate=baudrate)
