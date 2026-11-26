# Code quality

Three automated checks keep the code consistent and catch mistakes before tests even run:
**Ruff** formats and lints, **mypy** checks types, and **pre-commit** runs them on every commit.

## Concepts

### Formatter vs linter vs type checker

| Kind | Question | Example finding | Changes code? |
| --- | --- | --- | --- |
| **Formatter** | Does it *look* consistent? | quote style, line breaks, spacing | Yes, rewrites it |
| **Linter** | Does it follow good practice? | unused import, mutable default argument, `except:` without a type | Some rules can auto-fix |
| **Type checker** | Do the types fit together? | passing `bytes` where `str` is expected, possible `None` | No, only reports |

A formatter removes style discussions entirely: the code looks the way the tool writes it. A
linter catches bug patterns and enforces conventions. A type checker proves, without running the
code, that every call matches the signatures. In Python, where nothing is checked at compile time,
it catches a whole class of bugs that tests might miss.

### Why automate them

Checks that depend on remembering to run them are eventually skipped. Here they run in three
places: in your editor (optional), before every commit (pre-commit), and in CI (mandatory). The
same versions are used in all three because they come from `uv.lock`.

## Ruff

[Ruff](https://docs.astral.sh/ruff/) is both a formatter (compatible with Black) and a linter that
reimplements hundreds of rules from flake8, isort, pyupgrade, pylint and their plugins, in one fast
tool.

### Configuration

```toml
[tool.ruff]
line-length = 99
target-version = "py311"
src = ["src", "tests"]
```

- `line-length`: the formatter wraps code at 99 columns.
- `target-version`: Ruff suggests syntax available in 3.11, and never newer.
- `src`: where first-party code lives, used to sort imports into the right groups.

```toml
[tool.ruff.format]
docstring-code-format = true
```

Code examples inside docstrings are formatted too.

### Selected rule families

Ruff only runs the rule families you select. This project selects:

| Code | Origin | Catches |
| --- | --- | --- |
| `E`, `W` | pycodestyle | PEP 8 style errors and warnings |
| `F` | Pyflakes | unused imports and variables, undefined names |
| `I` | isort | import order and grouping |
| `UP` | pyupgrade | outdated syntax (`Optional[X]` instead of `X \| None`...) |
| `B` | flake8-bugbear | likely bugs: mutable defaults, `except` swallowing too much... |
| `SIM` | flake8-simplify | code that can be simpler |
| `N` | pep8-naming | naming conventions |
| `D` | pydocstyle | missing or malformed docstrings (Google convention) |
| `ANN` | flake8-annotations | missing type annotations |
| `RUF` | Ruff | Ruff's own checks, e.g. unsorted `__all__`, unused `noqa` comments |
| `PL` | Pylint | a broad set of design and correctness checks |
| `PT` | flake8-pytest-style | pytest idioms, e.g. `pytest.raises` without `match` |
| `TRY` | tryceratops | exception-handling anti-patterns |
| `LOG`, `G` | flake8-logging(-format) | logging misuse, e.g. f-strings in log calls |
| `S` | flake8-bandit | security issues |
| `C4`, `PIE`, `RET` | various | comprehensions, redundant code, return statements |
| `PTH` | flake8-use-pathlib | `os.path` where `pathlib` is clearer |
| `FA` | flake8-future-annotations | missing `from __future__ import annotations` |

The full rule list is at [docs.astral.sh/ruff/rules](https://docs.astral.sh/ruff/rules/).

### Exceptions to the rules

```toml
ignore = ["E501", "TRY003", "PLR0913"]
```

Each ignore is a deliberate project decision, commented in `pyproject.toml`. For example, `E501`
(line too long) is off because the formatter already wraps code, and long string literals are
intentionally left unsplit.

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "S101", "PLR2004", "ANN401"]
"examples/**" = ["D", "T201"]
```

Tests do not need docstrings and must use `assert` (which Bandit flags in production code).
Examples may `print`.

For a single justified exception in the code, use an inline comment naming the rule and the reason:

```python
if not 0 < port < 65536:  # noqa: PLR2004  TCP port range
```

`RUF100` reports `noqa` comments that are no longer needed, so they cannot accumulate.

### Commands

| Task | Command |
| --- | --- |
| Format everything | `uv run ruff format` |
| Check formatting without changing files (what CI does) | `uv run ruff format --check` |
| Lint | `uv run ruff check` |
| Lint and apply safe fixes | `uv run ruff check --fix` |
| Explain a rule | `uv run ruff rule PLR2004` |

## mypy

[mypy](https://mypy.readthedocs.io/) reads type hints and verifies that the code respects them.

### Configuration

```toml
[tool.mypy]
strict = true
python_version = "3.11"
files = ["src", "tests"]
mypy_path = "tests"
warn_unreachable = true
```

- `strict`: turns on every optional check. Among other things: every function must be fully
  annotated, `Any` must not leak silently, and `# type: ignore` comments that are no longer needed
  are errors. Strict mode is easiest to adopt at the start of a project, which is why it is on from
  day one.
- `python_version`: check against 3.11 semantics, the oldest supported version.
- `files`: what `uv run mypy` checks when given no arguments. Tests are type-checked too.
- `mypy_path`: lets mypy resolve `from emulator.fake_elm import ...` in the tests.
- `warn_unreachable`: reports code that the types prove can never run, which often reveals a wrong
  assumption.

### Third-party types

mypy needs type information for every imported library. Libraries either ship it (with a
`py.typed` file, like this project does) or have separate *stub* packages. pyserial has none of its
own, so the `dev` group includes `types-pyserial` from the
[typeshed](https://github.com/python/typeshed) project.

### Silencing an error

Fix the types when possible. When mypy is genuinely wrong, silence one specific error code on one
line:

```python
SerialTransport("loop://", baudrate="fast")  # type: ignore[arg-type]
```

Never use a bare `# type: ignore`.

### Commands

| Task | Command |
| --- | --- |
| Type-check the project | `uv run mypy` |
| Reveal what mypy thinks a type is | add `reveal_type(x)` to the code, then run mypy |

## pre-commit

### Concept

Git can run scripts at certain moments, called *hooks*. A *pre-commit* hook runs when you type
`git commit` and can abort the commit if it fails. [pre-commit](https://pre-commit.com/) is a
framework for managing such hooks from a config file, so everyone working on the project runs the
same checks.

### Configuration

`.pre-commit-config.yaml` has two parts:

1. **Generic file hygiene** from the `pre-commit-hooks` repository (pinned with `rev`): trailing
   whitespace, a final newline, valid YAML and TOML, no leftover merge-conflict markers, LF line
   endings.
2. **Local hooks** for Ruff and mypy. Instead of letting pre-commit install its own copies, they run
   `uv run --frozen ruff ...`, so the hook uses exactly the version from `uv.lock`, the same one as
   CI. With `--frozen`, the hooks start fast because uv does not re-check the lockfile.

Hooks receive the list of staged files, except mypy (`pass_filenames: false`), which always checks
the whole project because types cross file boundaries.

When a hook *modifies* files (the formatter, whitespace fixers), the commit is aborted so you can
review the changes. Stage them with `git add`, then commit again.

### Commands

| Task | Command |
| --- | --- |
| Install the hook in your clone (once per clone) | `uv run pre-commit install` |
| Run all hooks on every file | `uv run pre-commit run --all-files` |
| Update the pinned `pre-commit-hooks` revision | `uv run pre-commit autoupdate` |
| Bypass the hooks for one commit (avoid it: CI runs the same checks) | `git commit --no-verify` |

## Editor integration

Running the same tools inside your editor gives instant feedback:

- **VS Code**: the *Ruff* extension (format on save, lint as you type) and *Mypy Type Checker*.
  Select `.venv` as the interpreter so the extensions use the project's tool versions.
- **PyCharm**: the *Ruff* plugin, or Ruff support built into recent versions, and the *Mypy*
  plugin. Point the project interpreter at `.venv`.

Both read their configuration from `pyproject.toml`, so no extra settings are needed.
