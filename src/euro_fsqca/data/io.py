"""Input/output helpers for WBES-style microdata files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

#: Formats that carry variable and value labels alongside the data.
LABELLED_FORMATS = {".dta", ".sav", ".zsav"}


@dataclass(frozen=True)
class TableMetadata:
    """Variable and value labels recovered from a labelled source file.

    A WBES variable name says almost nothing. ``wk2`` and ``h1`` are only
    interpretable through the question text the release carries as a variable
    label, and their numeric codes only through the value labels. Mapping a
    variable on the strength of its name alone is the failure this exists to
    prevent.
    """

    column_labels: dict[str, str] = field(default_factory=dict)
    value_labels: dict[str, dict[object, str]] = field(default_factory=dict)
    missing_ranges: dict[str, list[object]] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        """Return whether the source carried any labels at all."""
        return bool(self.column_labels or self.value_labels)


@dataclass(frozen=True)
class LabelledTable:
    """A source table together with whatever metadata the format preserved."""

    frame: pd.DataFrame
    metadata: TableMetadata


def read_table_with_metadata(path: str | Path) -> LabelledTable:
    """Read a source file, preserving variable and value labels where present.

    Stata and SPSS files are read through ``pyreadstat`` so that question text
    and code meanings survive. CSV and Parquet carry no such metadata, and are
    returned with an empty label set rather than with invented ones.
    """
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in LABELLED_FORMATS:
        return LabelledTable(frame=read_table(source), metadata=TableMetadata())

    import pyreadstat

    reader = pyreadstat.read_dta if suffix == ".dta" else pyreadstat.read_sav
    frame, meta = reader(str(source), apply_value_formats=False)
    return LabelledTable(
        frame=frame,
        metadata=TableMetadata(
            column_labels={
                str(name): str(label)
                for name, label in (meta.column_names_to_labels or {}).items()
                if label
            },
            value_labels={
                str(name): {code: str(label) for code, label in mapping.items()}
                for name, mapping in (meta.variable_value_labels or {}).items()
            },
            missing_ranges={
                str(name): list(values)
                for name, values in (getattr(meta, "missing_ranges", None) or {}).items()
            },
        ),
    )


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
