"""Connect to, configure and communicate with ELM327 OBD-II/CAN adapters.

Examples:
    >>> from elm327 import ELM327
    >>> with ELM327.open("/dev/ttyUSB0") as elm:  # doctest: +SKIP
    ...     elm.read_voltage()
    12.6
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from elm327.device import DEFAULT_TIMEOUT, ELM327, RESET_TIMEOUT
from elm327.exceptions import (
    BufferFullError,
    BusError,
    CanBusError,
    ELM327Error,
    ELMTimeoutError,
    NoDataError,
    ResponseError,
    StoppedError,
    TransportError,
    UnsupportedCommandError,
)
from elm327.settings import Settings

try:
    __version__ = version("elm327")
except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled tree
    __version__ = "0.0.0"

__all__ = [
    "DEFAULT_TIMEOUT",
    "ELM327",
    "RESET_TIMEOUT",
    "BufferFullError",
    "BusError",
    "CanBusError",
    "ELM327Error",
    "ELMTimeoutError",
    "NoDataError",
    "ResponseError",
    "Settings",
    "StoppedError",
    "TransportError",
    "UnsupportedCommandError",
    "__version__",
]
