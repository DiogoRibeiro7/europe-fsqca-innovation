"""Core fuzzy-set operations and QCA fit parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Fit:
    """Set-theoretic fit parameters for sufficiency or necessity."""

    consistency: float
    coverage: float
    pri: float | None = None


def fuzzy_not(values: pd.Series | np.ndarray) -> np.ndarray:
    """Return fuzzy-set negation as one minus membership."""
    arr = np.asarray(values, dtype=float)
    return 1.0 - arr


def fuzzy_and(*values: pd.Series | np.ndarray) -> np.ndarray:
    """Return fuzzy conjunction using the minimum t-norm."""
    if not values:
        raise ValueError("fuzzy_and requires at least one operand")
    arrays = [np.asarray(value, dtype=float) for value in values]
    return cast(np.ndarray, np.minimum.reduce(arrays))


def fuzzy_or(*values: pd.Series | np.ndarray) -> np.ndarray:
    """Return fuzzy disjunction using the maximum s-norm."""
    if not values:
        raise ValueError("fuzzy_or requires at least one operand")
    arrays = [np.asarray(value, dtype=float) for value in values]
    return cast(np.ndarray, np.maximum.reduce(arrays))


def _aligned(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    weights: pd.Series | np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return pairwise-complete memberships and matching case weights."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.shape != y_arr.shape:
        raise ValueError("set memberships must have the same length")
    if weights is None:
        w_arr = np.ones_like(x_arr, dtype=float)
    else:
        w_arr = np.asarray(weights, dtype=float)
        if w_arr.shape != x_arr.shape:
            raise ValueError("weights must have the same length as set memberships")
    valid = ~(np.isnan(x_arr) | np.isnan(y_arr) | np.isnan(w_arr))
    return x_arr[valid], y_arr[valid], w_arr[valid]


def sufficiency_fit(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    *,
    weights: pd.Series | np.ndarray | None = None,
) -> Fit:
    """Compute fuzzy sufficiency consistency, coverage, and PRI.

    Cases missing either set are excluded pairwise. With survey weights the
    estimator becomes ``sum_i w_i min(X_i, Y_i) / sum_i w_i X_i`` and the
    statements refer to the weighted population rather than to the sample.
    """
    x_valid, y_valid, w_valid = _aligned(x, y, weights)
    denominator = float((w_valid * x_valid).sum())
    if len(x_valid) == 0 or np.isclose(denominator, 0.0):
        return Fit(float("nan"), float("nan"), float("nan"))

    intersection = float((w_valid * np.minimum(x_valid, y_valid)).sum())
    contradiction = float((w_valid * np.minimum(x_valid, 1.0 - y_valid)).sum())
    outcome_total = float((w_valid * y_valid).sum())
    consistency = intersection / denominator
    coverage = intersection / outcome_total if not np.isclose(outcome_total, 0.0) else float("nan")
    pri_denominator = denominator - contradiction
    pri = (
        (intersection - contradiction) / pri_denominator if pri_denominator > 0 else float("nan")
    )
    return Fit(consistency=consistency, coverage=coverage, pri=pri)


def necessity_fit(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    *,
    weights: pd.Series | np.ndarray | None = None,
) -> Fit:
    """Compute fuzzy necessity consistency and coverage."""
    x_valid, y_valid, w_valid = _aligned(x, y, weights)
    if len(x_valid) == 0:
        return Fit(float("nan"), float("nan"))
    intersection = float((w_valid * np.minimum(x_valid, y_valid)).sum())
    condition_total = float((w_valid * x_valid).sum())
    outcome_total = float((w_valid * y_valid).sum())
    consistency = (
        intersection / outcome_total if not np.isclose(outcome_total, 0.0) else float("nan")
    )
    coverage = (
        intersection / condition_total if not np.isclose(condition_total, 0.0) else float("nan")
    )
    return Fit(consistency=consistency, coverage=coverage)


def configuration_membership(frame: pd.DataFrame, literals: dict[str, bool]) -> pd.Series:
    """Compute membership in a conjunctural configuration.

    A literal value of ``True`` means presence; ``False`` means negation.
    """
    if not literals:
        return pd.Series(np.ones(len(frame), dtype=float), index=frame.index)
    operands: list[np.ndarray] = []
    for condition, present in literals.items():
        if condition not in frame.columns:
            raise KeyError(f"missing calibrated condition: {condition}")
        values = frame[condition].to_numpy(dtype=float)
        operands.append(values if present else 1.0 - values)
    return pd.Series(fuzzy_and(*operands), index=frame.index)
