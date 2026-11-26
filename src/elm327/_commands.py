"""Builders for the AT commands understood by the ELM327.

All command strings are produced here, so the rest of the package never assembles AT commands
from literals.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "DESCRIBE",
    "IDENTIFY",
    "READ_VOLTAGE",
    "RESET",
    "WARM_START",
    "echo",
    "headers",
    "linefeeds",
    "spaces",
    "validate",
]

RESET: Final = "ATZ"
WARM_START: Final = "ATWS"
IDENTIFY: Final = "ATI"
DESCRIBE: Final = "AT@1"
READ_VOLTAGE: Final = "ATRV"

_PRINTABLE_ASCII = frozenset(range(0x20, 0x7F))


def validate(command: str) -> str:
    """Check that ``command`` can be sent to the adapter and return it stripped.

    Args:
        command: A command without the trailing carriage return.

    Returns:
        The command with surrounding whitespace removed.

    Raises:
        TypeError: If ``command`` is not a string.
        ValueError: If it is empty or contains anything but printable ASCII.
    """
    if not isinstance(command, str):
        raise TypeError(f"command must be str, got {type(command).__name__}")
    stripped = command.strip()
    if not stripped:
        # An empty line makes the ELM327 repeat its previous command, which is never what a
        # caller of send() intends (think of a repeated "clear trouble codes").
        raise ValueError("command must not be empty")
    if not all(ord(char) in _PRINTABLE_ASCII for char in stripped):
        raise ValueError(
            f"command must be printable ASCII without control characters: {command!r}"
        )
    return stripped


def _switch(code: str, enabled: bool) -> str:
    return f"AT{code}{int(enabled)}"


def echo(enabled: bool) -> str:
    """Build ``ATE0``/``ATE1``: whether the adapter echoes received characters."""
    return _switch("E", enabled)


def linefeeds(enabled: bool) -> str:
    """Build ``ATL0``/``ATL1``: whether replies end lines with CR LF instead of CR."""
    return _switch("L", enabled)


def spaces(enabled: bool) -> str:
    """Build ``ATS0``/``ATS1``: whether hex bytes in replies are separated by spaces."""
    return _switch("S", enabled)


def headers(enabled: bool) -> str:
    """Build ``ATH0``/``ATH1``: whether replies include message headers (CAN IDs)."""
    return _switch("H", enabled)
