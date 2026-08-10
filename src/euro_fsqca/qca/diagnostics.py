"""Truth-table diversity and difficult-row diagnostics."""

from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.truth_table import TruthTableThresholds, contradictory_rows


def diversity_diagnostics(
    truth_table: pd.DataFrame,
    *,
    thresholds: TruthTableThresholds,
) -> pd.DataFrame:
    """Summarise limited diversity, contradictions, and logical remainders."""
    observed = truth_table["observed"].astype(bool)
    positive = truth_table["positive"].astype(bool)
    contradictions = contradictory_rows(truth_table, thresholds=thresholds)
    total_rows = len(truth_table)
    return pd.DataFrame(
        [
            {"metric": "logical_space", "value": total_rows},
            {"metric": "observed_configurations", "value": int(observed.sum())},
            {"metric": "unobserved_configurations", "value": int((~observed).sum())},
            {"metric": "positive_configurations", "value": int(positive.sum())},
            {"metric": "contradictory_configurations", "value": len(contradictions)},
            {
                "metric": "limited_diversity_share",
                "value": float((~observed).sum() / total_rows) if total_rows else 0.0,
            },
        ]
    )


def difficult_rows(
    truth_table: pd.DataFrame,
    *,
    thresholds: TruthTableThresholds,
    tolerance: float = 0.02,
) -> pd.DataFrame:
    """Return rows near the consistency or PRI decision thresholds."""
    mask = (
        (truth_table["consistency"].astype(float) - thresholds.consistency).abs() <= tolerance
    ) | ((truth_table["pri"].astype(float) - thresholds.pri).abs() <= tolerance)
    return truth_table.loc[mask].copy()
