# Documentation

This site is built with [MkDocs](https://www.mkdocs.org/). The API reference is generated from the
docstrings by [mkdocstrings](https://mkdocstrings.github.io/).

## Concepts

### Docs as code

The documentation lives in the repository as Markdown files, next to the code it describes. It is
versioned with the code, reviewed in the same commits, and built and checked by CI. A change that
breaks the docs, such as a link to a renamed function, fails the build like a failing test would.

### Static site generators

MkDocs is a *static site generator*: it converts a folder of Markdown files into a folder of plain
HTML, CSS and JavaScript. The result needs no server-side code or database, so it can be hosted
anywhere that serves files, and it opens offline too.

### Four kinds of documentation

A useful way to organise docs (the [Diátaxis](https://diataxis.fr/) framework) is by what the
reader is trying to do:

| Kind | Reader wants to... | Here |
| --- | --- | --- |
| Tutorial | learn by doing | [Quick start](../quickstart.md) |
| How-to guide | solve a specific problem | the "Everyday tasks" sections |
| Reference | look up exact details | [API reference](../api.md), generated |
| Explanation | understand why | this Development section, [Home](../index.md) |

Keeping them apart stops reference pages from turning into essays, and tutorials from drowning in
detail.

### API docs from docstrings

Hand-written API pages drift away from the code. Instead, mkdocstrings reads the docstrings and
type hints and renders them. Writing a good docstring therefore *is* writing the documentation.

## In this project

### Files

```text
mkdocs.yml            site configuration
docs/
├── index.md          Home
├── quickstart.md     Quick start
├── api.md            API reference (mostly ::: directives, see below)
└── development/      this guide
```

The built site goes to `site/`, which is git-ignored.

### `mkdocs.yml`

```yaml
site_name: elm327
strict: true

theme:
  name: mkdocs
  color_mode: auto
  user_color_mode_toggle: true
  navigation_depth: 3
```

- `strict`: warnings fail the build: broken links between pages, missing files, cross-references
  to objects that do not exist.
- `theme`: the built-in `mkdocs` theme. `color_mode: auto` follows the operating system's light or
  dark setting; the toggle in the top bar lets readers override it. `navigation_depth` is how many
  heading levels appear in the sidebar.

```yaml
nav:
  - Home: index.md
  - Quick start: quickstart.md
  - API reference: api.md
  - Development:
      - Overview: development/index.md
      - ...
```

`nav` defines the menu and its order. A nested list creates a section (a dropdown in the top bar).
A page in `docs/` that is not listed is still built, but cannot be reached from the menu.

```yaml
plugins:
  - search
  - mkdocstrings: ...
markdown_extensions:
  - admonition
  - tables
  - toc:
      permalink: true
```

- `search`: builds a client-side search index (no server needed).
- `mkdocstrings`: the API reference, see below.
- Markdown extensions add syntax on top of standard Markdown: `admonition` for note and warning
  boxes, `tables` for tables, `toc` with `permalink` for a clickable anchor next to every heading.

### Writing pages

Standard Markdown, plus:

```markdown
!!! warning "Optional title"
    Indented content becomes a highlighted box. Types include note, tip, warning, danger.

[Link to another page](../quickstart.md)          # relative path to the .md file
[Link to a heading](uv.md#the-lockfile)           # headings get anchors automatically
```

Link to the `.md` file, not to the generated HTML. MkDocs converts it and, in strict mode, fails the
build if the target does not exist. Links to files outside `docs/` (like `pyproject.toml`) are not
allowed, which is why repository files are referred to by name in these pages.

### The API reference: mkdocstrings

In `docs/api.md`, a line like this:

```markdown
::: elm327.ELM327
```

is replaced at build time by the documentation of `elm327.ELM327`: its signature, docstring,
parameters table and members. The Python handler uses [Griffe](https://mkdocstrings.github.io/griffe/)
to read the source files in `src/` (`paths: [src]`) *without importing them*, so documentation
builds never run library code.

The options in `mkdocs.yml` control the rendering:

| Option | Effect |
| --- | --- |
| `docstring_style: google` | Parse `Args:`, `Returns:`, `Raises:`, `Examples:` sections |
| `show_source: false` | Do not embed the source code |
| `show_root_heading: true` | Show the object's name as a heading |
| `members_order: source` | Keep members in source order, not alphabetical |
| `merge_init_into_class: true` | Show `__init__` parameters on the class itself |
| `separate_signature`, `show_signature_annotations` | Render the full typed signature as a code block |

Only public objects are documented: names starting with `_` are skipped, and `__all__` decides what
a module exposes.

### Docstrings that render well

```python
def send(self, command: str, *, timeout: float | None = None) -> list[str]:
    """Send a command and return its reply lines.

    The first line is the summary. Following paragraphs give details.

    Args:
        command: The command, without the trailing carriage return.
        timeout: Time to wait, in seconds. Defaults to
            [`timeout`][elm327.ELM327.timeout].

    Returns:
        The reply lines, e.g. `["OK"]`.

    Raises:
        NoDataError: If the vehicle did not answer.

    Examples:
        >>> elm.send("ATI")
        ['ELM327 v1.5']
    """
```

- Sections are recognised by their exact names, followed by a colon. Use `Examples:` (plural), so
  that `>>>` lines render as code.
- **Cross-references** use Markdown link syntax with the full Python path as the target:
  `` [`ELM327`][elm327.ELM327] ``, or `` [`connect()`][elm327.ELM327.connect] `` for a method.
  Strict mode verifies that the target exists.
- Sphinx-style roles such as ``:class:`ELM327` `` are *not* understood and would show up as
  literal text. `tests/unit/test_docstrings.py` rejects them.
- Types are not repeated in `Args:`; they come from the annotations.

## Everyday tasks

| Task | Command |
| --- | --- |
| Live preview with auto-reload | `uv run --group docs mkdocs serve`, then open <http://127.0.0.1:8000> |
| Build the site into `site/` (as CI does) | `uv run --group docs mkdocs build --strict` |
| Add a page | create the `.md` file in `docs/` and add it to `nav` in `mkdocs.yml` |
| Document a new public object | give it a docstring; if it is in a module already listed in `api.md`, it appears automatically |

### Publishing the site (when the time comes)

The output in `site/` can be served by any static host:

- **GitHub Pages**: `mkdocs gh-deploy` builds the site and pushes it to a `gh-pages` branch; or a
  GitHub Actions job can deploy it on every release.
- **Read the Docs**: builds automatically on every push and can host one version of the docs per
  release. It needs a small `.readthedocs.yaml` file in the repository.
- **Any web server**: copy the `site/` folder.
