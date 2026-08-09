"""Input/output helpers for WBES-style microdata files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path: str | Path) -> pd.DataFrame:
    """Read a supported tabular format."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    if suffix == ".dta":
        return pd.read_stata(source, convert_categoricals=False)
    if suffix in {".sav", ".zsav"}:
        return pd.read_spss(source)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(source)
    raise ValueError(f"unsupported data format: {suffix}")


def write_table(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a table according to its extension."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(target, index=False)
        return
    if suffix in {".parquet", ".pq"}:
        frame.to_parquet(target, index=False)
        return
    raise ValueError(f"unsupported output format: {suffix}")
