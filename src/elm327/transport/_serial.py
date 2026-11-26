"""Serial transport: USB adapters, Bluetooth SPP (``/dev/rfcomm*``, ``COMx``) and pyserial URLs."""

from __future__ import annotations

import logging
from typing import Final

import serial

from elm327.exceptions import TransportError
from elm327.transport._base import Transport

__all__ = ["DEFAULT_BAUDRATE", "SerialTransport"]

logger = logging.getLogger(__name__)

DEFAULT_BAUDRATE: Final = 38400
"""Factory default of a genuine ELM327. Many clones ship at 9600 or 115200 instead."""


class SerialTransport(Transport):
    """Transport over a serial port.

    ``port`` is anything :func:`serial.serial_for_url` accepts: a device path (``/dev/ttyUSB0``),
    a Windows port (``COM3``) or a pyserial URL (``rfc2217://host:port``, ``loop://``).
    """

    def __init__(
        self, port: str, *, baudrate: int = DEFAULT_BAUDRATE, write_timeout: float = 1.0
    ) -> None:
        """Create a closed serial transport.

        Args:
            port: Device path, port name or pyserial URL.
            baudrate: UART speed in bit/s.
            write_timeout: Maximum time a write may block, in seconds.

        Raises:
            ValueError: If ``baudrate`` or ``write_timeout`` is not positive.
        """
        if baudrate <= 0:
            raise ValueError(f"baudrate must be positive, got {baudrate}")
        if write_timeout <= 0:
            raise ValueError(f"write_timeout must be positive, got {write_timeout}")
        self.port = port
        self.baudrate = baudrate
        self.write_timeout = write_timeout
        self._serial: serial.SerialBase | None = None

    @property
    def is_open(self) -> bool:
        """Whether the port is open."""
        return self._serial is not None and self._serial.is_open

    def open(self) -> None:
        """Open the port.

        Raises:
            TransportError: If the port does not exist, is busy or cannot be configured.
        """
        if self.is_open:
            return
        try:
            self._serial = serial.serial_for_url(
                self.port, baudrate=self.baudrate, timeout=0, write_timeout=self.write_timeout
            )
        except (serial.SerialException, ValueError) as exc:
            raise TransportError(f"cannot open serial port {self.port!r}: {exc}") from exc
        logger.info("Opened serial port %s at %d bit/s", self.port, self.baudrate)

    def close(self) -> None:
        """Close the port. Does nothing if it is already closed."""
        if self._serial is None:
            return
        port, self._serial = self._serial, None
        port.close()
        logger.info("Closed serial port %s", self.port)

    def write(self, data: bytes) -> None:
        """Write all of ``data``.

        Raises:
            TransportError: If the port is closed or the write fails or times out.
        """
        port = self._require_open()
        try:
            port.write(data)
            port.flush()
        except serial.SerialException as exc:  # SerialTimeoutException is a subclass
            raise TransportError(f"write to {self.port!r} failed: {exc}") from exc

    def read(self, size: int, timeout: float) -> bytes:
        """Read up to ``size`` available bytes, waiting at most ``timeout`` s for the first one.

        Raises:
            TransportError: If the port is closed or the read fails.
        """
        if size <= 0:
            raise ValueError(f"size must be positive, got {size}")
        port = self._require_open()
        try:
            port.timeout = max(timeout, 0.0)
            first = port.read(1)
            if not first or size == 1:
                return first
            # With timeout 0, pyserial returns only what is already buffered.
            port.timeout = 0
            return first + port.read(size - 1)
        except serial.SerialException as exc:
            raise TransportError(f"read from {self.port!r} failed: {exc}") from exc

    def _require_open(self) -> serial.SerialBase:
        if self._serial is None or not self._serial.is_open:
            raise TransportError(f"serial port {self.port!r} is not open")
        return self._serial

    def __repr__(self) -> str:
        """Return a debugging representation."""
        state = "open" if self.is_open else "closed"
        return f"<SerialTransport {self.port!r} {self.baudrate} bit/s {state}>"
