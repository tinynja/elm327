"""Exceptions raised by the elm327 package.

Every exception derives from :class:`ELM327Error`, so callers can catch the whole family with a
single ``except`` clause. Error *replies* from the adapter (``NO DATA``, ``?``, ``BUFFER FULL`` ...)
are :class:`ResponseError` subclasses and carry the command that was sent and the raw reply.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "BufferFullError",
    "BusError",
    "CanBusError",
    "ELM327Error",
    "ELMTimeoutError",
    "NoDataError",
    "ResponseError",
    "StoppedError",
    "TransportError",
    "UnsupportedCommandError",
]


class ELM327Error(Exception):
    """Base class for all errors raised by this package."""


class TransportError(ELM327Error):
    """The connection to the adapter failed, is not open or was closed by the other side."""


class ELMTimeoutError(ELM327Error, TimeoutError):
    """The adapter did not finish its reply in time.

    Also a :class:`TimeoutError`, so generic timeout handling keeps working.

    Attributes:
        command: The command that was waiting for a reply, if any.
        received: The raw bytes received before the deadline expired.
    """

    def __init__(self, message: str, *, command: str | None = None, received: bytes = b"") -> None:
        """Create the error.

        Args:
            message: Human-readable description.
            command: The command that was waiting for a reply, if any.
            received: The raw bytes received before the deadline expired.
        """
        super().__init__(message)
        self.command = command
        self.received = received


class ResponseError(ELM327Error):
    """The adapter replied with an error message.

    Attributes:
        command: The command that was sent.
        response: The reply lines, with echo and prompt removed.
    """

    def __init__(self, command: str, response: Sequence[str]) -> None:
        """Create the error.

        Args:
            command: The command that was sent.
            response: The reply lines, with echo and prompt removed.
        """
        self.command = command
        self.response: tuple[str, ...] = tuple(response)
        reply = " | ".join(self.response) if self.response else "<empty>"
        super().__init__(f"{command!r} failed: {reply}")


class UnsupportedCommandError(ResponseError):
    """The adapter answered ``?``: the command is unknown, malformed or not supported by this chip."""


class NoDataError(ResponseError):
    """The adapter answered ``NO DATA``: nothing was received on the bus before its timeout."""


class BufferFullError(ResponseError):
    """The adapter's internal buffer overflowed (``BUFFER FULL``).

    Usually means the serial link is slower than the bus traffic. Raise the baud rate, disable
    spaces (``ATS0``) or filter the traffic.
    """


class CanBusError(ResponseError):
    """The CAN controller reported a problem (``CAN ERROR``): wrong bit rate, no ACK or a wiring fault."""


class BusError(ResponseError):
    """A non-CAN bus or protocol problem (``BUS ERROR``, ``BUS INIT: ...ERROR``, ``UNABLE TO CONNECT`` ...)."""


class StoppedError(ResponseError):
    """The operation was interrupted by a character received from the host (``STOPPED``)."""
