"""Output-format settings of the adapter."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["POWER_ON_SETTINGS", "Settings"]


@dataclass(frozen=True, slots=True)
class Settings:
    """How the adapter formats its replies.

    The defaults are what :class:`~elm327.ELM327` applies after connecting. They are chosen for
    throughput and easy parsing, not to match the chip's power-on defaults.

    Attributes:
        echo: Echo received characters back (``ATE``). Off halves the traffic.
        linefeeds: End lines with CR LF instead of CR (``ATL``).
        spaces: Separate hex bytes with spaces (``ATS``). Off saves about a third of the
            bandwidth, which matters when monitoring a busy bus.
        headers: Include headers / CAN identifiers in replies (``ATH``).
    """

    echo: bool = False
    linefeeds: bool = False
    spaces: bool = False
    headers: bool = False


POWER_ON_SETTINGS = Settings(echo=True, linefeeds=True, spaces=True, headers=False)
"""What a genuine ELM327 uses after ``ATZ``. Linefeeds actually depend on pin 7, usually high."""
