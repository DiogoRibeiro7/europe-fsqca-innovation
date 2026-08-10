"""Necessary-condition diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from euro_fsqca.qca.fuzzy import necessity_fit


def necessity_table(
    frame: pd.DataFrame,
    *,
    conditions: list[str],
    outcome: str,
    weights: pd.Series | np.ndarray | None = None,
) -> pd.DataFrame:
    """Evaluate presence and absence of each condition as necessary for the outcome."""
    rows: list[dict[str, object]] = []
    y = frame[outcome].to_numpy(dtype=float)
    weight_values = None if weights is None else np.asarray(weights, dtype=float)
    for condition in conditions:
        x = frame[condition].to_numpy(dtype=float)
        for negated, values in ((False, x), (True, 1.0 - x)):
            fit = necessity_fit(values, y, weights=weight_values)
            rows.append(
                {
                    "condition": condition,
                    "negated": negated,
                    "label": f"~{condition}" if negated else condition,
                    "n": int(frame[[condition, outcome]].dropna().shape[0]),
                    "weighted": weight_values is not None,
                    "consistency": fit.consistency,
                    "coverage": fit.coverage,
                    "trivial": bool(fit.consistency >= 0.9 and fit.coverage < 0.5),
                }
            )
    return pd.DataFrame(rows).sort_values("consistency", ascending=False, ignore_index=True)
