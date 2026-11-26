# Development guide

This section explains everything in the repository *except* the library code: how the project is
packaged, installed, checked, tested, documented and released. It is written for someone who is
comfortable writing Python but has not maintained a releasable package before.

Each page follows the same structure:

1. **Concepts**: what the tool or standard is and which problem it solves.
2. **In this project**: how it is configured here, and why.
3. **Everyday tasks**: the exact commands.

!!! tip "Just want the rules?"
    `CONTRIBUTING.md` at the repository root is the short checklist of conventions and commands.
    These pages are the explanations behind it.

## The big picture

A Python *project* is more than its source code. Around the code sit:

| Concern | Question it answers | Tool here | Page |
| --- | --- | --- | --- |
| Metadata and packaging | What is this package, what does it need, how is it built? | `pyproject.toml`, hatchling | [pyproject.toml](pyproject.md) |
| Environments and dependencies | Which exact versions are installed, and where? | uv | [uv](uv.md) |
| Code quality | Is the code formatted, idiomatic and type-correct? | Ruff, mypy, pre-commit | [Code quality](code-quality.md) |
| Testing | Does it work, and how much of it is exercised? | pytest, coverage | [Testing](testing.md) |
| Documentation | How do people learn to use it? | MkDocs, mkdocstrings | [Documentation](documentation.md) |
| Automation and release | Is every change checked, and how does a version reach users? | GitHub Actions, PyPI | [CI and releasing](releasing.md) |

They are glued together by a few files at the repository root, described in the
[project tour](project-tour.md).

## Lifecycle of a change

```text
edit code ─▶ uv run pytest ─▶ git commit ─▶ pre-commit hooks ─▶ push ─▶ CI ─▶ tag vX.Y.Z ─▶ release
             (local checks)               (format, lint, types)        (all OSes,   (build once,
                                                                        all Pythons) publish)
```

Everything that runs in CI can be run locally with the same tool versions, because they all come
from the same lockfile (`uv.lock`). "Works on my machine" and "works in CI" mean the same thing.

## Suggested reading order

1. [Project tour](project-tour.md): know what every file is for.
2. [pyproject.toml](pyproject.md) and [uv](uv.md): the foundation everything else builds on.
3. [Code quality](code-quality.md) and [Testing](testing.md): the day-to-day loop.
4. [Documentation](documentation.md) and [CI and releasing](releasing.md): getting it to users.
