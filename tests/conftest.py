"""Shared pytest configuration."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Adapter URL for hardware tests, e.g. /dev/ttyUSB0, COM3 or tcp://192.168.0.10:35000",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--port"):
        return
    skip_hardware = pytest.mark.skip(reason="hardware test: pass --port=<url> to run")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hardware)
