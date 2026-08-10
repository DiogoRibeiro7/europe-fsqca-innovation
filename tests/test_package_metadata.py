from __future__ import annotations

from importlib import resources

import euro_fsqca


def test_package_exports_version() -> None:
    assert euro_fsqca.__all__ == ["__version__"]
    assert euro_fsqca.__version__


def test_package_marks_typed_interface() -> None:
    marker = resources.files("euro_fsqca").joinpath("py.typed")

    assert marker.is_file()
