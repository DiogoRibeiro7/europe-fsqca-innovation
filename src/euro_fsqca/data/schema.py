"""Schema inspection used before mapping a new WBES release."""

from __future__ import annotations

import pandas as pd


def schema_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a compact variable audit without exposing case-level values."""
    rows: list[dict[str, object]] = []
    n_rows = len(frame)
    for column in frame.columns:
        series = frame[column]
        rows.append(
            {
                "column": str(column),
                "dtype": str(series.dtype),
                "n_non_missing": int(series.notna().sum()),
                "missing_share": float(series.isna().mean()) if n_rows else 0.0,
                "n_unique": int(series.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)
