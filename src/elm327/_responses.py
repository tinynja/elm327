"""Decoding and classification of raw adapter replies.

This is the only place where bytes received from the adapter are decoded to text.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from elm327.exceptions import (
    BufferFullError,
    BusError,
    CanBusError,
    NoDataError,
    ResponseError,
    StoppedError,
    UnsupportedCommandError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["PROMPT", "check_errors", "parse_version", "split_lines", "strip_echo"]

PROMPT: Final = b">"
"""Sent by the adapter when it is idle and ready for the next command."""

_LINE_BREAK = re.compile(r"[\r\n]+")
_VERSION = re.compile(r"ELM327\s+v?(\d+\.\d+[A-Za-z]?)", re.IGNORECASE)
_SEARCHING = "SEARCHING..."

# Replies that are an error as a whole line, matched after upper-casing.
_EXACT_ERRORS: Final[dict[str, type[ResponseError]]] = {
    "?": UnsupportedCommandError,
    "NO DATA": NoDataError,
    "BUFFER FULL": BufferFullError,
    "CAN ERROR": CanBusError,
    "STOPPED": StoppedError,
    "BUS BUSY": BusError,
    "BUS ERROR": BusError,
    "DATA ERROR": BusError,
    "FB ERROR": BusError,
    "UNABLE TO CONNECT": BusError,
    "LV RESET": ResponseError,
    "ACT ALERT": ResponseError,
}
# Markers that make a line an error wherever they appear (e.g. "7E8 03 41 0D <DATA ERROR").
_EMBEDDED_ERRORS: Final[dict[str, type[ResponseError]]] = {
    "<DATA ERROR": BusError,
    "<RX ERROR": BusError,
}
_INTERNAL_ERROR = re.compile(r"ERR\d{2}")
_BUS_INIT = "BUS INIT"


def split_lines(raw: bytes) -> list[str]:
    """Decode a reply (prompt already removed) into its non-empty, stripped lines.

    NUL bytes, which some adapters emit after a reset or on a baud rate change, are dropped. Bytes
    that are not ASCII are replaced instead of raising, so line noise cannot crash the parser.
    """
    text = raw.replace(b"\x00", b"").decode("ascii", errors="replace")
    return [line for line in (part.strip() for part in _LINE_BREAK.split(text)) if line]


def _normalise(line: str) -> str:
    return line.replace(" ", "").upper()


def strip_echo(command: str, lines: Sequence[str]) -> list[str]:
    """Remove the echoed command and protocol search notices from a reply.

    The echo is removed whenever the first line matches the command, whatever the adapter's echo
    setting, because right after a reset the echo is on even if the host asked for it to be off.
    """
    result = list(lines)
    if result and _normalise(result[0]) == _normalise(command):
        del result[0]
    return [line for line in result if line.upper() != _SEARCHING]


def check_errors(command: str, lines: Sequence[str]) -> None:
    """Raise the matching error if the reply reports one.

    Raises:
        ResponseError: The most specific subclass for the first error line found.
    """
    for line in lines:
        upper = line.upper()
        error_type = _EXACT_ERRORS.get(upper)
        if error_type is None:
            error_type = next(
                (error for marker, error in _EMBEDDED_ERRORS.items() if marker in upper), None
            )
        if error_type is None and upper.startswith(_BUS_INIT) and "ERROR" in upper:
            # "BUS INIT: ...OK" is success, "BUS INIT: ...ERROR" is not.
            error_type = BusError
        if error_type is None and _INTERNAL_ERROR.fullmatch(upper):
            error_type = ResponseError
        if error_type is not None:
            raise error_type(command, lines)


def parse_version(lines: Sequence[str]) -> str | None:
    """Extract the firmware version from an ``ATZ``/``ATI`` reply.

    Returns:
        The version number (e.g. ``"1.5"`` for ``ELM327 v1.5``), or ``None`` if no line looks like
        an ELM327 identification string.
    """
    for line in lines:
        if match := _VERSION.search(line):
            return match.group(1)
    return None
