from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.data.mapping import (
    MappingValidationError,
    load_variable_mapping,
    mapping_coverage_report,
    validate_variable_mapping,
)


def test_mapping_template_is_valid_but_not_main_ready() -> None:
    mappings = load_variable_mapping(Path("configs/wbes_variable_map.yml"))
    report = validate_variable_mapping(mappings)

    assert report.ok
    assert len(report.unresolved) == 7


def test_mapping_main_ready_requires_verified_constructs() -> None:
    mappings = load_variable_mapping(Path("configs/wbes_variable_map.yml"))
    report = validate_variable_mapping(mappings, require_main_ready=True)

    assert not report.ok
    assert "DIG_raw is not verified" in report.errors[0]


def test_mapping_rejects_unknown_status(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.yml"
    mapping.write_text(
        """
constructs:
  DIG_raw:
    concept: Digital
    verification_status: maybe
    source_variables: []
""",
        encoding="utf-8",
    )

    with pytest.raises(MappingValidationError, match="unknown status"):
        load_variable_mapping(mapping)


def test_mapping_coverage_reports_usable_countries(tmp_path: Path) -> None:
    mapping = tmp_path / "mapping.yml"
    mapping.write_text(
        """
constructs:
  DIG_raw:
    concept: Digital
    verification_status: verified
    source_variables:
      - source_variable: a1
        country: Portugal
        survey_year: "2024"
        question_text_or_label: Uses digital tools
        transformation: direct copy
        missing_value_rule: special codes to missing
        verification_status: verified
""",
        encoding="utf-8",
    )
    mappings = load_variable_mapping(mapping)

    coverage = mapping_coverage_report(mappings)

    assert coverage.loc[0, "countries"] == "Portugal"
    assert bool(coverage.loc[0, "main_ready"])
