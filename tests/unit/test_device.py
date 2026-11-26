from __future__ import annotations

import logging

import pytest

from elm327 import (
    ELM327,
    ELMTimeoutError,
    NoDataError,
    ResponseError,
    Settings,
    TransportError,
    UnsupportedCommandError,
)
from elm327.transport import LoopbackTransport
from emulator.fake_elm import FakeELM327

# ------------------------------------------------------------------ connect


def test_connect_resets_and_applies_default_settings(fake: FakeELM327) -> None:
    with ELM327(fake.transport) as elm:
        assert elm.is_connected
        assert elm.banner == "ELM327 v1.5"
        assert elm.version == "1.5"
        assert elm.settings == Settings()
    assert fake.received == ["ATI", "ATZ", "ATE0", "ATL0", "ATS0", "ATH0"]
    assert (fake.state.echo, fake.state.linefeeds, fake.state.spaces, fake.state.headers) == (
        False,
        False,
        False,
        False,
    )


def test_connect_applies_requested_settings(fake: FakeELM327) -> None:
    requested = Settings(spaces=True, headers=True)
    with ELM327(fake.transport, settings=requested) as elm:
        assert elm.settings == requested
    assert fake.state.spaces
    assert fake.state.headers


def test_connect_stops_an_adapter_left_monitoring(fake: FakeELM327) -> None:
    fake.monitoring = True
    with ELM327(fake.transport) as elm:
        assert elm.version == "1.5"
    assert not fake.monitoring


def test_connect_to_silent_adapter_times_out_and_closes_transport(fake: FakeELM327) -> None:
    fake.silent = True
    elm = ELM327(fake.transport)
    with pytest.raises(ELMTimeoutError, match="check the port and baud rate"):
        elm.connect()
    assert not elm.is_connected
    assert not fake.transport.is_open


def test_connect_failure_during_setup_closes_transport(fake: FakeELM327) -> None:
    fake.replies["ATS0"] = ["?"]
    elm = ELM327(fake.transport)
    with pytest.raises(UnsupportedCommandError):
        elm.connect()
    assert not fake.transport.is_open


def test_open_builds_transport_from_url() -> None:
    # pyserial's loop:// echoes our own bytes back: never an ELM prompt, so connecting times out.
    with pytest.raises(ELMTimeoutError):
        ELM327.open("loop://", timeout=0.05)


def test_close_is_idempotent(elm: ELM327) -> None:
    elm.close()
    elm.close()
    assert not elm.is_connected


def test_context_manager_does_not_reconnect_a_connected_device(fake: FakeELM327) -> None:
    elm = ELM327(fake.transport)
    elm.connect()
    count = len(fake.received)
    with elm:
        pass
    assert len(fake.received) == count
    assert not elm.is_connected


def test_connect_logs_at_info(fake: FakeELM327, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="elm327"), ELM327(fake.transport):
        pass
    assert "Connected to" in caplog.text
    assert "Disconnecting from" in caplog.text


# ------------------------------------------------------------------ send


def test_send_returns_reply_lines(fake: FakeELM327, elm: ELM327) -> None:
    fake.replies["0100"] = ["41 00 BE 3E B8 13"]
    assert elm.send("01 00") == ["41 00 BE 3E B8 13"]


def test_send_raises_on_error_reply(elm: ELM327) -> None:
    with pytest.raises(NoDataError) as info:
        elm.send("0100")
    assert info.value.command == "0100"


def test_send_raises_on_unknown_command(elm: ELM327) -> None:
    with pytest.raises(UnsupportedCommandError):
        elm.send("ATXYZ")


def test_send_discards_stale_input(fake: FakeELM327, elm: ELM327) -> None:
    fake.transport.feed(b"leftover\r>")
    assert elm.send("ATI") == ["ELM327 v1.5"]


def test_send_ignores_bytes_after_prompt(fake: FakeELM327, elm: ELM327) -> None:
    fake.replies["ATI"] = ["ELM327 v1.5\r\r>extra"]
    assert elm.send("ATI") == ["ELM327 v1.5"]


def test_send_times_out_with_partial_data(fake: FakeELM327, elm: ELM327) -> None:
    fake.silent = True
    fake.transport.feed(b"41 00")
    with pytest.raises(ELMTimeoutError) as info:
        elm.send("0100", timeout=0.05)
    assert info.value.command == "0100"


def test_send_validates_before_sending(fake: FakeELM327, elm: ELM327) -> None:
    count = len(fake.received)
    with pytest.raises(ValueError, match="empty"):
        elm.send("")
    with pytest.raises(ValueError, match="timeout"):
        elm.send("ATI", timeout=0)
    assert len(fake.received) == count


def test_send_requires_connection(fake: FakeELM327) -> None:
    with pytest.raises(TransportError, match="not connected"):
        ELM327(fake.transport).send("ATI")


def test_send_logs_tx_and_rx_at_debug(elm: ELM327, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="elm327"):
        elm.send("ATI")
    assert "TX: 'ATI'" in caplog.text
    assert "RX: ['ELM327 v1.5']" in caplog.text


# ------------------------------------------------------------------ configuration


@pytest.mark.parametrize("name", ["echo", "linefeeds", "spaces", "headers"])
def test_setters_update_adapter_and_tracked_settings(
    fake: FakeELM327, elm: ELM327, name: str
) -> None:
    getattr(elm, f"set_{name}")(True)
    assert getattr(elm.settings, name) is True
    assert getattr(fake.state, name) is True
    getattr(elm, f"set_{name}")(False)
    assert getattr(elm.settings, name) is False
    assert getattr(fake.state, name) is False


def test_replies_parse_with_echo_and_linefeeds_on(fake: FakeELM327, elm: ELM327) -> None:
    elm.configure(Settings(echo=True, linefeeds=True, spaces=True, headers=True))
    fake.replies["0100"] = ["7E8 06 41 00 BE 3E B8 13"]
    assert elm.send("0100") == ["7E8 06 41 00 BE 3E B8 13"]


def test_setter_rejects_unexpected_reply(fake: FakeELM327, elm: ELM327) -> None:
    fake.replies["ATH1"] = ["WHAT"]
    with pytest.raises(ResponseError):
        elm.set_headers(True)
    assert elm.settings.headers is False


def test_reset_returns_banner_and_restores_power_on_settings(
    fake: FakeELM327, elm: ELM327
) -> None:
    assert elm.reset() == "ELM327 v1.5"
    assert elm.settings.echo is True
    assert fake.state.echo is True


def test_warm_start(fake: FakeELM327, elm: ELM327) -> None:
    fake.version = "v2.1"
    assert elm.warm_start() == "ELM327 v2.1"
    assert elm.version == "2.1"
    assert fake.received[-1] == "ATWS"


def test_reset_with_unrecognised_banner_warns(
    fake: FakeELM327, elm: ELM327, caplog: pytest.LogCaptureFixture
) -> None:
    fake.replies["ATZ"] = ["OBDLink MX"]
    with caplog.at_level(logging.WARNING, logger="elm327"):
        assert elm.reset() == "OBDLink MX"
    assert elm.version is None
    assert "Unrecognised reply" in caplog.text


# ------------------------------------------------------------------ information


def test_identify(elm: ELM327) -> None:
    assert elm.identify() == "ELM327 v1.5"


def test_describe(elm: ELM327) -> None:
    assert elm.describe() == "OBDII to RS232 Interpreter"


def test_describe_unsupported_on_clone(fake: FakeELM327, elm: ELM327) -> None:
    fake.supports_describe = False
    with pytest.raises(UnsupportedCommandError):
        elm.describe()


def test_read_voltage(fake: FakeELM327, elm: ELM327) -> None:
    fake.voltage = 13.84
    assert elm.read_voltage() == pytest.approx(13.8)


@pytest.mark.parametrize("reply", [["n/a"], ["12.1V", "12.2V"], []])
def test_read_voltage_rejects_malformed_reply(
    fake: FakeELM327, elm: ELM327, reply: list[str]
) -> None:
    fake.replies["ATRV"] = reply
    with pytest.raises(ResponseError):
        elm.read_voltage()


# ------------------------------------------------------------------ misc


def test_timeout_property_validates() -> None:
    elm = ELM327(LoopbackTransport(), timeout=1)
    assert elm.timeout == 1.0
    with pytest.raises(ValueError, match="timeout"):
        elm.timeout = -1


def test_repr_and_transport(fake: FakeELM327, elm: ELM327) -> None:
    assert elm.transport is fake.transport
    assert "ELM327 v1.5 connected" in repr(elm)
