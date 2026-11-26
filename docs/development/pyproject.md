# pyproject.toml

`pyproject.toml` is the single configuration file of a modern Python project. It describes what the
package is, how to build it, and how every development tool should behave.

## Concepts

### From setup.py to pyproject.toml

Historically, packages were described by a `setup.py` script that ran `setuptools`. Because it was
code, tools had to *execute* it just to learn a package's name or dependencies, and every project
did it differently. A series of standards (PEPs, Python Enhancement Proposals) replaced it with a
declarative TOML file:

| PEP | What it standardised |
| --- | --- |
| [518](https://peps.python.org/pep-0518/) | The file itself and the `[build-system]` table: what is needed to build the project |
| [517](https://peps.python.org/pep-0517/) | The interface between build *front ends* and build *back ends* |
| [621](https://peps.python.org/pep-0621/) | The `[project]` table: name, version, dependencies and other metadata |
| [639](https://peps.python.org/pep-0639/) | `license` as an SPDX expression (`"MIT"`) and `license-files` |
| [735](https://peps.python.org/pep-0735/) | `[dependency-groups]`: development-only dependency lists |
| [440](https://peps.python.org/pep-0440/) / [508](https://peps.python.org/pep-0508/) | Version numbers and dependency specifiers (`pyserial>=3.5`) |

Any table named `[tool.<name>]` belongs to that tool (Ruff, mypy, pytest...). Python packaging
ignores them, which is why one file can configure everything.

### Front ends, back ends and distributions

*Building* turns a source tree into files that can be installed. Two roles are involved:

- A **build front end** is what you run: `uv build`, `pip install .`, `python -m build`. It reads
  `[build-system]`, creates an isolated temporary environment, installs the back end in it, and
  calls it.
- A **build back end** does the work: it collects files and writes metadata. Popular back ends are
  hatchling, setuptools, flit-core, pdm-backend and uv's own `uv_build`. This project uses
  **hatchling**.

Because the interface is standard, any front end works with any back end.

The back end produces two kinds of **distributions**:

| | Source distribution (sdist) | Wheel |
| --- | --- | --- |
| File | `elm327-0.1.0.tar.gz` | `elm327-0.1.0-py3-none-any.whl` |
| Contains | Source tree: code, tests, docs, config | Exactly the files to install, plus metadata |
| Installing it | Must be *built* first (runs the back end) | Unzipped into place: fast, no build step |
| Used by | Packagers, as an archival source | `pip`/`uv` for almost every install |

A wheel's file name encodes where it can be installed: `py3-none-any` means "any Python 3, no
compiled extension (no ABI), any platform". Packages with C extensions publish one wheel per
platform instead. This project is pure Python, so a single wheel serves everyone.

### Metadata vs development configuration

Everything in `[project]` ends up *inside the published package* and is visible to users and
installers. Everything under `[dependency-groups]` and `[tool.*]` exists only for people working on
the repository. Keeping that distinction in mind explains most of the file.

## In this project

### `[build-system]`

```toml
[build-system]
requires = ["hatchling>=1.27", "hatch-vcs>=0.4"]
build-backend = "hatchling.build"
```

- `requires`: packages the front end installs in the temporary build environment. `hatch-vcs` is a
  hatchling plugin that reads the version from git (see [Versioning](#versioning)). `>=1.27` is
  the first hatchling version supporting PEP 639 license fields.
- `build-backend`: the Python object the front end calls.

### Project metadata

```toml
[project]
name = "elm327"
dynamic = ["version"]
description = "..."
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.11"
authors = [{ name = "Amine Kchouk" }]
keywords = [...]
classifiers = [...]
dependencies = ["pyserial>=3.5"]
```

| Field | Meaning |
| --- | --- |
| `name` | The distribution name on PyPI (`pip install elm327`). It happens to match the import name, but it does not have to (`pip install pyserial` gives `import serial`). |
| `dynamic` | Fields computed at build time instead of written here. The version comes from git tags. |
| `description` | One-line summary shown in search results on PyPI. |
| `readme` | Long description: `README.md` becomes the PyPI project page. |
| `license`, `license-files` | SPDX identifier and the files copied into every distribution. |
| `requires-python` | Installers refuse to install on older Pythons. They pick an older release of the package instead, if one fits. |
| `authors` | Shown on PyPI. An `email` key is optional. |
| `keywords`, `classifiers` | Help people find the package. Classifiers come from a [fixed list](https://pypi.org/classifiers/). `Typing :: Typed` advertises `py.typed`, `Development Status` signals maturity. |
| `dependencies` | What users get installed alongside the package. |

**How to write dependency versions for a library.** Give a minimum version (the oldest one known to
work) and no maximum. A library is installed next to other packages; an upper cap such as
`pyserial<4` would make it impossible to install together with anything that needs pyserial 4, even
if it works fine with it. Exact pins (`==`) belong in lockfiles, not in a library's metadata.

**Not yet present, but coming:**

- `[project.urls]`: links shown on PyPI (homepage, docs, changelog, issues) once the repository is
  public.
- `[project.optional-dependencies]` (*extras*): optional feature sets users can request, e.g.
  `pip install elm327[can]` to also get python-can. Unlike dependency groups, extras are published
  metadata.
- `[project.scripts]`: command-line programs. `elm327 = "elm327.cli:main"` makes installers create
  an `elm327` command.
- `[project.entry-points."can.interface"]`: how python-can discovers third-party interfaces such as
  the planned `elm327` one.

### `[dependency-groups]`

```toml
[dependency-groups]
dev = ["mypy>=1.13", "pre-commit>=4.0", "pytest>=8.3", "pytest-cov>=6.0", "ruff>=0.8", "types-pyserial>=3.5"]
docs = ["mkdocs>=1.6", "mkdocstrings[python]>=0.27"]
```

Tools needed to *work on* the project, never installed by users. uv installs the `dev` group by
default and others on request (`--group docs`). `types-pyserial` provides type hints for pyserial,
which does not ship its own (it has no `py.typed`).

### Versioning

```toml
[tool.hatch.version]
source = "vcs"
fallback-version = "0.0.0"
```

The version is not written anywhere in the code. hatch-vcs (which uses setuptools-scm) computes it
from git when the package is built:

| State of the repository | Version |
| --- | --- |
| HEAD is exactly at tag `v0.1.0` | `0.1.0` |
| 3 commits after `v0.1.0` | `0.1.1.dev3+g1a2b3c4` (a development version of the *next* release) |
| ... with uncommitted changes | `0.1.1.dev3+g1a2b3c4.d20261126` (`d` + date marks a dirty tree) |
| No tags at all yet | `0.0.1.devN+g...`, where N counts all commits |
| No git information available | `0.0.0`, the fallback |

Releasing is therefore just tagging a commit, and the built package can never disagree with the tag.
At runtime, `elm327.__version__` reads the installed version through `importlib.metadata`.

!!! note
    Versions like `0.1.1.dev3+g1a2b3c4` contain a *local version label* (`+...`). PyPI rejects
    those, which conveniently prevents publishing an untagged build by accident.

### Build targets

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/elm327"]

[tool.hatch.build.targets.sdist]
include = ["src", "tests", "docs", "mkdocs.yml", "README.md", "CHANGELOG.md", "LICENSE"]
```

- **Wheel**: only the `elm327` package. hatchling strips the `src/` prefix, so it installs as
  `site-packages/elm327/`.
- **sdist**: an explicit list, so nothing unexpected is published (local scratch files, editor
  settings...). Tests and docs are included so that people building from source can verify and
  document it.

### Tool tables

| Table | Configures | Explained in |
| --- | --- | --- |
| `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]` | Formatter and linter | [Code quality](code-quality.md#ruff) |
| `[tool.mypy]` | Static type checking | [Code quality](code-quality.md#mypy) |
| `[tool.pytest.ini_options]` | Test runner | [Testing](testing.md#configuration) |
| `[tool.coverage.*]` | Coverage measurement and threshold | [Testing](testing.md#coverage) |

## Everyday tasks

| Task | How |
| --- | --- |
| Add a runtime dependency | `uv add "package>=X.Y"`: edits `dependencies` and updates `uv.lock` |
| Add a development tool | `uv add --group dev tool` |
| Remove a dependency | `uv remove package` |
| Build the sdist and wheel | `uv build` (output in `dist/`) |
| See the computed version | `uv run python -c "import elm327; print(elm327.__version__)"` |
| Inspect what a wheel contains | `unzip -l dist/*.whl` (or open it as a zip file) |
| Check the metadata PyPI will see | `uvx twine check --strict dist/*` |

After editing `pyproject.toml` by hand, run `uv sync` (or any `uv run`) so the lockfile and
environment follow.
