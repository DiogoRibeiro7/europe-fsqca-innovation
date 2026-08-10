from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.spec import load_research_spec, validate_research_spec


def test_research_spec_matches_project_configuration() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    report = validate_research_spec(spec, base_dir=root)

    assert report.passed
    assert not report.warnings


def test_research_spec_reports_condition_mismatch() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    altered = spec.model_copy(update={"condition_sets": ["DIG"]})
    report = validate_research_spec(altered, base_dir=root)

    assert "condition_sets do not match analysis configuration" in report.errors


def test_research_spec_requires_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(TypeError, match="research specification root"):
        load_research_spec(path)
