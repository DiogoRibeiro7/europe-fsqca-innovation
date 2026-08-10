"""Truth-table construction for calibrated fuzzy-set data."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Literal

import numpy as np
import pandas as pd

from euro_fsqca.qca.fuzzy import configuration_membership, sufficiency_fit
from euro_fsqca.survey import effective_sample_size

FrequencyBasis = Literal["cases", "weighted", "effective"]


@dataclass(frozen=True)
class TruthTableThresholds:
    """Thresholds that determine positive truth-table rows.

    ``frequency_basis`` selects the evidence measure compared against
    ``frequency``. ``cases`` counts sampled establishments, ``weighted`` sums
    survey weights, and ``effective`` uses Kish's effective sample size within
    the row so that an over-sampled stratum cannot buy row inclusion.
    """

    frequency: int
    consistency: float
    pri: float
    frequency_basis: FrequencyBasis = "cases"


def _row_key(bits: tuple[int, ...]) -> str:
    return "".join(str(bit) for bit in bits)


def _row_frequencies(
    crisp: pd.DataFrame,
    conditions: list[str],
    weights: np.ndarray,
) -> dict[tuple[int, ...], dict[str, float]]:
    """Aggregate case counts, weight mass, and effective sample size per row."""
    counts: dict[tuple[int, ...], dict[str, float]] = {}
    keys = list(map(tuple, crisp[conditions].to_numpy(dtype=int)))
    for position, key in enumerate(keys):
        entry = counts.setdefault(key, {"n_cases": 0.0, "sum_weight": 0.0, "sum_sq_weight": 0.0})
        weight = float(weights[position])
        entry["n_cases"] += 1.0
        entry["sum_weight"] += weight
        entry["sum_sq_weight"] += weight * weight
    for entry in counts.values():
        entry["effective"] = (
            entry["sum_weight"] ** 2 / entry["sum_sq_weight"]
            if entry["sum_sq_weight"] > 0
            else 0.0
        )
    return counts


def build_truth_table(
    frame: pd.DataFrame,
    *,
    conditions: list[str],
    outcome: str,
    thresholds: TruthTableThresholds,
    weights: pd.Series | np.ndarray | None = None,
) -> pd.DataFrame:
    """Build all logically possible truth-table rows.

    Case assignment uses fuzzy membership above 0.5 for row frequency. Row fit
    is calculated from fuzzy membership in the complete row configuration. When
    survey weights are supplied, fit parameters and the frequency measure
    selected by ``thresholds.frequency_basis`` are design-aware.
    """
    required = [*conditions, outcome]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"missing calibrated columns: {missing}")

    if weights is None:
        weight_series = pd.Series(np.ones(len(frame), dtype=float), index=frame.index)
    elif isinstance(weights, pd.Series):
        weight_series = weights.astype(float)
    else:
        weight_series = pd.Series(np.asarray(weights, dtype=float), index=frame.index)

    complete = frame[required].notna().all(axis=1) & weight_series.notna()
    valid = frame.loc[complete, required].copy()
    valid_weights = weight_series.loc[complete].to_numpy(dtype=float)
    crisp = (valid[conditions] > 0.5).astype(int)
    counts = _row_frequencies(crisp, conditions, valid_weights)
    outcome_values = valid[outcome].to_numpy(dtype=float)

    rows: list[dict[str, object]] = []
    for bits in product([0, 1], repeat=len(conditions)):
        literals = {condition: bool(bit) for condition, bit in zip(conditions, bits, strict=True)}
        membership = configuration_membership(valid, literals)
        fit = sufficiency_fit(membership.to_numpy(), outcome_values, weights=valid_weights)
        entry = counts.get(bits, {"n_cases": 0.0, "sum_weight": 0.0, "effective": 0.0})
        frequency = int(entry["n_cases"])
        weighted_frequency = float(entry["sum_weight"])
        effective_frequency = float(entry["effective"])
        evidence = {
            "cases": float(frequency),
            "weighted": weighted_frequency,
            "effective": effective_frequency,
        }[thresholds.frequency_basis]
        positive = bool(
            evidence >= thresholds.frequency
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
                "weighted_frequency": weighted_frequency,
                "effective_frequency": effective_frequency,
                "frequency_basis": thresholds.frequency_basis,
                "frequency_evidence": evidence,
                "consistency": fit.consistency,
                "coverage": fit.coverage,
                "pri": fit.pri,
                "observed": frequency > 0,
                # QCA::truthTable codes a row with fewer than n.cut cases as a
                # logical remainder, not as a negative case. A row nobody
                # observed enough of is not evidence that the outcome is absent.
                "remainder": bool(evidence < thresholds.frequency),
                "positive": positive,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _evidence(truth_table: pd.DataFrame) -> pd.Series:
    """Return the frequency measure used to include rows."""
    if "frequency_evidence" in truth_table.columns:
        return truth_table["frequency_evidence"].astype(float)
    return truth_table["frequency"].astype(float)


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
        & (_evidence(truth_table) >= thresholds.frequency)
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
    metrics = [
        {"metric": "total_rows", "value": float(len(truth_table))},
        {"metric": "observed_rows", "value": float(observed.sum())},
        {"metric": "positive_rows", "value": float(positive.sum())},
        {"metric": "contradictory_rows", "value": float(len(contradictions))},
        {"metric": "logical_remainders", "value": float((~observed).sum())},
    ]
    if "weighted_frequency" in truth_table.columns:
        weights = truth_table.loc[observed, "weighted_frequency"].to_numpy(dtype=float)
        metrics.extend(
            [
                {"metric": "observed_weight_mass", "value": float(weights.sum())},
                {
                    "metric": "observed_effective_sample_size",
                    "value": effective_sample_size(weights),
                },
                {
                    "metric": "positive_row_case_share",
                    "value": _case_share(truth_table, positive),
                },
                {
                    "metric": "positive_row_weight_share",
                    "value": _weight_share(truth_table, positive),
                },
            ]
        )
    return pd.DataFrame(metrics)


def _case_share(truth_table: pd.DataFrame, mask: pd.Series) -> float:
    total = float(truth_table["frequency"].astype(float).sum())
    if np.isclose(total, 0.0):
        return float("nan")
    return float(truth_table.loc[mask, "frequency"].astype(float).sum() / total)


def _weight_share(truth_table: pd.DataFrame, mask: pd.Series) -> float:
    total = float(truth_table["weighted_frequency"].astype(float).sum())
    if np.isclose(total, 0.0):
        return float("nan")
    return float(truth_table.loc[mask, "weighted_frequency"].astype(float).sum() / total)
