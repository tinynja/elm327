from __future__ import annotations

import elm327


def test_package_exposes_version() -> None:
    assert isinstance(elm327.__version__, str)
    assert elm327.__version__
