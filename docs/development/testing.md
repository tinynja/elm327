# Testing

The test suite is run with [pytest](https://docs.pytest.org/) and measured with
[coverage.py](https://coverage.readthedocs.io/) through the `pytest-cov` plugin.

## Concepts

### Kinds of tests

| Kind | Exercises | Speed | Here |
| --- | --- | --- | --- |
| **Unit tests** | One piece of code in isolation, with its surroundings replaced | Milliseconds | `tests/unit/` |
| **Integration tests** | Several real components together | Slower | e.g. the TCP and serial transport tests, which use real sockets and pyserial |
| **Hardware tests** | The library against a real adapter | Seconds, needs a device | `tests/hardware/` |

Unit tests are the bulk because they are fast, deterministic and run anywhere, including CI, which
has no ELM327 plugged in. Hardware tests confirm that the assumptions baked into the unit tests
match reality.

### Test doubles: fakes and mocks

To unit-test code that talks to a device, the device is replaced by a *test double*:

- A **mock** records calls and returns canned values, configured per test
  (`unittest.mock`). It is quick to write, but tests end up asserting *how* the code works, so they
  break on every refactor.
- A **fake** is a small working implementation of the real thing. Tests then assert on *behaviour*:
  "after connecting, echo is off on the device".

This project uses a fake, `FakeELM327` in `tests/emulator/fake_elm.py`. It interprets AT commands,
keeps the device state (echo, linefeeds...), formats replies like a real chip, and can be scripted:

```python
fake.replies["0100"] = ["41 00 BE 3E B8 13"]  # canned reply for one command
fake.silent = True  # never answers: simulates a wrong port
fake.monitoring = True  # behaves as if left running ATMA
```

It plugs into the driver through `LoopbackTransport`, the in-memory transport, and answers
synchronously, so tests need no threads or sleeps. When the library learns a new device behaviour,
the emulator learns it too.

### pytest essentials

- **Discovery**: files named `test_*.py`, functions named `test_*`. Plain `assert` statements;
  pytest rewrites them to show the values involved when they fail.
- **Fixtures**: functions decorated with `@pytest.fixture` that provide something a test needs.
  A test requests one by naming it as a parameter. Code after a `yield` in a fixture runs as
  cleanup, even when the test fails.
- **`conftest.py`**: fixtures and hooks defined there are available to every test in that folder
  and below, without imports.
- **Parametrisation**: `@pytest.mark.parametrize` runs one test function over a table of inputs,
  each reported as a separate test.
- **Markers**: labels on tests (`@pytest.mark.hardware`) used to select or skip groups of tests.
- **Built-in fixtures** used here: `monkeypatch` (temporarily replace attributes, undone after the
  test) and `caplog` (capture log records).

### Coverage

Coverage measures which lines (and, with *branch coverage*, which sides of each `if`) the tests
executed. It shows what is **not** tested; a high number does not prove the tests are good, but
uncovered code is certainly untested. The project requires at least 90%.

## In this project

### Layout

```text
tests/
├── conftest.py              --port option, hardware skipping, shared fixtures
├── emulator/fake_elm.py     FakeELM327
├── unit/
│   ├── test_commands.py     AT command builders and validation
│   ├── test_responses.py    reply decoding and error mapping
│   ├── test_device.py       the ELM327 driver, against the emulator
│   ├── test_transport.py    loopback, serial (pyserial loop://) and TCP (local socket server)
│   ├── test_exceptions.py
│   ├── test_docstrings.py   documentation conventions
│   └── test_package.py
└── hardware/
    └── test_real_device.py  read-only smoke tests on a real adapter
```

Test files mirror the source modules, so the tests for a module are easy to find.

### Shared fixtures (`tests/conftest.py`)

| Fixture | Provides |
| --- | --- |
| `fake` | A fresh `FakeELM327` |
| `elm` | An `ELM327` driver already connected to `fake`, closed after the test |
| `fast_sync` | *Autouse* (applies to every test): shrinks the connection-synchronisation delays, which exist for real hardware only, so the suite stays fast. Skipped for hardware tests. |

A typical test is therefore just:

```python
def test_read_voltage(fake: FakeELM327, elm: ELM327) -> None:
    fake.voltage = 13.84
    assert elm.read_voltage() == pytest.approx(13.8)
```

### Hardware tests

`conftest.py` adds a `--port` command-line option. Tests marked `hardware` are skipped unless it is
given, so a plain `uv run pytest` never touches a device. The hardware tests only send read-only
commands, so they are safe with the adapter plugged into a vehicle.

### Configuration

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
pythonpath = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
markers = ["hardware: needs a real ELM327 adapter (run with --port=<url>)"]
filterwarnings = ["error", "ignore::pytest.PytestCacheWarning"]
```

| Setting | Effect |
| --- | --- |
| `testpaths` | Where pytest looks when run without arguments |
| `pythonpath` | Adds `tests/` to the import path, so tests can `import emulator` |
| `-ra` | Prints a summary line for every test that did not pass (skipped, failed...) |
| `--strict-markers` | A typo in a marker name is an error instead of silently creating a new marker |
| `--strict-config` | Unknown settings in this table are errors |
| `markers` | Declares the custom markers (required by `--strict-markers`) |
| `filterwarnings` | Every warning fails the test run, so deprecations are fixed when they appear, not when the feature is removed. The exception is pytest's own cache warning, which signals an environment issue (e.g. an unwritable folder on Windows), not a code problem. |

### Coverage configuration

```toml
[tool.coverage.run]
source = ["elm327"]
branch = true

[tool.coverage.report]
fail_under = 90
show_missing = true
skip_covered = true
exclude_also = ["if TYPE_CHECKING:", "@abstractmethod", "raise NotImplementedError"]
```

- `source`: measure the installed `elm327` package (not the tests themselves).
- `branch`: measure both outcomes of every condition, not just lines.
- `fail_under`: `pytest --cov` fails when total coverage drops below 90%.
- `show_missing`, `skip_covered`: the report lists the uncovered line numbers and hides files that
  are fully covered.
- `exclude_also`: lines that can never run in a test by design (imports only for type checkers,
  abstract method bodies).

Coverage is only measured when `--cov` is passed, so normal test runs stay fast.

## Everyday tasks

| Task | Command |
| --- | --- |
| Run the unit tests | `uv run pytest` |
| ... with coverage and the 90% check | `uv run pytest --cov` |
| Browsable HTML coverage report | `uv run pytest --cov --cov-report=html`, then open `htmlcov/index.html` |
| Run one file / one test | `uv run pytest tests/unit/test_device.py` / `uv run pytest tests/unit/test_device.py::test_identify` |
| Run tests whose name matches | `uv run pytest -k voltage` |
| Stop at the first failure | `uv run pytest -x` |
| Rerun only what failed last time | `uv run pytest --lf` |
| Verbose names, show `print` output | `uv run pytest -v -s` |
| Find slow tests | `uv run pytest --durations=10` |
| Hardware tests only | `uv run pytest -m hardware --port=COM3` |
| Everything, including hardware | `uv run pytest --port=/dev/ttyUSB0` |
| See the library's TX/RX log during a test | `uv run pytest --log-level=DEBUG -k identify` (shown for failing tests) |

### Writing a new test

1. Put it in the file mirroring the module under test, named `test_<unit>_<behaviour>`.
2. Use the `fake` and `elm` fixtures. If the device needs a new behaviour, extend `FakeELM327`.
3. Prefer asserting on observable behaviour (return values, device state, raised exceptions)
   over internal details.
4. For expected errors, pass `match=` to `pytest.raises` so the test fails if the *wrong* error
   is raised. Ruff enforces this for broad exceptions such as `ValueError`.
