from __future__ import annotations

import pytest

from elm327._responses import check_errors, parse_version, split_lines, strip_echo
from elm327.exceptions import (
    BufferFullError,
    BusError,
    CanBusError,
    NoDataError,
    ResponseError,
    StoppedError,
    UnsupportedCommandError,
)


def test_split_lines_handles_cr_crlf_and_blank_lines() -> None:
    assert split_lines(b"ATZ\r\r\rELM327 v1.5\r\n\r\n") == ["ATZ", "ELM327 v1.5"]


def test_split_lines_drops_nul_bytes_and_strips_lines() -> None:
    assert split_lines(b"\x00\x00  OK  \r") == ["OK"]


def test_split_lines_survives_non_ascii_noise() -> None:
    assert split_lines(b"\xffOK\r") == ["�OK"]


def test_split_lines_of_empty_reply() -> None:
    assert split_lines(b"") == []


def test_strip_echo_removes_matching_first_line_ignoring_case_and_spaces() -> None:
    assert strip_echo("01 00", ["0100", "41 00 BE 3E B8 13"]) == ["41 00 BE 3E B8 13"]
    assert strip_echo("ate0", ["ATE0", "OK"]) == ["OK"]


def test_strip_echo_keeps_non_matching_first_line() -> None:
    assert strip_echo("ATI", ["ELM327 v1.5"]) == ["ELM327 v1.5"]


def test_strip_echo_removes_searching_notice() -> None:
    assert strip_echo("0100", ["SEARCHING...", "41 00 BE 3E B8 13"]) == ["41 00 BE 3E B8 13"]


@pytest.mark.parametrize(
    ("line", "error_type"),
    [
        ("?", UnsupportedCommandError),
        ("NO DATA", NoDataError),
        ("no data", NoDataError),
        ("BUFFER FULL", BufferFullError),
        ("CAN ERROR", CanBusError),
        ("STOPPED", StoppedError),
        ("BUS BUSY", BusError),
        ("BUS ERROR", BusError),
        ("DATA ERROR", BusError),
        ("FB ERROR", BusError),
        ("UNABLE TO CONNECT", BusError),
        ("BUS INIT: ...ERROR", BusError),
        ("7E8 03 41 0D <DATA ERROR", BusError),
        ("7E8 03 41 <RX ERROR", BusError),
        ("LV RESET", ResponseError),
        ("ACT ALERT", ResponseError),
        ("ERR94", ResponseError),
    ],
)
def test_check_errors_maps_replies_to_exceptions(
    line: str, error_type: type[ResponseError]
) -> None:
    with pytest.raises(error_type) as info:
        check_errors("0100", ["junk", line])
    assert type(info.value) is error_type
    assert info.value.command == "0100"
    assert info.value.response == ("junk", line)


@pytest.mark.parametrize(
    "lines",
    [
        [],
        ["OK"],
        ["41 00 BE 3E B8 13"],
        ["BUS INIT: ...OK", "41 00 BE 3E B8 13"],
        ["ERROR CODE 7"],
        ["ERR9"],
    ],
)
def test_check_errors_accepts_normal_replies(lines: list[str]) -> None:
    check_errors("0100", lines)


@pytest.mark.parametrize(
    ("lines", "version"),
    [
        (["ELM327 v1.5"], "1.5"),
        (["", "ELM327 v2.3"], "2.3"),
        (["elm327 V1.4b"], "1.4b"),
        (["OBDLink SX", "ELM327 v1.3a"], "1.3a"),
        (["STN1110 v4.2.0"], None),
        ([], None),
    ],
)
def test_parse_version(lines: list[str], version: str | None) -> None:
    assert parse_version(lines) == version
