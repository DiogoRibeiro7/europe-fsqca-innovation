"""Schema inspection used before mapping a new WBES release."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from euro_fsqca.data.io import read_table
from euro_fsqca.data.provenance import ManifestEntry, load_manifest

SCHEMA_AUDIT_COLUMNS = [
    "source_name",
    "country",
    "survey_year",
    "wbes_version",
    "column",
    "label",
    "dtype",
    "valid_values",
    "missing_value_codes",
    "survey_module",
    "n_non_missing",
    "missing_share",
    "n_unique",
    "availability",
    "presence_count",
    "total_sources",
    "countries_present",
    "years_present",
    "definition_status",
]

POTENTIAL_MISSING_CODES = {
    -9,
    -8,
    -7,
    -6,
    -5,
    -4,
    -3,
    -2,
    -1,
    97,
    98,
    99,
    997,
    998,
    999,
}


@dataclass(frozen=True)
class SchemaDataset:
    """One dataset included in a cross-file schema audit."""

    source_name: str
    country: str
    survey_year: str
    wbes_version: str
    frame: pd.DataFrame
    labels: dict[str, str] | None = None


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


def _json_list(values: Sequence[object]) -> str:
    return json.dumps([str(value) for value in values], ensure_ascii=True)


def _valid_values(series: pd.Series, *, max_values: int) -> str:
    values = series.dropna().unique().tolist()
    if len(values) > max_values:
        return ""
    return _json_list(sorted(values, key=lambda item: str(item)))


def _potential_missing_codes(series: pd.Series) -> str:
    numeric = pd.to_numeric(series, errors="coerce")
    observed = {
        int(value)
        for value in numeric.dropna().unique().tolist()
        if float(value).is_integer() and int(value) in POTENTIAL_MISSING_CODES
    }
    return _json_list(sorted(observed))


def _availability(presence_count: int, total_sources: int) -> str:
    if total_sources == 0 or presence_count == 0:
        return "absent"
    if presence_count == total_sources:
        return "all"
    if presence_count / total_sources >= 0.75:
        return "most"
    return "some"


def schema_audit(datasets: Sequence[SchemaDataset], *, max_values: int = 20) -> pd.DataFrame:
    """Compare column schemas across source datasets."""
    if not datasets:
        return pd.DataFrame(columns=SCHEMA_AUDIT_COLUMNS)

    total_sources = len(datasets)
    all_columns = sorted({str(column) for dataset in datasets for column in dataset.frame.columns})
    presence: dict[str, list[SchemaDataset]] = {
        column: [dataset for dataset in datasets if column in dataset.frame.columns]
        for column in all_columns
    }

    rows: list[dict[str, object]] = []
    for dataset in datasets:
        n_rows = len(dataset.frame)
        labels = dataset.labels or {}
        for column in all_columns:
            present = presence[column]
            presence_count = len(present)
            countries = sorted({source.country for source in present})
            years = sorted({source.survey_year for source in present})
            if column not in dataset.frame.columns:
                rows.append(
                    {
                        "source_name": dataset.source_name,
                        "country": dataset.country,
                        "survey_year": dataset.survey_year,
                        "wbes_version": dataset.wbes_version,
                        "column": column,
                        "label": "",
                        "dtype": "",
                        "valid_values": "",
                        "missing_value_codes": "",
                        "survey_module": "",
                        "n_non_missing": 0,
                        "missing_share": 1.0,
                        "n_unique": 0,
                        "availability": _availability(presence_count, total_sources),
                        "presence_count": presence_count,
                        "total_sources": total_sources,
                        "countries_present": _json_list(countries),
                        "years_present": _json_list(years),
                        "definition_status": "absent_in_source",
                    }
                )
                continue

            series = dataset.frame[column]
            rows.append(
                {
                    "source_name": dataset.source_name,
                    "country": dataset.country,
                    "survey_year": dataset.survey_year,
                    "wbes_version": dataset.wbes_version,
                    "column": column,
                    "label": labels.get(column, ""),
                    "dtype": str(series.dtype),
                    "valid_values": _valid_values(series, max_values=max_values),
                    "missing_value_codes": _potential_missing_codes(series),
                    "survey_module": "",
                    "n_non_missing": int(series.notna().sum()),
                    "missing_share": float(series.isna().mean()) if n_rows else 0.0,
                    "n_unique": int(series.nunique(dropna=True)),
                    "availability": _availability(presence_count, total_sources),
                    "presence_count": presence_count,
                    "total_sources": total_sources,
                    "countries_present": _json_list(countries),
                    "years_present": _json_list(years),
                    "definition_status": "requires_label_review",
                }
            )
    return pd.DataFrame(rows, columns=SCHEMA_AUDIT_COLUMNS)


def schema_audit_from_manifest(
    manifest_path: str | Path,
    *,
    raw_root: str | Path = "data/raw",
    max_values: int = 20,
) -> pd.DataFrame:
    """Load manifest sources and produce a cross-file schema audit."""
    manifest_entries = load_manifest(manifest_path)
    raw_root_path = Path(raw_root)
    datasets: list[SchemaDataset] = []
    for entry in manifest_entries:
        source_path = entry.relative_path
        if not source_path.is_absolute():
            source_path = raw_root_path / source_path
        if not source_path.exists():
            raise FileNotFoundError(f"missing source file: {source_path}")
        datasets.append(_dataset_from_manifest_entry(entry, read_table(source_path)))
    return schema_audit(datasets, max_values=max_values)


def _dataset_from_manifest_entry(entry: ManifestEntry, frame: pd.DataFrame) -> SchemaDataset:
    return SchemaDataset(
        source_name=entry.source_name,
        country=entry.country,
        survey_year=entry.survey_year,
        wbes_version=entry.wbes_version,
        frame=frame,
    )
