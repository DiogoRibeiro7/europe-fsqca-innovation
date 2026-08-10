from __future__ import annotations

from pathlib import Path

import pytest

from euro_fsqca.data.provenance import (
    MANIFEST_COLUMNS,
    ManifestValidationError,
    compute_sha256,
    load_manifest,
    raise_for_manifest_errors,
    validate_manifest,
)


def _write_manifest(path: Path, rows: list[list[str]]) -> None:
    lines = [",".join(MANIFEST_COLUMNS)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_empty_manifest_is_valid(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [])

    report = validate_manifest(manifest, root=tmp_path / "raw")

    assert report.ok
    assert report.entries == []


def test_manifest_validates_checksum_and_size(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "country.csv"
    source.write_text("id,value\n1,2\n", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            [
                "WBES country",
                "restricted",
                "2026-08-09",
                "Portugal",
                "2024",
                "v1",
                "country.csv",
                "csv",
                compute_sha256(source),
                str(source.stat().st_size),
                "pending",
            ]
        ],
    )

    report = validate_manifest(manifest, root=raw)

    assert report.ok
    assert report.checks[0].checksum_ok is True
    assert report.checks[0].size_ok is True


def test_manifest_reports_missing_files(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            [
                "WBES country",
                "restricted",
                "2026-08-09",
                "Portugal",
                "2024",
                "v1",
                "missing.csv",
                "csv",
                "0" * 64,
                "10",
                "pending",
            ]
        ],
    )

    report = validate_manifest(manifest, root=tmp_path / "raw")

    assert not report.ok
    with pytest.raises(ManifestValidationError, match="missing source file"):
        raise_for_manifest_errors(report)


def test_manifest_rejects_malformed_rows(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [["WBES country"]])

    with pytest.raises(ManifestValidationError, match="missing"):
        load_manifest(manifest)
