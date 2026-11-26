"""Smoke tests against a real adapter: ``pytest -m hardware --port=/dev/ttyUSB0``.

They only use read-only commands, so they are safe with the adapter plugged into a vehicle.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from elm327 import ELM327, Settings, UnsupportedCommandError

pytestmark = pytest.mark.hardware


@pytest.fixture(scope="module")
def device(pytestconfig: pytest.Config) -> Iterator[ELM327]:
    url = pytestconfig.getoption("--port")
    assert isinstance(url, str)
    with ELM327.open(url) as elm:
        yield elm


def test_reports_a_version(device: ELM327) -> None:
    assert device.banner
    assert device.version is not None, f"unrecognised banner {device.banner!r}"


def test_identify_matches_banner(device: ELM327) -> None:
    assert device.identify() == device.banner


def test_reads_a_plausible_voltage(device: ELM327) -> None:
    assert 5.0 < device.read_voltage() < 30.0


def test_describe_or_reports_unsupported(device: ELM327) -> None:
    try:
        assert device.describe()
    except UnsupportedCommandError:
        pytest.skip("adapter does not support AT@1 (common on clones)")


def test_settings_round_trip(device: ELM327) -> None:
    device.configure(Settings(echo=True, linefeeds=True, spaces=True, headers=True))
    assert device.identify() == device.banner
    device.configure(Settings())
    assert device.settings == Settings()
