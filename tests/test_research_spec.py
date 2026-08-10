from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.spec import load_research_spec, validate_research_spec


def test_research_spec_matches_project_configuration() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    report = validate_research_spec(spec, base_dir=root)

    assert report.passed


def test_research_spec_warns_that_the_study_is_not_yet_empirical() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    report = validate_research_spec(spec, base_dir=root)

    joined = " ".join(report.warnings)
    assert "template" in joined
    assert "survey weight column" in joined


def test_research_spec_reports_condition_mismatch() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    altered = spec.model_copy(update={"condition_sets": ["DIG"]})
    report = validate_research_spec(altered, base_dir=root)

    assert "condition_sets do not match the primary sample of the analysis config" in report.errors


def test_research_spec_reports_sample_and_estimand_mismatch() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = load_research_spec(root / "configs" / "research_spec.yml")
    altered = spec.model_copy(
        update={"primary_sample": "management_20plus", "estimands": ["firm_population"]}
    )
    report = validate_research_spec(altered, base_dir=root)

    assert "primary_sample does not match analysis configuration" in report.errors
    assert "estimands do not match analysis configuration" in report.errors


def test_research_spec_requires_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(TypeError, match="research specification root"):
        load_research_spec(path)
