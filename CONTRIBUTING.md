# Contributing

## Setup

```bash
uv sync                      # creates .venv with the dev dependency group
uv run pre-commit install    # format, lint and type-check on every commit
```

## Everyday commands

| Task | Command |
| --- | --- |
| Tests (no hardware) | `uv run pytest` |
| Tests with coverage | `uv run pytest --cov` |
| Hardware tests | `uv run pytest -m hardware --port=/dev/ttyUSB0` (or `--port=tcp://192.168.0.10:35000`) |
| Format | `uv run ruff format` |
| Lint | `uv run ruff check --fix` |
| Type check | `uv run mypy` |
| Docs preview | `uv run --group docs mkdocs serve` |
| Build sdist + wheel | `uv build` |

## Coding conventions

### Formatting and linting
- Ruff formats and lints. Line length is **99**. Long string literals are **not** split to fit; `E501` is disabled and the formatter handles code lines.
- Ignore a rule only inline (`# noqa: XXX  reason`), never file-wide without review.

### Typing
- `mypy --strict` must pass for `src/` and `tests/`.
- Every module starts with `from __future__ import annotations`. Use `X | None`, `list[int]`, `Self`.
- No `Any` in the public API. `Protocol`/ABC for interfaces, `Final` for constants.

### Naming and structure
- PEP 8 naming. No abbreviations beyond domain terms (CAN, OBD, DLC, PID, DTC).
- **Private by default.** Internal modules and helpers start with `_`. The public API is exactly what `elm327/__init__.py` (and `elm327.transport`) list in `__all__`.
- Methods use the device's vocabulary and name the AT command they send in their docstring ("Sends `ATSH`").

### Bytes, strings and units
- Transports deal in `bytes` only. ASCII decoding happens in one place (`_responses.py`).
- CAN payloads are `bytes`, never hex strings. Hex only appears in `__repr__` and logs.
- All durations are `float` **seconds**, parameters are named `timeout`. Device-specific units (e.g. the 4 ms steps of `ATST`) are converted inside the command builders.
- Every blocking call has an explicit, bounded `timeout`.
- AT command strings are built in `_commands.py`, never as literals scattered through the code.

### Errors
- Everything raised derives from `ELM327Error`. Device error replies map to `ResponseError` subclasses carrying `.command` and `.response`.
- Wrap foreign exceptions with `raise ... from exc`. Never `except Exception: pass`.
- Invalid arguments raise `ValueError`/`TypeError` *before* anything is sent to the device.

### Logging
- `logger = logging.getLogger(__name__)` per module. The library never configures handlers and never prints.
- `DEBUG`: every TX/RX line. `INFO`: connect/disconnect. `WARNING`: recoverable device quirks.
- Lazy formatting only: `logger.debug("RX: %r", line)`.

### Concurrency and resources
- `ELM327` and transports are context managers; `close()` is idempotent.
- One lock serialises access to the device. No global state, no work at import time.
- Background threads are daemon threads, named `elm327-<purpose>`, with an explicit stop path.

### Docstrings and comments
- Google style on every public item (`Args`, `Returns`, `Raises`, `Example`).
- Comments explain *why* (device and clone quirks), not *what*.

### Tests
- pytest, files mirror the source layout, names read `test_<unit>_<behaviour>`.
- Unit tests use the in-memory emulator (`tests/emulator`) and must be fast and deterministic.
- Tests needing hardware are marked `@pytest.mark.hardware` and skipped unless `--port` is given.
- Coverage of `src/` stays at **90 % or higher**.

## Git workflow
- `main` is always releasable. Work on short-lived `feat/…`, `fix/…` branches and merge via PR.
- [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `build:`, `ci:`, `chore:`.
- Each commit builds and passes the test suite on its own.
- Update `CHANGELOG.md` (Keep a Changelog format) under *Unreleased* for user-visible changes.

## Releasing
- Versions come from git tags via `hatch-vcs` and follow SemVer. The API is unstable while on `0.x`.
- `git tag v0.1.0 && git push origin v0.1.0` triggers `.github/workflows/release.yml`, which builds, then publishes to PyPI (Trusted Publishing) and, if configured, to a private index.
- Private index: set repository variable `PRIVATE_INDEX_URL` and secrets `PRIVATE_INDEX_USERNAME` / `PRIVATE_INDEX_PASSWORD`.
- Supported Python versions follow upstream end-of-life dates; currently 3.11+.
