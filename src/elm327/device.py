"""The :class:`ELM327` adapter driver."""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from typing import TYPE_CHECKING, Final

from elm327 import _commands
from elm327._responses import PROMPT, check_errors, parse_version, split_lines, strip_echo
from elm327.exceptions import ELMTimeoutError, ResponseError, TransportError
from elm327.settings import POWER_ON_SETTINGS, Settings
from elm327.transport import DEFAULT_BAUDRATE, open_transport

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

    from elm327.transport import Transport

__all__ = ["DEFAULT_TIMEOUT", "ELM327", "RESET_TIMEOUT"]

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final = 2.0
"""Default time to wait for a complete reply, in seconds."""

RESET_TIMEOUT: Final = 5.0
"""Time allowed for ``ATZ``/``ATWS``. Genuine chips need about 1 s, some clones far longer."""

_SYNC_TIMEOUT: Final = 1.0
_SYNC_ATTEMPTS: Final = 3
_SYNC_SETTLE: Final = 0.1
_READ_CHUNK: Final = 4096
_OK: Final = "OK"


class ELM327:
    """Driver for an ELM327 (or compatible) adapter.

    The driver owns the connection and keeps track of the adapter's output format, so replies can
    always be parsed reliably. All methods are thread-safe: one lock serialises access to the
    adapter.

    Example:
        >>> with ELM327.open("/dev/ttyUSB0") as elm:  # doctest: +SKIP
        ...     elm.version
        '1.5'
    """

    def __init__(
        self,
        transport: Transport,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        settings: Settings | None = None,
    ) -> None:
        """Create a driver for ``transport``. Call :meth:`connect` before using it.

        Args:
            transport: The connection to the adapter. It may be open or closed.
            timeout: Default time to wait for a complete reply, in seconds.
            settings: Output format to apply on connect. Defaults to :class:`Settings()`.

        Raises:
            ValueError: If ``timeout`` is not positive.
        """
        self._transport = transport
        self.timeout = timeout
        self._requested = settings if settings is not None else Settings()
        self._settings = POWER_ON_SETTINGS
        self._lock = threading.RLock()
        self._connected = False
        self._banner: str | None = None
        self._version: str | None = None

    @classmethod
    def open(
        cls,
        url: str,
        *,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
        settings: Settings | None = None,
    ) -> Self:
        """Open a connection from a URL and initialise the adapter.

        Args:
            url: A connection URL, see :func:`elm327.transport.open_transport`.
            baudrate: UART speed for serial adapters, in bit/s.
            timeout: Default time to wait for a complete reply, in seconds.
            settings: Output format to apply. Defaults to :class:`Settings()`.

        Returns:
            A connected driver.

        Raises:
            ValueError: If the URL or an argument is invalid.
            TransportError: If the connection cannot be opened.
            ELMTimeoutError: If the adapter does not answer.
        """
        elm = cls(open_transport(url, baudrate=baudrate), timeout=timeout, settings=settings)
        elm.connect()
        return elm

    # ------------------------------------------------------------------ properties

    @property
    def timeout(self) -> float:
        """Default time to wait for a complete reply, in seconds."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._timeout = _check_timeout(value)

    @property
    def transport(self) -> Transport:
        """The underlying transport."""
        return self._transport

    @property
    def is_connected(self) -> bool:
        """Whether :meth:`connect` succeeded and the transport is still open."""
        return self._connected and self._transport.is_open

    @property
    def settings(self) -> Settings:
        """The output format currently configured on the adapter."""
        return self._settings

    @property
    def banner(self) -> str | None:
        """The identification line from the last reset, e.g. ``"ELM327 v1.5"``."""
        return self._banner

    @property
    def version(self) -> str | None:
        """The firmware version reported at reset, e.g. ``"1.5"``, if recognised."""
        return self._version

    # ------------------------------------------------------------------ lifecycle

    def connect(self) -> None:
        """Open the transport, synchronise with the adapter, reset it and apply the settings.

        Synchronising first makes connecting work even if the adapter was left busy, for example
        still monitoring the bus after a previous program crashed.

        Raises:
            TransportError: If the transport cannot be opened.
            ELMTimeoutError: If the adapter does not answer. Check the port and baud rate.
            ResponseError: If the adapter rejects one of the setup commands.
        """
        with self._lock:
            self._transport.open()
            try:
                self._synchronise()
                self._connected = True
                self.reset()
                self.configure(self._requested)
            except BaseException:
                self._connected = False
                self._transport.close()
                raise
            logger.info("Connected to %s (%s)", self._transport, self._banner or "unknown adapter")

    def close(self) -> None:
        """Close the connection. Calling it more than once is harmless."""
        with self._lock:
            if self._connected:
                logger.info("Disconnecting from %s", self._transport)
            self._connected = False
            self._transport.close()

    def __enter__(self) -> Self:
        """Connect if needed and return the driver."""
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the connection."""
        self.close()

    # ------------------------------------------------------------------ commands

    def send(self, command: str, *, timeout: float | None = None) -> list[str]:
        """Send a command and return its reply lines.

        Works for both AT commands and OBD requests. The echo, blank lines, ``SEARCHING...``
        notices and the prompt are removed from the reply.

        Args:
            command: The command, without the trailing carriage return.
            timeout: Time to wait for the complete reply, in seconds. Defaults to
                :attr:`timeout`.

        Returns:
            The reply lines, e.g. ``["OK"]`` or ``["41 00 BE 3E B8 13"]``.

        Raises:
            ValueError: If ``command`` is empty or not printable ASCII.
            TransportError: If not connected or the connection fails.
            ELMTimeoutError: If the reply does not complete in time.
            ResponseError: If the adapter reports an error. The subclass says which one, e.g.
                :class:`~elm327.NoDataError` or :class:`~elm327.UnsupportedCommandError`.
        """
        command = _commands.validate(command)
        wait = self._timeout if timeout is None else _check_timeout(timeout)
        with self._lock:
            if not self.is_connected:
                raise TransportError("not connected to an adapter")
            lines = self._exchange(command, wait)
        check_errors(command, lines)
        return lines

    def reset(self) -> str:
        """Reset the adapter completely (sends ``ATZ``).

        All settings return to their power-on values, so the driver's output format is reset too.
        :meth:`connect` re-applies the requested settings; after calling this directly, use
        :meth:`configure` if needed.

        Returns:
            The identification banner, e.g. ``"ELM327 v1.5"``.
        """
        return self._restart(_commands.RESET)

    def warm_start(self) -> str:
        """Restart the adapter without the LED test, keeping the baud rate (sends ``ATWS``).

        Returns:
            The identification banner, e.g. ``"ELM327 v1.5"``.
        """
        return self._restart(_commands.WARM_START)

    def configure(self, settings: Settings) -> None:
        """Apply an output format.

        Every setting is sent, even ones believed to be in place already, because clones do not
        always start from the documented defaults.

        Raises:
            ResponseError: If the adapter rejects a setting.
        """
        with self._lock:
            self.set_echo(settings.echo)
            self.set_linefeeds(settings.linefeeds)
            self.set_spaces(settings.spaces)
            self.set_headers(settings.headers)

    def set_echo(self, enabled: bool) -> None:
        """Turn the echo of received characters on or off (sends ``ATE0``/``ATE1``)."""
        self._set(_commands.echo(enabled), echo=enabled)

    def set_linefeeds(self, enabled: bool) -> None:
        """Choose CR LF (on) or CR (off) line endings (sends ``ATL0``/``ATL1``)."""
        self._set(_commands.linefeeds(enabled), linefeeds=enabled)

    def set_spaces(self, enabled: bool) -> None:
        """Turn spaces between hex bytes on or off (sends ``ATS0``/``ATS1``)."""
        self._set(_commands.spaces(enabled), spaces=enabled)

    def set_headers(self, enabled: bool) -> None:
        """Turn headers / CAN identifiers in replies on or off (sends ``ATH0``/``ATH1``)."""
        self._set(_commands.headers(enabled), headers=enabled)

    def identify(self) -> str:
        """Return the identification string (sends ``ATI``), e.g. ``"ELM327 v1.5"``."""
        return " ".join(self.send(_commands.IDENTIFY))

    def describe(self) -> str:
        """Return the device description (sends ``AT@1``).

        Genuine chips answer ``"OBDII to RS232 Interpreter"``. Many clones do not support it.

        Raises:
            UnsupportedCommandError: If the adapter does not support the command.
        """
        return " ".join(self.send(_commands.DESCRIBE))

    def read_voltage(self) -> float:
        """Return the voltage at the adapter's supply pin, in volts (sends ``ATRV``).

        On a vehicle this is the battery voltage, measured with about 0.1 V resolution.

        Raises:
            ResponseError: If the reply is not a voltage.
        """
        lines = self.send(_commands.READ_VOLTAGE)
        try:
            (line,) = lines
            return float(line.upper().removesuffix("V"))
        except ValueError as exc:
            raise ResponseError(_commands.READ_VOLTAGE, lines) from exc

    # ------------------------------------------------------------------ internals

    def _set(self, command: str, **change: bool) -> None:
        with self._lock:
            lines = self.send(command)
            if lines != [_OK]:
                raise ResponseError(command, lines)
            self._settings = dataclasses.replace(self._settings, **change)

    def _restart(self, command: str) -> str:
        with self._lock:
            lines = self.send(command, timeout=max(self._timeout, RESET_TIMEOUT))
            self._settings = POWER_ON_SETTINGS
            self._banner = next((line for line in lines if parse_version([line])), None)
            if self._banner is None and lines:
                self._banner = lines[-1]
            self._version = parse_version(lines)
            if self._version is None:
                logger.warning("Unrecognised reply to %s: %r", command, lines)
            return self._banner or ""

    def _exchange(self, command: str, timeout: float) -> list[str]:
        """Send ``command`` and return the reply lines without echo. Caller holds the lock."""
        stale = self._transport.reset_input_buffer()
        if stale:
            logger.debug("Discarded stale input: %r", stale)
        logger.debug("TX: %r", command)
        self._transport.write(command.encode("ascii") + b"\r")
        raw = self._read_until_prompt(timeout, command)
        lines = strip_echo(command, split_lines(raw))
        logger.debug("RX: %r", lines)
        return lines

    def _read_until_prompt(self, timeout: float, command: str | None) -> bytes:
        deadline = time.monotonic() + timeout
        buffer = bytearray()
        while (end := buffer.find(PROMPT)) < 0:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ELMTimeoutError(
                    f"no prompt from the adapter within {timeout:g} s",
                    command=command,
                    received=bytes(buffer),
                )
            buffer += self._transport.read(_READ_CHUNK, remaining)
        if trailing := buffer[end + len(PROMPT) :]:
            logger.debug("Ignored data after prompt: %r", bytes(trailing))
        return bytes(buffer[:end])

    def _synchronise(self) -> None:
        """Bring the adapter to its prompt, whatever state it was left in. Caller holds the lock.

        A harmless ``ATI`` is sent rather than a bare CR: an empty line makes the adapter repeat
        its previous command, which might have been anything. If the adapter was monitoring, the
        first character stops it and the rest becomes a separate (rejected) command, hence the
        settle time and the final flush.
        """
        self._transport.reset_input_buffer()
        for attempt in range(1, _SYNC_ATTEMPTS + 1):
            self._transport.write(_commands.IDENTIFY.encode("ascii") + b"\r")
            try:
                self._read_until_prompt(_SYNC_TIMEOUT, None)
            except ELMTimeoutError:
                logger.debug("No prompt on synchronisation attempt %d", attempt)
                continue
            time.sleep(_SYNC_SETTLE)
            self._transport.reset_input_buffer()
            return
        raise ELMTimeoutError(
            f"adapter did not answer after {_SYNC_ATTEMPTS} attempts; check the port and baud rate"
        )

    def __repr__(self) -> str:
        """Return a debugging representation."""
        state = "connected" if self.is_connected else "disconnected"
        return f"<ELM327 {self._transport!r} {self._banner or 'unknown'} {state}>"


def _check_timeout(value: float) -> float:
    if not value > 0:
        raise ValueError(f"timeout must be positive, got {value}")
    return float(value)
