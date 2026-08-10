"""Survey-design handling for weighted configurational analysis.

The World Bank Enterprise Surveys are stratified probability samples that
deliberately over-sample some size x sector x location strata. Inclusion
probabilities therefore differ across establishments and population inference
requires the published sampling weights.

Three estimands are supported. ``unweighted`` is the conventional
case-oriented QCA estimand in which every sampled establishment counts once.
``firm_population`` uses the published weights, so set-theoretic statements
refer to the population of establishments in the sampling frame.
``equal_country`` rescales the published weights so every country contributes
the same aggregate weight, which prevents large member states from dominating
a pooled European solution.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

WeightScheme = Literal["unweighted", "firm_population", "equal_country"]

WEIGHT_SCHEMES: tuple[WeightScheme, ...] = ("unweighted", "firm_population", "equal_country")

#: Column written by the pipeline holding the resolved analysis weight.
ANALYSIS_WEIGHT_COLUMN = "analysis_weight"


def resolve_weights(
    frame: pd.DataFrame,
    *,
    scheme: WeightScheme,
    weight_column: str | None = None,
    country_column: str = "country",
    normalise: bool = True,
) -> pd.Series:
    """Return analysis weights for one estimand.

    ``normalise`` rescales weights to sum to the number of cases so that
    weighted row frequencies stay on the same scale as raw case counts.
    """
    if scheme not in WEIGHT_SCHEMES:
        raise ValueError(f"unknown weight scheme: {scheme}")
    n_cases = len(frame)
    if scheme == "unweighted":
        return pd.Series(np.ones(n_cases, dtype=float), index=frame.index, name="weight")

    if weight_column is None:
        raise ValueError(f"weight scheme {scheme!r} requires a survey weight column")
    if weight_column not in frame.columns:
        raise KeyError(f"missing survey weight column: {weight_column}")

    raw = pd.to_numeric(frame[weight_column], errors="coerce")
    invalid = raw.isna() | (raw <= 0)
    if bool(invalid.any()):
        raise ValueError(
            f"survey weight column {weight_column!r} has "
            f"{int(invalid.sum())} missing or non-positive values; "
            "resolve them in harmonisation before analysis"
        )
    weights = raw.astype(float)

    if scheme == "equal_country":
        if country_column not in frame.columns:
            raise KeyError(f"missing country column: {country_column}")
        country = frame[country_column].astype(str)
        totals = weights.groupby(country).transform("sum")
        n_countries = int(country.nunique())
        weights = weights / totals * (n_cases / n_countries)

    if normalise and n_cases:
        total = float(weights.sum())
        if np.isclose(total, 0.0):
            raise ValueError("resolved weights sum to zero")
        weights = weights / total * n_cases
    return pd.Series(weights.to_numpy(dtype=float), index=frame.index, name="weight")


def effective_sample_size(weights: pd.Series | np.ndarray) -> float:
    """Return Kish's effective sample size ``(sum w)^2 / sum w^2``.

    Unequal weights reduce the information content of a sample. Truth-table
    frequency cutoffs applied to a weighted sum of establishments would
    otherwise credit an over-sampled stratum with more evidence than it holds.
    """
    values = np.asarray(weights, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return 0.0
    squared = float(np.square(values).sum())
    if np.isclose(squared, 0.0):
        return 0.0
    return float(np.square(values.sum()) / squared)


def design_effect(weights: pd.Series | np.ndarray) -> float:
    """Return the weighting design effect ``n / n_effective``."""
    values = np.asarray(weights, dtype=float)
    values = values[~np.isnan(values)]
    n_eff = effective_sample_size(values)
    if np.isclose(n_eff, 0.0):
        return float("nan")
    return float(values.size / n_eff)


def weight_diagnostics(
    frame: pd.DataFrame,
    *,
    weights: pd.Series,
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Summarise weight concentration overall and within grouping columns."""
    rows: list[dict[str, object]] = [_weight_row("total", "all", weights)]
    for column in group_columns or []:
        if column not in frame.columns:
            continue
        for group, index in frame.groupby(column, dropna=False, observed=True).groups.items():
            rows.append(_weight_row(column, str(group), weights.loc[index]))
    return pd.DataFrame(rows)


def weighted_share(values: pd.Series | np.ndarray, weights: pd.Series | np.ndarray) -> float:
    """Return the weighted mean of a numeric or boolean series."""
    numeric = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    valid = ~(np.isnan(numeric) | np.isnan(w))
    if not valid.any() or np.isclose(w[valid].sum(), 0.0):
        return float("nan")
    return float(np.average(numeric[valid], weights=w[valid]))


def _weight_row(scope: str, group: str, weights: pd.Series) -> dict[str, object]:
    values = weights.to_numpy(dtype=float)
    total = float(values.sum()) if values.size else 0.0
    return {
        "scope": scope,
        "group": group,
        "n_cases": int(values.size),
        "sum_weight": total,
        "mean_weight": float(values.mean()) if values.size else float("nan"),
        "min_weight": float(values.min()) if values.size else float("nan"),
        "max_weight": float(values.max()) if values.size else float("nan"),
        "cv_weight": _coefficient_of_variation(values),
        "effective_sample_size": effective_sample_size(values),
        "design_effect": design_effect(values),
    }


def _coefficient_of_variation(values: np.ndarray) -> float:
    if values.size == 0:
        return float("nan")
    mean = float(values.mean())
    if np.isclose(mean, 0.0):
        return float("nan")
    return float(values.std(ddof=0) / mean)
