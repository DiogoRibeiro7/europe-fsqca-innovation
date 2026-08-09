"""Python-to-R QCA parity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

ParityStatus = Literal["PASS", "TOLERANCE_DIFFERENCE", "STRUCTURAL_DIFFERENCE", "FAIL"]


@dataclass(frozen=True)
class ParityTolerance:
    """Numerical tolerances for Python-to-R comparisons."""

    consistency: float = 1e-6
    coverage: float = 1e-6
    pri: float = 1e-6


def compare_qca_outputs(
    python: pd.DataFrame,
    r: pd.DataFrame,
    *,
    key_columns: list[str],
    metric_columns: list[str],
    tolerance: float = 1e-6,
) -> pd.DataFrame:
    """Compare machine-readable Python and R QCA outputs."""
    missing_python = set(key_columns + metric_columns) - set(python.columns)
    missing_r = set(key_columns + metric_columns) - set(r.columns)
    if missing_python:
        raise KeyError(f"missing Python columns: {sorted(missing_python)}")
    if missing_r:
        raise KeyError(f"missing R columns: {sorted(missing_r)}")

    merged = python.merge(
        r,
        on=key_columns,
        how="outer",
        suffixes=("_python", "_r"),
        indicator=True,
    )
    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        key = {column: row[column] for column in key_columns}
        if row["_merge"] != "both":
            rows.append({**key, "metric": "", "status": "STRUCTURAL_DIFFERENCE", "difference": ""})
            continue
        for metric in metric_columns:
            left = float(row[f"{metric}_python"])
            right = float(row[f"{metric}_r"])
            difference = abs(left - right)
            status: ParityStatus = "PASS" if difference <= tolerance else "TOLERANCE_DIFFERENCE"
            rows.append(
                {
                    **key,
                    "metric": metric,
                    "status": status,
                    "difference": difference,
                }
            )
    return pd.DataFrame(rows)


def parity_status_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    """Count comparison rows by parity status."""
    if comparison.empty:
        return pd.DataFrame(columns=["status", "n"])
    return (
        comparison.groupby("status", dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values("status")
        .reset_index(drop=True)
    )
