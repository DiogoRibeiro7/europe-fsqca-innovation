"""Construction of transparent pre-calibration composite scores."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

from euro_fsqca.config import CompositeSpec


def build_composite(frame: pd.DataFrame, spec: CompositeSpec) -> pd.Series:
    """Build a configured composite score from observed indicators."""
    missing_columns = [column for column in spec.columns if column not in frame.columns]
    if missing_columns:
        raise KeyError(f"missing composite columns: {missing_columns}")

    data = frame[spec.columns].apply(pd.to_numeric, errors="coerce")
    skipna = spec.missing == "available"

    if spec.aggregation == "mean":
        return cast(pd.Series, data.mean(axis=1, skipna=skipna))
    if spec.aggregation == "min":
        return cast(pd.Series, data.min(axis=1, skipna=skipna))
    if spec.aggregation == "max":
        return cast(pd.Series, data.max(axis=1, skipna=skipna))
    if spec.aggregation == "weighted_mean":
        assert spec.weights is not None
        weights = np.asarray(spec.weights, dtype=float)
        if np.isclose(weights.sum(), 0.0):
            raise ValueError("composite weights must not sum to zero")
        values = data.to_numpy(dtype=float)
        if spec.missing == "complete":
            complete = ~np.isnan(values).any(axis=1)
            result = np.full(len(data), np.nan, dtype=float)
            result[complete] = np.average(values[complete], axis=1, weights=weights)
            return pd.Series(result, index=frame.index)

        observed = ~np.isnan(values)
        weighted_values = np.where(observed, values * weights, 0.0)
        denominators = np.where(observed, weights, 0.0).sum(axis=1)
        numerators = weighted_values.sum(axis=1)
        result = np.divide(
            numerators,
            denominators,
            out=np.full_like(numerators, np.nan, dtype=float),
            where=~np.isclose(denominators, 0.0),
        )
        return pd.Series(result, index=frame.index)
    raise AssertionError("unreachable aggregation")
