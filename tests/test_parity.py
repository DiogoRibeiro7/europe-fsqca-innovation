from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.analysis.parity import (
    canonical_configuration,
    compare_qca_outputs,
    compare_solution_terms,
    load_python_solution_terms,
    load_r_solution_terms,
    parity_passed,
    parity_status_summary,
)

CONDITIONS = ["DIG", "HC", "FIN"]


def test_canonical_configuration_accepts_both_negation_notations() -> None:
    assert canonical_configuration("HC*DIG", CONDITIONS) == "DIG*HC"
    assert canonical_configuration("~HC*DIG", CONDITIONS) == "DIG*~HC"
    # The R QCA package writes absence in lowercase under some settings.
    assert canonical_configuration("hc*DIG", CONDITIONS) == "DIG*~HC"


def test_compare_solution_terms_matches_engines_term_by_term() -> None:
    python = pd.DataFrame(
        {
            "solution": ["conservative", "conservative"],
            "configuration": ["DIG*HC", "DIG*~FIN"],
            "consistency": [0.91, 0.85],
            "coverage": [0.40, 0.22],
            "pri": [0.80, 0.70],
        }
    )
    r = pd.DataFrame(
        {
            "solution": ["conservative", "conservative"],
            "configuration": ["HC*DIG", "dig*fin"],
            "consistency": [0.91, 0.85],
            "coverage": [0.40, 0.22],
            "pri": [0.80, 0.70],
        }
    )
    r["configuration"] = r["configuration"].map(
        lambda value: canonical_configuration(value, CONDITIONS)
    )
    python["configuration"] = python["configuration"].map(
        lambda value: canonical_configuration(value, CONDITIONS)
    )

    comparison = compare_solution_terms(python, r)

    matched = comparison[comparison["configuration"] == "DIG*HC"]
    assert set(matched["status"]) == {"PASS"}
    # The second term differs structurally: ~FIN in Python versus ~DIG*~FIN in R.
    assert "STRUCTURAL_DIFFERENCE" in set(comparison["status"])
    assert not parity_passed(comparison)


def test_compare_solution_terms_flags_metric_disagreement() -> None:
    python = pd.DataFrame(
        {"solution": ["conservative"], "configuration": ["DIG*HC"], "consistency": [0.91]}
    )
    r = pd.DataFrame(
        {"solution": ["conservative"], "configuration": ["DIG*HC"], "consistency": [0.80]}
    )

    comparison = compare_solution_terms(python, r, metrics=["consistency"])

    assert comparison.loc[0, "status"] == "TOLERANCE_DIFFERENCE"


def test_load_engine_outputs_normalises_configurations(tmp_path: Path) -> None:
    python_path = tmp_path / "python_terms.csv"
    r_path = tmp_path / "r_terms.csv"
    pd.DataFrame(
        {
            "solution": ["conservative", "conservative"],
            "estimand": ["unweighted", "firm_population"],
            "configuration": ["HC*DIG", "HC*DIG"],
            "consistency": [0.9, 0.7],
            "coverage": [0.3, 0.3],
            "pri": [0.8, 0.6],
        }
    ).to_csv(python_path, index=False)
    pd.DataFrame(
        {
            "solution": ["conservative"],
            "configuration": ["DIG*HC"],
            "consistency": [0.9],
            "raw_coverage": [0.3],
            "pri": [0.8],
        }
    ).to_csv(r_path, index=False)

    python_terms = load_python_solution_terms(python_path, CONDITIONS)
    r_terms = load_r_solution_terms(r_path, CONDITIONS)

    # R has no survey weights, so parity is checked against the unweighted run.
    assert list(python_terms["estimand"]) == ["unweighted"]
    assert r_terms.loc[0, "coverage"] == 0.3
    assert parity_passed(compare_solution_terms(python_terms, r_terms))


def test_compare_qca_outputs_passes_within_tolerance() -> None:
    python = pd.DataFrame({"row": ["11"], "consistency": [0.9000001]})
    r = pd.DataFrame({"row": ["11"], "consistency": [0.9000002]})

    result = compare_qca_outputs(
        python,
        r,
        key_columns=["row"],
        metric_columns=["consistency"],
        tolerance=1e-5,
    )

    assert result.loc[0, "status"] == "PASS"


def test_compare_qca_outputs_flags_structure_difference() -> None:
    python = pd.DataFrame({"row": ["11"], "consistency": [0.9]})
    r = pd.DataFrame({"row": ["10"], "consistency": [0.9]})

    result = compare_qca_outputs(
        python,
        r,
        key_columns=["row"],
        metric_columns=["consistency"],
    )

    assert set(result["status"]) == {"STRUCTURAL_DIFFERENCE"}


def test_parity_status_summary_counts_statuses() -> None:
    comparison = pd.DataFrame({"status": ["PASS", "PASS", "FAIL"]})

    summary = parity_status_summary(comparison)

    assert dict(zip(summary["status"], summary["n"], strict=True)) == {"FAIL": 1, "PASS": 2}
