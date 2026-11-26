"""Guards for documentation conventions that the strict docs build cannot catch."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SOURCE_FILES = sorted((Path(__file__).parents[2] / "src").rglob("*.py"))
SPHINX_ROLE = re.compile(r":(?:class|meth|func|attr|exc|mod|obj|data):`")


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda path: path.name)
def test_docstrings_use_markdown_cross_references(path: Path) -> None:
    # mkdocstrings renders Markdown: Sphinx roles would show up literally in the docs.
    offending = [
        f"{path.name}:{number}: {line.strip()}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if SPHINX_ROLE.search(line)
    ]
    assert not offending, "use [`Name`][elm327.Name] instead of Sphinx roles:\n" + "\n".join(
        offending
    )
