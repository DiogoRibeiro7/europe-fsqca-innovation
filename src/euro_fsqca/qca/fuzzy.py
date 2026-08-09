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


def sufficiency_fit(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> Fit:
    """Compute fuzzy sufficiency consistency, coverage, and PRI.

    Cases missing either set are excluded pairwise.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x_arr) | np.isnan(y_arr))
    x_valid = x_arr[valid]
    y_valid = y_arr[valid]
    if len(x_valid) == 0 or np.isclose(x_valid.sum(), 0.0):
        return Fit(float("nan"), float("nan"), float("nan"))

    intersection = np.minimum(x_valid, y_valid)
    contradiction = np.minimum(x_valid, 1.0 - y_valid)
    consistency = float(intersection.sum() / x_valid.sum())
    coverage = (
        float(intersection.sum() / y_valid.sum())
        if not np.isclose(y_valid.sum(), 0.0)
        else float("nan")
    )
    denominator = x_valid.sum() - contradiction.sum()
    pri = (
        float((intersection.sum() - contradiction.sum()) / denominator)
        if denominator > 0
        else float("nan")
    )
    return Fit(consistency=consistency, coverage=coverage, pri=pri)


def necessity_fit(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> Fit:
    """Compute fuzzy necessity consistency and coverage."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x_arr) | np.isnan(y_arr))
    x_valid = x_arr[valid]
    y_valid = y_arr[valid]
    if len(x_valid) == 0:
        return Fit(float("nan"), float("nan"))
    intersection = np.minimum(x_valid, y_valid)
    consistency = (
        float(intersection.sum() / y_valid.sum())
        if not np.isclose(y_valid.sum(), 0.0)
        else float("nan")
    )
    coverage = (
        float(intersection.sum() / x_valid.sum())
        if not np.isclose(x_valid.sum(), 0.0)
        else float("nan")
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
