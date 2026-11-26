from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "error_type",
    [
        BufferFullError,
        BusError,
        CanBusError,
        NoDataError,
        StoppedError,
        UnsupportedCommandError,
    ],
)
def test_response_errors_share_the_response_error_base(error_type: type[ResponseError]) -> None:
    error = error_type("0100", ["NO DATA"])
    assert isinstance(error, ResponseError)
    assert isinstance(error, ELM327Error)


def test_response_error_keeps_command_and_reply() -> None:
    error = ResponseError("ATSP6", ["?"])
    assert error.command == "ATSP6"
    assert error.response == ("?",)
    assert str(error) == "'ATSP6' failed: ?"


def test_response_error_message_with_empty_reply() -> None:
    assert str(ResponseError("ATI", [])) == "'ATI' failed: <empty>"


def test_timeout_error_is_also_a_builtin_timeout_error() -> None:
    error = ELMTimeoutError("no prompt", command="ATZ", received=b"ELM")
    assert isinstance(error, TimeoutError)
    assert isinstance(error, ELM327Error)
    assert str(error) == "no prompt"
    assert error.command == "ATZ"
    assert error.received == b"ELM"


def test_transport_error_is_an_elm327_error() -> None:
    assert issubclass(TransportError, ELM327Error)
