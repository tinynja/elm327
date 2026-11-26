# Project tour

Every file and folder outside the library code, what it does, and why it exists.

```text
elm327/
├── .github/workflows/        CI and release automation (GitHub Actions)
│   ├── ci.yml
│   └── release.yml
├── docs/                     Documentation pages (Markdown), built by MkDocs
├── examples/                 Small runnable scripts using the library
├── src/elm327/               The library itself (the only thing that ships to users)
├── tests/                    Test suite and the adapter emulator
├── .gitattributes            Line-ending rules for git
├── .gitignore                Files git must never track
├── .pre-commit-config.yaml   Checks run automatically before each commit
├── .python-version           Python version for the development environment
├── CHANGELOG.md              Human-readable history of user-visible changes
├── CLAUDE.md                 Instructions for AI coding assistants working on the repo
├── CONTRIBUTING.md           Conventions and commands for contributors
├── LICENSE                   The MIT license text
├── README.md                 Front page: what it is, how to install, a first example
├── mkdocs.yml                Documentation site configuration
├── pyproject.toml            Project metadata, build and tool configuration
└── uv.lock                   Exact versions of every dependency, for reproducibility
```

Generated folders that are **not** in git: `.venv/` (the virtual environment), `dist/` (built
packages), `site/` (built docs) and the tool caches (`.pytest_cache/`, `.mypy_cache/`,
`.ruff_cache/`, `__pycache__/`, `.coverage`).

## The `src/` layout

**Concept.** There are two common ways to place a package in a repository:

```text
flat layout                 src layout
elm327/                     src/
    __init__.py                 elm327/
tests/                              __init__.py
                            tests/
```

With the flat layout, running Python from the repository root makes `import elm327` pick up the
folder directly from disk, whether or not the package is installed. Tests then pass locally even
when the *installed* package is broken, for example because a file is missing from the wheel or a
dependency is undeclared.

With the src layout, the package is only importable once installed. The tests therefore always run
against the package as users get it. This is the layout recommended by the Python Packaging
Authority, and it is what this project uses.

During development the package is installed in **editable** mode (uv does this automatically): the
environment points at `src/` instead of a copy, so code changes take effect without reinstalling.

## Inside `src/elm327/`: public and private modules

Modules whose names start with `_` (`_commands.py`, `_responses.py`, `transport/_serial.py`...) are
private: they may change at any time. The public API is exactly what `elm327/__init__.py` and
`elm327/transport/__init__.py` list in `__all__`. Users import from those two places only, which
lets the internals be reorganised without breaking anyone.

### `py.typed`

An empty file with an important meaning, defined by
[PEP 561](https://peps.python.org/pep-0561/). It tells type checkers (mypy, Pyright, IDEs) that
this package ships its own type hints and that they should be trusted. Without it, a user's type
checker would treat everything imported from `elm327` as untyped (`Any`).

## `tests/`

```text
tests/
├── conftest.py          Shared pytest fixtures and the --port option
├── emulator/            FakeELM327: an in-memory adapter for unit tests
├── unit/                Fast tests, no hardware, run everywhere
└── hardware/            Smoke tests against a real adapter, opt-in
```

Tests live outside `src/` so they are not shipped to users. They *are* included in the source
distribution (see [pyproject.toml](pyproject.md#build-targets)), so that downstream packagers, such
as Linux distributions, can run them. Details in [Testing](testing.md).

## `examples/`

Short scripts showing real usage. They are not part of the package and not run by the tests, but
they are linted, so they stay valid Python.

## Root files in detail

### `.gitignore`

Lists files git should not track: generated environments, caches and build output. Committing those
would bloat the repository and cause conflicts between machines.

### `.gitattributes`

`* text=auto eol=lf` makes git store text files with Unix line endings (LF) and check them out with
LF on every OS. Without it, Windows checkouts can get CRLF endings, which produces whole-file diffs
and can break shell scripts and some tools.

### `.python-version`

Contains `3.11`. uv reads it to choose the interpreter for `.venv`, and downloads it if needed.
The project develops on the **oldest** supported version on purpose: using a feature that only
exists in a newer Python then fails immediately on your machine, not later in CI. CI still tests
every supported version.

### `README.md`

The project's front page on GitHub and on PyPI (it becomes the package's long description, see
`readme` in [pyproject.toml](pyproject.md#project-metadata)). It should answer: what is it, how do
I install it, what does the simplest use look like.

### `CHANGELOG.md`

A curated list of user-visible changes per version, in the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. New entries go under
`## [Unreleased]`; at release time that heading becomes the version number. Unlike the git log, it is
written for users, so internal refactors are left out.

### `CONTRIBUTING.md`

The rules: coding conventions, git workflow, the commands to run. GitHub links to it automatically
when someone opens an issue or a pull request.

### `CLAUDE.md`

Read automatically by Claude Code at the start of a session. It points to `CONTRIBUTING.md` and
lists the few rules an AI assistant must follow. Other assistants use similar files
(e.g. `AGENTS.md`).

### `LICENSE`

The MIT license with the copyright holder. Its name is also declared in `pyproject.toml`, so it
appears on PyPI and inside the built packages.

### `uv.lock`

Generated by uv, never edited by hand, always committed. See [uv](uv.md#the-lockfile).

### `pyproject.toml`, `mkdocs.yml`, `.pre-commit-config.yaml`, `.github/workflows/`

Each has its own page: [pyproject.toml](pyproject.md), [Documentation](documentation.md),
[Code quality](code-quality.md#pre-commit) and [CI and releasing](releasing.md).
