"""In-memory transport, for tests and emulators."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from elm327.exceptions import TransportError
from elm327.transport._base import Transport

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["LoopbackTransport"]


class LoopbackTransport(Transport):
    """A transport whose other end is Python code.

    Bytes written by the host are passed to ``on_write``. Bytes given to
    [`feed()`][elm327.transport.LoopbackTransport.feed] become readable by the host. This lets an
    emulator stand in for a real adapter.
    """

    def __init__(self, on_write: Callable[[bytes], None] | None = None) -> None:
        """Create a closed loopback transport.

        Args:
            on_write: Called with every chunk the host writes. It may call
                [`feed()`][elm327.transport.LoopbackTransport.feed].
        """
        self._on_write = on_write
        self._rx = bytearray()
        self._cond = threading.Condition()
        self._open = False

    @property
    def is_open(self) -> bool:
        """Whether the transport is open."""
        return self._open

    def open(self) -> None:
        """Open the transport."""
        with self._cond:
            self._open = True

    def close(self) -> None:
        """Close the transport and wake up any blocked reader."""
        with self._cond:
            self._open = False
            self._cond.notify_all()

    def feed(self, data: bytes) -> None:
        """Make ``data`` available to the host, as if the adapter had sent it."""
        with self._cond:
            self._rx += data
            self._cond.notify_all()

    def write(self, data: bytes) -> None:
        """Hand ``data`` to ``on_write``.

        Raises:
            TransportError: If the transport is closed.
        """
        if not self._open:
            raise TransportError("loopback transport is not open")
        if self._on_write is not None:
            self._on_write(bytes(data))

    def read(self, size: int, timeout: float) -> bytes:
        """Read up to ``size`` fed bytes, waiting at most ``timeout`` s for the first one.

        Raises:
            TransportError: If the transport is closed.
        """
        if size <= 0:
            raise ValueError(f"size must be positive, got {size}")
        with self._cond:
            self._cond.wait_for(lambda: self._rx or not self._open, max(timeout, 0.0))
            if not self._open:
                raise TransportError("loopback transport is not open")
            data = bytes(self._rx[:size])
            del self._rx[:size]
            return data
