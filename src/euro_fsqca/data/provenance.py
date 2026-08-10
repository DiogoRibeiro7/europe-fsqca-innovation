"""Source-file manifest and checksum validation."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

MANIFEST_COLUMNS = [
    "source_name",
    "download_location",
    "retrieval_date",
    "country",
    "survey_year",
    "wbes_version",
    "file_name",
    "source_format",
    "checksum",
    "file_size",
    "processing_status",
]


class ManifestValidationError(ValueError):
    """Raised when a source manifest is malformed or does not match local files."""


@dataclass(frozen=True)
class ManifestEntry:
    """One source file recorded in the data manifest."""

    source_name: str
    download_location: str
    retrieval_date: str
    country: str
    survey_year: str
    wbes_version: str
    file_name: str
    source_format: str
    checksum: str
    file_size: int
    processing_status: str

    @property
    def relative_path(self) -> Path:
        """Return the source path recorded by the manifest."""
        return Path(self.file_name)


@dataclass(frozen=True)
class FileCheck:
    """Validation result for one manifest entry."""

    entry: ManifestEntry
    path: Path
    exists: bool
    checksum_ok: bool | None
    size_ok: bool | None
    actual_checksum: str | None
    actual_size: int | None


@dataclass(frozen=True)
class ManifestReport:
    """Complete validation result for a source manifest."""

    manifest_path: Path
    entries: list[ManifestEntry]
    checks: list[FileCheck]

    @property
    def ok(self) -> bool:
        """Return true when all manifest entries match local files."""
        return all(
            check.exists
            and check.checksum_ok is not False
            and check.size_ok is not False
            for check in self.checks
        )

    @property
    def missing(self) -> list[FileCheck]:
        """Return checks for files that are not available locally."""
        return [check for check in self.checks if not check.exists]

    @property
    def mismatched(self) -> list[FileCheck]:
        """Return checks with checksum or size mismatches."""
        return [
            check
            for check in self.checks
            if check.exists and (check.checksum_ok is False or check.size_ok is False)
        ]


def compute_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute the SHA-256 checksum for a local file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    """Load and validate source metadata from a CSV manifest."""
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != MANIFEST_COLUMNS:
            raise ManifestValidationError(
                f"manifest columns must be exactly: {', '.join(MANIFEST_COLUMNS)}"
            )
        entries: list[ManifestEntry] = []
        for row_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            missing = [column for column in MANIFEST_COLUMNS if not (row.get(column) or "").strip()]
            if missing:
                raise ManifestValidationError(
                    f"manifest row {row_number} is missing: {', '.join(missing)}"
                )
            try:
                file_size = int(row["file_size"])
            except ValueError as exc:
                raise ManifestValidationError(
                    f"manifest row {row_number} has non-integer file_size"
                ) from exc
            if file_size < 0:
                raise ManifestValidationError(
                    f"manifest row {row_number} has negative file_size"
                )
            entries.append(
                ManifestEntry(
                    source_name=row["source_name"].strip(),
                    download_location=row["download_location"].strip(),
                    retrieval_date=row["retrieval_date"].strip(),
                    country=row["country"].strip(),
                    survey_year=row["survey_year"].strip(),
                    wbes_version=row["wbes_version"].strip(),
                    file_name=row["file_name"].strip(),
                    source_format=row["source_format"].strip().lower(),
                    checksum=row["checksum"].strip().lower(),
                    file_size=file_size,
                    processing_status=row["processing_status"].strip(),
                )
            )
    return entries


def validate_manifest(path: str | Path, *, root: str | Path = "data/raw") -> ManifestReport:
    """Validate all files listed in a source manifest against checksum and size."""
    manifest_path = Path(path)
    root_path = Path(root)
    entries = load_manifest(manifest_path)
    checks: list[FileCheck] = []
    for entry in entries:
        file_path = entry.relative_path
        if not file_path.is_absolute():
            file_path = root_path / file_path
        exists = file_path.exists()
        actual_size = file_path.stat().st_size if exists else None
        actual_checksum = compute_sha256(file_path) if exists else None
        checks.append(
            FileCheck(
                entry=entry,
                path=file_path,
                exists=exists,
                checksum_ok=actual_checksum == entry.checksum if exists else None,
                size_ok=actual_size == entry.file_size if exists else None,
                actual_checksum=actual_checksum,
                actual_size=actual_size,
            )
        )
    return ManifestReport(manifest_path=manifest_path, entries=entries, checks=checks)


def raise_for_manifest_errors(report: ManifestReport) -> None:
    """Raise a clear error when manifest validation fails."""
    if report.ok:
        return
    messages: list[str] = []
    for check in report.missing:
        messages.append(f"missing source file: {check.path}")
    for check in report.mismatched:
        if check.size_ok is False:
            messages.append(
                f"size mismatch for {check.path}: expected {check.entry.file_size}, "
                f"found {check.actual_size}"
            )
        if check.checksum_ok is False:
            messages.append(
                f"checksum mismatch for {check.path}: expected {check.entry.checksum}, "
                f"found {check.actual_checksum}"
            )
    raise ManifestValidationError("; ".join(messages))
