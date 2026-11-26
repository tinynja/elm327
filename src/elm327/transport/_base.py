"""Abstract byte transport shared by all connection types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

__all__ = ["Transport"]


class Transport(ABC):
    """A bidirectional byte stream to an adapter.

    Implementations only move bytes. They know nothing about AT commands, prompts or encodings.
    """

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Whether the transport is currently open."""

    @abstractmethod
    def open(self) -> None:
        """Open the connection.

        Raises:
            TransportError: If the connection cannot be established.
        """

    @abstractmethod
    def close(self) -> None:
        """Close the connection. Calling it on a closed transport does nothing."""

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Write all of ``data``.

        Raises:
            TransportError: If the transport is closed or the write fails.
        """

    @abstractmethod
    def read(self, size: int, timeout: float) -> bytes:
        """Read up to ``size`` bytes that are available.

        Blocks for at most ``timeout`` seconds waiting for the first byte, then returns whatever is
        immediately available, without waiting further.

        Args:
            size: Maximum number of bytes to return. Must be positive.
            timeout: Maximum time to wait for the first byte, in seconds. ``0`` polls.

        Returns:
            The bytes read, or ``b""`` if nothing arrived before the timeout.

        Raises:
            TransportError: If the transport is closed or the read fails.
        """

    def reset_input_buffer(self) -> bytes:
        """Discard and return any bytes that have already been received.

        Raises:
            TransportError: If the transport is closed or the read fails.
        """
        discarded = bytearray()
        while chunk := self.read(4096, 0):
            discarded += chunk
        return bytes(discarded)

    def __enter__(self) -> Self:
        """Open the transport if needed and return it."""
        if not self.is_open:
            self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the transport."""
        self.close()
