"""Ingestion of real WBES source files into one standardised raw table.

Ingestion does three things and nothing else: it reads the source files, it
normalises the *structural* metadata that every release carries under different
names, and it preserves provenance. Analytical variables are passed through
untouched. Recoding, construct construction and calibration happen downstream,
after the schema audit has established what is actually comparable.

Releases differ, so the structural columns are resolved from configured
candidate names rather than guessed. Which candidate matched is recorded for
every source, so the mapping is auditable rather than implicit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from euro_fsqca.data.io import read_table
from euro_fsqca.data.provenance import (
    ManifestEntry,
    compute_sha256,
    load_manifest,
    raise_for_manifest_errors,
    validate_manifest,
)

#: Structural metadata carried through the whole pipeline. These are not
#: analytical variables; they identify the case and describe the sample design.
CANONICAL_METADATA = [
    "establishment_id",
    "country",
    "survey_year",
    "sector",
    "size_class",
    "n_employees",
    "sampling_weight",
    "stratum",
    "region",
]

#: Without these the case cannot be placed in the design and cannot be weighted.
REQUIRED_METADATA = [
    "establishment_id",
    "country",
    "survey_year",
    "sampling_weight",
]

#: Provenance columns added to every ingested row.
PROVENANCE_COLUMNS = ["source_name", "source_file", "source_format"]

MIN_SURVEY_YEAR = 1990
MAX_SURVEY_YEAR = 2100

SUPPORTED_FORMATS = {
    ".csv": "csv",
    ".dta": "stata",
    ".sav": "spss",
    ".zsav": "spss",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".xlsx": "excel",
    ".xls": "excel",
}


class IngestionError(ValueError):
    """Raised when a source file cannot be ingested with usable provenance."""


@dataclass(frozen=True)
class IngestionSpec:
    """Candidate source-column names for each structural metadata field.

    ``default`` applies to every source. ``overrides`` is keyed by manifest
    ``source_name`` for releases that deviate.
    """

    default: dict[str, list[str]] = field(default_factory=dict)
    overrides: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def candidates(self, canonical: str, source_name: str) -> list[str]:
        """Return candidate source columns for one field and one source."""
        override = self.overrides.get(source_name, {})
        if canonical in override:
            return list(override[canonical])
        return list(self.default.get(canonical, []))


@dataclass
class IngestionResult:
    """One standardised raw table plus the record of how it was built."""

    frame: pd.DataFrame
    resolution: pd.DataFrame
    sources: pd.DataFrame


def load_ingestion_spec(path: str | Path) -> IngestionSpec:
    """Load structural-column candidates from YAML."""
    with Path(path).open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise IngestionError("ingestion specification root must be a mapping")
    default = payload.get("default", {})
    overrides = payload.get("overrides", {}) or {}
    if not isinstance(default, dict) or not isinstance(overrides, dict):
        raise IngestionError("ingestion specification must define mappings")
    unknown = set(default) - set(CANONICAL_METADATA)
    if unknown:
        raise IngestionError(f"unknown canonical metadata fields: {sorted(unknown)}")
    return IngestionSpec(
        default={key: list(value) for key, value in default.items()},
        overrides={
            source: {key: list(value) for key, value in mapping.items()}
            for source, mapping in overrides.items()
        },
    )


def detect_format(path: str | Path) -> str:
    """Return the source format implied by the file extension."""
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise IngestionError(f"unsupported source format: {suffix or Path(path).name}")
    return SUPPORTED_FORMATS[suffix]


def resolve_column(
    frame: pd.DataFrame,
    *,
    canonical: str,
    spec: IngestionSpec,
    source_name: str,
) -> str | None:
    """Return the first candidate column present in a source frame."""
    lookup = {str(column).lower(): str(column) for column in frame.columns}
    for candidate in spec.candidates(canonical, source_name):
        match = lookup.get(candidate.lower())
        if match is not None:
            return match
    return None


def standardise_source(
    frame: pd.DataFrame,
    *,
    entry: ManifestEntry,
    spec: IngestionSpec,
    source_format: str,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Attach canonical metadata and provenance without touching analytical data."""
    result = frame.copy()
    resolution: list[dict[str, object]] = []
    for canonical in CANONICAL_METADATA:
        column = resolve_column(
            result, canonical=canonical, spec=spec, source_name=entry.source_name
        )
        resolution.append(
            {
                "source_name": entry.source_name,
                "canonical": canonical,
                "source_column": column or "",
                "resolved": column is not None,
                "required": canonical in REQUIRED_METADATA,
            }
        )
        if column is None:
            continue
        if canonical in result.columns and column != canonical:
            raise IngestionError(
                f"{entry.source_name}: cannot map {column!r} onto {canonical!r} because a "
                "different column already uses that name"
            )
        result[canonical] = result[column]

    # Country and survey year are recorded in the manifest, so a source that
    # does not carry them internally still gets them from provenance.
    if "country" not in result.columns:
        result["country"] = entry.country
    if "survey_year" not in result.columns:
        result["survey_year"] = entry.survey_year

    result["source_name"] = entry.source_name
    result["source_file"] = entry.file_name
    result["source_format"] = source_format

    missing = [name for name in REQUIRED_METADATA if name not in result.columns]
    if missing:
        raise IngestionError(
            f"{entry.source_name}: required metadata could not be resolved: {missing}. "
            "Add the release-specific column names to the ingestion specification."
        )
    _validate_survey_year(result, entry)
    _validate_weight(result, entry)
    return result, resolution


def ingest_manifest(
    manifest_path: str | Path,
    *,
    raw_root: str | Path = "data/raw",
    spec: IngestionSpec,
    verify_checksums: bool = True,
) -> IngestionResult:
    """Read every manifest source into one standardised raw table."""
    entries = load_manifest(manifest_path)
    if not entries:
        raise IngestionError(
            "the data manifest records no source files; acquire the licensed EU-27 "
            "releases before ingestion"
        )
    _reject_duplicate_entries(entries)
    if verify_checksums:
        raise_for_manifest_errors(validate_manifest(manifest_path, root=raw_root))

    root = Path(raw_root)
    frames: list[pd.DataFrame] = []
    resolution: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []
    for entry in entries:
        path = entry.relative_path
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            raise IngestionError(f"missing source file: {path}")
        source_format = detect_format(path)
        raw = read_table(path)
        standardised, resolved = standardise_source(
            raw, entry=entry, spec=spec, source_format=source_format
        )
        frames.append(standardised)
        resolution.extend(resolved)
        sources.append(
            {
                "source_name": entry.source_name,
                "country": entry.country,
                "survey_year": entry.survey_year,
                "wbes_version": entry.wbes_version,
                "source_file": entry.file_name,
                "source_format": source_format,
                "n_rows": len(standardised),
                "n_columns": int(standardised.shape[1]),
                "checksum": entry.checksum,
                "file_size": entry.file_size,
                "import_status": entry.processing_status,
            }
        )

    combined = pd.concat(frames, ignore_index=True, sort=False)
    _reject_duplicate_ids(combined)
    ordered = _order_columns(combined)
    return IngestionResult(
        frame=ordered,
        resolution=pd.DataFrame(resolution),
        sources=pd.DataFrame(sources),
    )


def build_manifest_rows(
    directory: str | Path,
    *,
    download_location: str = "",
    retrieval_date: str = "",
    wbes_version: str = "",
    processing_status: str = "pending",
) -> pd.DataFrame:
    """Describe every readable source file in a directory as manifest rows.

    Country and survey year cannot be inferred reliably from a file name, so
    they are left blank for the researcher to complete. Everything that can be
    established mechanically is filled in.
    """
    root = Path(directory)
    if not root.exists():
        raise IngestionError(f"source directory does not exist: {root}")
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_FORMATS:
            continue
        rows.append(
            {
                "source_name": path.stem,
                "download_location": download_location,
                "retrieval_date": retrieval_date,
                "country": "",
                "survey_year": "",
                "wbes_version": wbes_version,
                "file_name": str(path.relative_to(root).as_posix()),
                "source_format": SUPPORTED_FORMATS[path.suffix.lower()],
                "checksum": compute_sha256(path),
                "file_size": int(path.stat().st_size),
                "processing_status": processing_status,
            }
        )
    return pd.DataFrame(rows)


def _order_columns(frame: pd.DataFrame) -> pd.DataFrame:
    leading = [
        column
        for column in [*CANONICAL_METADATA, *PROVENANCE_COLUMNS]
        if column in frame.columns
    ]
    remaining = [column for column in frame.columns if column not in leading]
    return frame[[*leading, *remaining]]


def _reject_duplicate_entries(entries: Sequence[ManifestEntry]) -> None:
    seen_files: set[str] = set()
    seen_sources: set[str] = set()
    for entry in entries:
        key = entry.file_name.lower()
        if key in seen_files:
            raise IngestionError(f"duplicate manifest entry for file: {entry.file_name}")
        seen_files.add(key)
        if entry.source_name.lower() in seen_sources:
            raise IngestionError(f"duplicate manifest source name: {entry.source_name}")
        seen_sources.add(entry.source_name.lower())


def _reject_duplicate_ids(frame: pd.DataFrame) -> None:
    identifiers = frame["establishment_id"].astype(str)
    duplicated = identifiers.duplicated(keep=False)
    if not bool(duplicated.any()):
        return
    examples = sorted(identifiers[duplicated].unique())[:5]
    countries = sorted(frame.loc[duplicated, "country"].astype(str).unique())
    raise IngestionError(
        f"{int(duplicated.sum())} establishment identifiers are not unique across sources "
        f"(examples: {examples}; countries: {countries}). Configure the release-wide "
        "identifier rather than a within-country one."
    )


def _validate_survey_year(frame: pd.DataFrame, entry: ManifestEntry) -> None:
    years = pd.to_numeric(frame["survey_year"], errors="coerce")
    if years.isna().any():
        raise IngestionError(
            f"{entry.source_name}: survey_year has {int(years.isna().sum())} non-numeric values"
        )
    outside = (years < MIN_SURVEY_YEAR) | (years > MAX_SURVEY_YEAR)
    if bool(outside.any()):
        observed = sorted(years[outside].unique().tolist())
        raise IngestionError(
            f"{entry.source_name}: implausible survey years {observed}"
        )


def _validate_weight(frame: pd.DataFrame, entry: ManifestEntry) -> None:
    weights = pd.to_numeric(frame["sampling_weight"], errors="coerce")
    invalid = weights.isna() | (weights <= 0)
    if bool(invalid.any()):
        raise IngestionError(
            f"{entry.source_name}: sampling_weight has {int(invalid.sum())} missing or "
            "non-positive values; population inference is impossible until they are resolved"
        )
