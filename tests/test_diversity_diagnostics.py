from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.diagnostics import difficult_rows, diversity_diagnostics
from euro_fsqca.qca.truth_table import TruthTableThresholds


def test_diversity_diagnostics_counts_rows() -> None:
    table = pd.DataFrame(
        {
            "observed": [True, False],
            "positive": [True, False],
            "frequency": [3, 0],
            "consistency": [0.9, 0.0],
            "pri": [0.8, 0.0],
        }
    )

    result = diversity_diagnostics(
        table,
        thresholds=TruthTableThresholds(frequency=1, consistency=0.8, pri=0.5),
    )

    assert "limited_diversity_share" in set(result["metric"])


def test_difficult_rows_finds_near_thresholds() -> None:
    table = pd.DataFrame({"consistency": [0.79, 0.5], "pri": [0.5, 0.1]})

    result = difficult_rows(
        table,
        thresholds=TruthTableThresholds(frequency=1, consistency=0.8, pri=0.5),
        tolerance=0.02,
    )

    assert result.shape[0] == 1
