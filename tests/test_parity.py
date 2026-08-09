from __future__ import annotations

import pandas as pd

from euro_fsqca.analysis.parity import compare_qca_outputs, parity_status_summary


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
