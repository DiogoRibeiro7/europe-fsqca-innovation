from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.config import load_config
from euro_fsqca.expectations import (
    ExpectationError,
    compare_with_config,
    load_expectations,
    missing_references,
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


def test_five_expectations_are_anchored_and_extk_is_not() -> None:
    register = load_expectations(REGISTER)

    # Anchoring the theory was the part completable without the data.
    assert register.unanchored_conditions == []
    assert register.provisional_conditions == ["EXTK"]
    assert register.expectations["EXTK"].status == "blocked_on_measurement"
    for condition in ["DIG", "HC", "FIN", "INT", "MGT"]:
        assert register.expectations[condition].anchored, condition


def test_every_cited_reference_exists_in_the_bibliography() -> None:
    root = Path(__file__).resolve().parents[1]
    register = load_expectations(REGISTER)

    # A dangling citation is a justification that cannot be checked.
    assert missing_references(register, root / "paper" / "references.bib") == []
    assert register.cited_keys


def test_theoretical_status_requires_a_reference(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\n"
        "expectations:\n"
        "  DIG:\n"
        "    polarity: present\n"
        "    justification: enabling capability\n"
        "    status: theoretical\n",
        encoding="utf-8",
    )

    with pytest.raises(ExpectationError, match="requires at least one reference"):
        load_expectations(path)


def test_unknown_status_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\n"
        "expectations:\n"
        "  DIG:\n"
        "    polarity: present\n"
        "    justification: x\n"
        "    status: obviously_true\n",
        encoding="utf-8",
    )

    with pytest.raises(ExpectationError, match="status must be one of"):
        load_expectations(path)


def test_dangling_citation_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "register.yml"
    path.write_text(
        "outcome: INN\n"
        "expectations:\n"
        "  DIG:\n"
        "    polarity: present\n"
        "    justification: x\n"
        "    status: theoretical\n"
        "    references: [nonexistent2099]\n",
        encoding="utf-8",
    )
    bibliography = tmp_path / "refs.bib"
    bibliography.write_text("@article{cohen1990, title={x}}\n", encoding="utf-8")

    register = load_expectations(path)

    assert missing_references(register, bibliography) == ["nonexistent2099"]


def test_readiness_reports_unanchored_expectations_before_freezing(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = REGISTER.read_text(encoding="utf-8")
    # Demote one anchored expectation to an unsupported assertion.
    weakened = source.replace(
        "    references: [cohen1990]\n    status: theoretical",
        "    references: []\n    status: provisional",
    )
    register_path = tmp_path / "weak.yml"
    register_path.write_text(weakened, encoding="utf-8")
    config_path = tmp_path / "analysis.yml"
    config_path.write_text(
        (root / "configs" / "analysis.yml")
        .read_text(encoding="utf-8")
        .replace(
            "directional_expectations_file: configs/directional_expectations.yml",
            f"directional_expectations_file: {register_path.as_posix()}",
        ),
        encoding="utf-8",
    )

    report = assess_readiness(
        config_path=config_path,
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=root / "data" / "manifest.csv",
        raw_root=root / "data" / "raw",
    )

    row = report[report["check"] == "directional_expectations"].iloc[0]
    assert row["status"] == FATAL
    assert "without a published anchor" in row["detail"]
    assert "HC" in row["detail"]
