"""Print basic information about an adapter.

Usage:
    python examples/adapter_info.py /dev/ttyUSB0
    python examples/adapter_info.py tcp://192.168.0.10:35000
"""

from __future__ import annotations

import logging
import sys

from elm327 import ELM327, UnsupportedCommandError


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARNING)

    with ELM327.open(url) as elm:
        print(f"Banner:  {elm.banner}")
        print(f"Version: {elm.version}")
        try:
            print(f"Device:  {elm.describe()}")
        except UnsupportedCommandError:
            print("Device:  (AT@1 not supported)")
        print(f"Voltage: {elm.read_voltage():.1f} V")


if __name__ == "__main__":
    main()
