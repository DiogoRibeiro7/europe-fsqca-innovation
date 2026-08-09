"""Truth-table construction for calibrated fuzzy-set data."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from euro_fsqca.qca.fuzzy import configuration_membership, sufficiency_fit


@dataclass(frozen=True)
class TruthTableThresholds:
    """Thresholds that determine positive truth-table rows."""

    frequency: int
    consistency: float
    pri: float


def _row_key(bits: tuple[int, ...]) -> str:
    return "".join(str(bit) for bit in bits)


def build_truth_table(
    frame: pd.DataFrame,
    *,
    conditions: list[str],
    outcome: str,
    thresholds: TruthTableThresholds,
) -> pd.DataFrame:
    """Build all logically possible truth-table rows.

    Case assignment uses fuzzy membership above 0.5 for row frequency. Row fit
    is calculated from fuzzy membership in the complete row configuration.
    """
    required = [*conditions, outcome]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"missing calibrated columns: {missing}")

    valid = frame[required].dropna().copy()
    crisp = (valid[conditions] > 0.5).astype(int)
    counts = crisp.value_counts(sort=False).to_dict()

    rows: list[dict[str, object]] = []
    for bits in product([0, 1], repeat=len(conditions)):
        literals = {condition: bool(bit) for condition, bit in zip(conditions, bits, strict=True)}
        membership = configuration_membership(valid, literals)
        fit = sufficiency_fit(membership.to_numpy(), valid[outcome].to_numpy(dtype=float))
        frequency = int(counts.get(bits, 0))
        positive = bool(
            frequency >= thresholds.frequency
            and fit.consistency >= thresholds.consistency
            and fit.pri is not None
            and fit.pri >= thresholds.pri
        )
        row: dict[str, object] = {
            condition: bit for condition, bit in zip(conditions, bits, strict=True)
        }
        row.update(
            {
                "row": _row_key(bits),
                "frequency": frequency,
                "consistency": fit.consistency,
                "coverage": fit.coverage,
                "pri": fit.pri,
                "observed": frequency > 0,
                "positive": positive,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def contradictory_rows(
    truth_table: pd.DataFrame,
    *,
    thresholds: TruthTableThresholds,
) -> pd.DataFrame:
    """Return observed rows with enough cases but insufficient outcome consistency."""
    required = {"frequency", "consistency", "positive", "observed"}
    missing = required - set(truth_table.columns)
    if missing:
        raise KeyError(f"missing truth-table columns: {sorted(missing)}")
    mask = (
        truth_table["observed"].astype(bool)
        & (truth_table["frequency"].astype(int) >= thresholds.frequency)
        & ~truth_table["positive"].astype(bool)
        & (truth_table["consistency"].astype(float) < thresholds.consistency)
    )
    return truth_table.loc[mask].copy()


def truth_table_diagnostics(
    truth_table: pd.DataFrame,
    *,
    thresholds: TruthTableThresholds,
) -> pd.DataFrame:
    """Summarise observed, positive, contradictory, and remainder rows."""
    required = {"frequency", "positive", "observed"}
    missing = required - set(truth_table.columns)
    if missing:
        raise KeyError(f"missing truth-table columns: {sorted(missing)}")
    observed = truth_table["observed"].astype(bool)
    positive = truth_table["positive"].astype(bool)
    contradictions = contradictory_rows(truth_table, thresholds=thresholds)
    return pd.DataFrame(
        [
            {"metric": "total_rows", "value": int(len(truth_table))},
            {"metric": "observed_rows", "value": int(observed.sum())},
            {"metric": "positive_rows", "value": int(positive.sum())},
            {"metric": "contradictory_rows", "value": int(len(contradictions))},
            {"metric": "logical_remainders", "value": int((~observed).sum())},
        ]
    )
