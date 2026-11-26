"""TCP transport for Wi-Fi adapters."""

from __future__ import annotations

import logging
import socket
from typing import Final

from elm327.exceptions import TransportError
from elm327.transport._base import Transport

__all__ = ["DEFAULT_TCP_PORT", "TcpTransport"]

logger = logging.getLogger(__name__)

DEFAULT_TCP_PORT: Final = 35000
"""Port used by nearly all Wi-Fi ELM327 adapters (usually at ``192.168.0.10``)."""


class TcpTransport(Transport):
    """Transport over a raw TCP connection."""

    def __init__(
        self, host: str, port: int = DEFAULT_TCP_PORT, *, connect_timeout: float = 5.0
    ) -> None:
        """Create a closed TCP transport.

        Args:
            host: Host name or IP address of the adapter.
            port: TCP port of the adapter.
            connect_timeout: Maximum time to establish the connection, in seconds.

        Raises:
            ValueError: If ``port`` is out of range or ``connect_timeout`` is not positive.
        """
        if not 0 < port < 65536:  # noqa: PLR2004  TCP port range
            raise ValueError(f"port must be in 1..65535, got {port}")
        if connect_timeout <= 0:
            raise ValueError(f"connect_timeout must be positive, got {connect_timeout}")
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self._socket: socket.socket | None = None

    @property
    def is_open(self) -> bool:
        """Whether the connection is open."""
        return self._socket is not None

    def open(self) -> None:
        """Connect to the adapter.

        Raises:
            TransportError: If the connection cannot be established.
        """
        if self._socket is not None:
            return
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        except OSError as exc:
            raise TransportError(f"cannot connect to {self.host}:{self.port}: {exc}") from exc
        # Commands are tiny; without TCP_NODELAY, Nagle's algorithm adds latency to each one.
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket = sock
        logger.info("Connected to %s:%d", self.host, self.port)

    def close(self) -> None:
        """Close the connection. Does nothing if it is already closed."""
        if self._socket is None:
            return
        sock, self._socket = self._socket, None
        sock.close()
        logger.info("Disconnected from %s:%d", self.host, self.port)

    def write(self, data: bytes) -> None:
        """Write all of ``data``.

        Raises:
            TransportError: If the connection is closed or the write fails.
        """
        sock = self._require_open()
        try:
            sock.settimeout(self.connect_timeout)
            sock.sendall(data)
        except OSError as exc:
            raise TransportError(f"write to {self.host}:{self.port} failed: {exc}") from exc

    def read(self, size: int, timeout: float) -> bytes:
        """Read up to ``size`` available bytes, waiting at most ``timeout`` s for the first one.

        Raises:
            TransportError: If the connection is closed, reset or closed by the adapter.
        """
        if size <= 0:
            raise ValueError(f"size must be positive, got {size}")
        sock = self._require_open()
        try:
            sock.settimeout(max(timeout, 0.0))
            data = sock.recv(size)
        except (TimeoutError, BlockingIOError):
            return b""
        except OSError as exc:
            raise TransportError(f"read from {self.host}:{self.port} failed: {exc}") from exc
        if not data:
            raise TransportError(f"connection closed by {self.host}:{self.port}")
        return data

    def _require_open(self) -> socket.socket:
        if self._socket is None:
            raise TransportError(f"connection to {self.host}:{self.port} is not open")
        return self._socket

    def __repr__(self) -> str:
        """Return a debugging representation."""
        state = "open" if self.is_open else "closed"
        return f"<TcpTransport {self.host}:{self.port} {state}>"
