from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.config import load_config
from euro_fsqca.expectations import (
    ExpectationError,
    compare_with_config,
    load_expectations,
)
from euro_fsqca.readiness import FATAL, assess_readiness

REGISTER = Path("configs/directional_expectations.yml")


def test_project_register_agrees_with_the_analysis_configuration() -> None:
    register = load_expectations(REGISTER)
    config = load_config("configs/analysis.yml")

    # The canonical R engine reads the polarity from the analysis config, so a
    # register that disagreed would document expectations that were never used.
    assert compare_with_config(register, config) == []


def test_project_register_is_not_yet_frozen() -> None:
    register = load_expectations(REGISTER)

    assert not register.frozen
    assert register.provisional_conditions
    # EXTK asserts no direction while its construct bundles three different things.
    assert register.unconstrained_conditions == ["EXTK"]


def test_disagreement_with_the_configuration_is_detected() -> None:
    register = load_expectations(REGISTER)
    config = load_config("configs/analysis.yml")
    config.conditions["DIG"].direction = "absent"

    problems = compare_with_config(register, config)

    assert any("DIG" in problem for problem in problems)


def test_directional_expectation_requires_a_justification(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\nexpectations:\n  DIG:\n    polarity: present\n", encoding="utf-8"
    )

    with pytest.raises(ExpectationError, match="requires a justification"):
        load_expectations(path)


def test_unconstrained_expectation_needs_no_justification(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\nexpectations:\n  DIG:\n    polarity: unconstrained\n", encoding="utf-8"
    )

    register = load_expectations(path)

    assert register.expectations["DIG"].direction == "either"


def test_unknown_polarity_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\nexpectations:\n  DIG:\n    polarity: positive\n", encoding="utf-8"
    )

    with pytest.raises(ExpectationError, match="present, absent or unconstrained"):
        load_expectations(path)


def test_readiness_blocks_an_unfrozen_register() -> None:
    root = Path(__file__).resolve().parents[1]

    report = assess_readiness(
        config_path=root / "configs" / "analysis.yml",
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=root / "data" / "manifest.csv",
        raw_root=root / "data" / "raw",
    )

    row = report[report["check"] == "directional_expectations"].iloc[0]
    assert row["status"] == FATAL
    assert "not frozen" in row["detail"]
