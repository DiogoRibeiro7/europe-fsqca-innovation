from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.minimize import minimize_truth_table
from euro_fsqca.qca.truth_table import (
    TruthTableThresholds,
    build_truth_table,
    contradictory_rows,
    truth_table_diagnostics,
)


def test_truth_table_and_minimization() -> None:
    frame = pd.DataFrame(
        {
            "A": [0.9, 0.85, 0.1, 0.15],
            "B": [0.9, 0.1, 0.9, 0.1],
            "Y": [0.95, 0.90, 0.10, 0.05],
        }
    )
    table = build_truth_table(
        frame,
        conditions=["A", "B"],
        outcome="Y",
        thresholds=TruthTableThresholds(frequency=1, consistency=0.80, pri=0.50),
    )
    conservative = minimize_truth_table(table, conditions=["A", "B"], kind="conservative")
    assert "A" in conservative.expression


def test_truth_table_reports_contradictory_rows() -> None:
    frame = pd.DataFrame(
        {
            "A": [0.9, 0.8, 0.1],
            "B": [0.9, 0.8, 0.1],
            "Y": [0.1, 0.2, 0.9],
        }
    )
    thresholds = TruthTableThresholds(frequency=2, consistency=0.8, pri=0.5)
    table = build_truth_table(frame, conditions=["A", "B"], outcome="Y", thresholds=thresholds)

    contradictions = contradictory_rows(table, thresholds=thresholds)
    diagnostics = truth_table_diagnostics(table, thresholds=thresholds)

    count = diagnostics.loc[
        diagnostics["metric"] == "contradictory_rows",
        "value",
    ].astype(int).iloc[0]
    assert contradictions.shape[0] == 1
    assert count == 1
