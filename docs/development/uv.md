# uv

[uv](https://docs.astral.sh/uv/) manages Python versions, virtual environments and dependencies
for this project, and builds and publishes it.

## Concepts

### Virtual environments

Installing packages into the system Python mixes every project's dependencies together: project A
needs `pyserial 3.4`, project B needs `3.5`, and both share one `site-packages`. A **virtual
environment** is a self-contained directory with its own `site-packages` and a link to a Python
interpreter. Each project gets one, so its dependencies never collide with anything else.

uv creates the project's environment in `.venv/` at the repository root. It is disposable: delete
it at any time and the next `uv sync` or `uv run` rebuilds it exactly.

### Declared dependencies vs locked dependencies

There are two levels of "what this project needs":

- **Declared** (`pyproject.toml`): human-written ranges such as `pytest>=8.3`. They say what is
  *acceptable*.
- **Locked** (`uv.lock`): the exact versions chosen, such as `pytest==9.2.0`, for the project's
  direct dependencies *and* everything they depend on, with file hashes. They say what is
  *installed*.

Resolution (finding a set of versions that satisfies every range at once) happens only when the
lock is updated. Installing from the lock just reproduces it. That is what makes environments
identical across machines and in CI, and what makes installs fast.

### What uv replaces

Before uv, the same job took several tools:

| Job | Traditional tool | With uv |
| --- | --- | --- |
| Install a Python version | pyenv, python.org installer | `uv python install` |
| Create an environment | `python -m venv`, virtualenv | automatic (`.venv/`) |
| Install packages | pip | `uv sync`, `uv add` |
| Lock dependencies | pip-tools, Poetry | `uv lock` (automatic) |
| Run a command in the environment | `source .venv/bin/activate` | `uv run <command>` |
| Run a CLI tool once | pipx | `uvx <tool>` |
| Build | `python -m build` | `uv build` |
| Upload to an index | twine | `uv publish` |

uv is written in Rust and keeps a global cache of downloaded packages, so creating an environment
usually takes well under a second.

## In this project

### The lockfile

`uv.lock` is generated, committed, and never edited by hand. It is *universal*: one file covers
every operating system and every Python version allowed by `requires-python`, so the Windows, macOS
and Linux CI jobs and your machine all resolve to the same versions.

It changes when:

- you add or remove a dependency (`uv add`, `uv remove`) or edit the dependency lists in
  `pyproject.toml`;
- you ask for upgrades (`uv lock --upgrade`).

Commit `uv.lock` together with the `pyproject.toml` change that caused it.

!!! note "Libraries still declare ranges"
    The lock only governs *this repository's* environment. Users who `pip install elm327` get
    the ranges from `[project] dependencies` resolved against their own environment. Locking keeps
    development reproducible without imposing pins on users.

### The Python version

`.python-version` contains `3.11`, so `.venv` is built with Python 3.11, the oldest version the
project supports. If 3.11 is not installed, uv downloads a standalone build automatically.

### What gets installed

`uv sync` installs, into `.venv/`:

1. the runtime dependencies (`pyserial`);
2. the `dev` dependency group (pytest, Ruff, mypy...), because uv includes it by default;
3. the project itself, in **editable** mode: the environment points at `src/`, so edits are live
   without reinstalling.

Other groups, such as `docs`, are only installed when requested with `--group docs`.

### Exact and inexact syncs

- `uv sync` is **exact**: it also *removes* packages that are not part of the requested set. Running
  `uv sync` after `uv sync --group docs` uninstalls MkDocs again.
- `uv run` is **inexact**: it installs what is missing but removes nothing.

### How CI uses it

CI runs `uv sync --locked`, which fails if `uv.lock` is out of date with `pyproject.toml`. This
catches a dependency change committed without its lockfile update. `--frozen` (used by the
pre-commit hooks) is the faster variant: it trusts the lockfile and skips that check.

## Everyday tasks

### Environment

| Task | Command |
| --- | --- |
| Create or update `.venv` to match the lock | `uv sync` |
| Same, including the docs tools | `uv sync --group docs` |
| Run anything inside the environment | `uv run <command>`, e.g. `uv run pytest`, `uv run python script.py` |
| Start from scratch | delete `.venv/`, then `uv sync` |

`uv run` checks the environment first and syncs it if needed, so after a `git pull` you can simply
run your command.

!!! tip "Activating instead"
    If you prefer typing `pytest` instead of `uv run pytest`, activate the environment once per
    terminal: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows).
    You then have to remember to `uv sync` after dependency changes yourself.

### Dependencies

| Task | Command |
| --- | --- |
| Add a runtime dependency | `uv add "package>=X.Y"` |
| Add a development tool | `uv add --group dev package` |
| Add a docs tool | `uv add --group docs package` |
| Remove a dependency | `uv remove package` |
| Upgrade everything in the lock (within the ranges) | `uv lock --upgrade`, then `uv sync` |
| Upgrade one package | `uv lock --upgrade-package pytest` |
| Show the dependency tree | `uv tree` |

### Python versions

| Task | Command |
| --- | --- |
| List installed and available versions | `uv python list` |
| Install a version | `uv python install 3.14` |
| Run the tests on another version, without touching `.venv` | `uv run --isolated --python 3.13 pytest` |

`--isolated` builds a temporary environment for that one command, which is handy to reproduce a CI
failure on a specific Python version.

### One-off tools

`uvx <tool>` runs a tool in a throwaway environment without adding it to the project, for example
`uvx twine check dist/*`. Use it for tools you need occasionally; anything the project relies on
belongs in a dependency group, so its version is locked.

### Building and publishing

| Task | Command |
| --- | --- |
| Build sdist and wheel into `dist/` | `uv build` |
| Publish to PyPI (normally done by CI) | `uv publish` |
| Publish to another index | `uv publish --publish-url <upload URL>` |

See [CI and releasing](releasing.md) for how releases are actually made.

### Housekeeping

| Task | Command |
| --- | --- |
| Show where the cache lives | `uv cache dir` |
| Free disk space | `uv cache prune` (unused entries) or `uv cache clean` (everything) |
| Update uv itself | `uv self update` (if installed with the official installer) |
