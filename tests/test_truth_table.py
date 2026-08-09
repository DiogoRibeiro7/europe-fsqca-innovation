from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.minimize import minimize_truth_table
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table


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
