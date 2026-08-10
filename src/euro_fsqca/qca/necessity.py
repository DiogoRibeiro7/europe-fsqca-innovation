"""Necessary-condition diagnostics."""

from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.fuzzy import necessity_fit


def necessity_table(frame: pd.DataFrame, *, conditions: list[str], outcome: str) -> pd.DataFrame:
    """Evaluate presence and absence of each condition as necessary for the outcome."""
    rows: list[dict[str, object]] = []
    y = frame[outcome].to_numpy(dtype=float)
    for condition in conditions:
        x = frame[condition].to_numpy(dtype=float)
        for negated, values in ((False, x), (True, 1.0 - x)):
            fit = necessity_fit(values, y)
            rows.append(
                {
                    "condition": condition,
                    "negated": negated,
                    "label": f"~{condition}" if negated else condition,
                    "n": int(frame[[condition, outcome]].dropna().shape[0]),
                    "consistency": fit.consistency,
                    "coverage": fit.coverage,
                    "trivial": bool(fit.consistency >= 0.9 and fit.coverage < 0.5),
                }
            )
    return pd.DataFrame(rows).sort_values("consistency", ascending=False, ignore_index=True)
