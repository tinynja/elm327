"""Shared pytest configuration."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import elm327.device
from elm327 import ELM327
from emulator.fake_elm import FakeELM327


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


@pytest.fixture
def fake() -> FakeELM327:
    """A fresh emulated adapter."""
    return FakeELM327()


@pytest.fixture
def elm(fake: FakeELM327) -> Iterator[ELM327]:
    """A driver connected to :func:`fake`."""
    with ELM327(fake.transport, timeout=0.5) as device:
        yield device


@pytest.fixture(autouse=True)
def fast_sync(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink the synchronisation delays, which exist for real hardware only."""
    if "hardware" in request.keywords:
        return
    monkeypatch.setattr(elm327.device, "_SYNC_TIMEOUT", 0.02)
    monkeypatch.setattr(elm327.device, "_SYNC_SETTLE", 0.0)
