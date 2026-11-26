from __future__ import annotations

import pytest

from elm327 import _commands


@pytest.mark.parametrize(
    ("builder", "code"),
    [
        (_commands.echo, "E"),
        (_commands.linefeeds, "L"),
        (_commands.spaces, "S"),
        (_commands.headers, "H"),
    ],
)
def test_switch_builders(builder: object, code: str) -> None:
    assert callable(builder)
    assert builder(True) == f"AT{code}1"
    assert builder(False) == f"AT{code}0"


def test_validate_strips_whitespace() -> None:
    assert _commands.validate("  ATZ \n") == "ATZ"


def test_validate_keeps_inner_spaces() -> None:
    assert _commands.validate("01 00") == "01 00"


@pytest.mark.parametrize("command", ["", "   ", "\r"])
def test_validate_rejects_empty_command_which_would_repeat_the_last_one(command: str) -> None:
    with pytest.raises(ValueError, match="empty"):
        _commands.validate(command)


@pytest.mark.parametrize("command", ["AT\rZ", "AT\x00Z", "ATZé", "AT\tZ"])
def test_validate_rejects_control_and_non_ascii_characters(command: str) -> None:
    with pytest.raises(ValueError, match="printable ASCII"):
        _commands.validate(command)


def test_validate_rejects_non_strings() -> None:
    with pytest.raises(TypeError, match="must be str"):
        _commands.validate(b"ATZ")  # type: ignore[arg-type]
