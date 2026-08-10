from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from euro_fsqca.data.ingest import (
    CANONICAL_METADATA,
    IngestionError,
    IngestionSpec,
    build_manifest_rows,
    detect_format,
    ingest_manifest,
    load_ingestion_spec,
    standardise_source,
)
from euro_fsqca.data.provenance import MANIFEST_COLUMNS, ManifestEntry, compute_sha256

SPEC = IngestionSpec(
    default={
        "establishment_id": ["idstd", "id"],
        "country": ["country"],
        "survey_year": ["year"],
        "sector": ["sector"],
        "size_class": ["size"],
        "n_employees": ["l1"],
        "sampling_weight": ["wt", "weight"],
        "stratum": ["stratum"],
        "region": ["region"],
    }
)


def _entry(file_name: str, *, source_name: str = "PT", country: str = "Portugal") -> ManifestEntry:
    return ManifestEntry(
        source_name=source_name,
        download_location="restricted",
        retrieval_date="2026-08-10",
        country=country,
        survey_year="2019",
        wbes_version="v1",
        file_name=file_name,
        source_format="csv",
        checksum="0" * 64,
        file_size=0,
        processing_status="pending",
    )


def _source(**overrides: Any) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "idstd": [1, 2, 3],
            "country": ["Portugal"] * 3,
            "year": [2019, 2019, 2019],
            "sector": ["manufacturing", "retail", "manufacturing"],
            "size": ["small", "medium", "large"],
            "l1": [8, 40, 300],
            "wt": [2.5, 1.4, 0.7],
            "stratum": ["PT|man|small", "PT|ret|med", "PT|man|large"],
            "region": ["PT11", "PT16", "PT17"],
            # An analytical variable that must pass through untouched.
            "h1": [1, 0, -9],
        }
    )
    for column, value in overrides.items():
        frame[column] = value
    return frame


def _write_manifest(path: Path, rows: list[list[str]]) -> None:
    lines = [",".join(MANIFEST_COLUMNS)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _manifest_row(source: Path, *, name: str, country: str, year: str = "2019") -> list[str]:
    return [
        name,
        "restricted",
        "2026-08-10",
        country,
        year,
        "v1",
        source.name,
        "csv",
        compute_sha256(source),
        str(source.stat().st_size),
        "pending",
    ]


def test_detect_format_covers_real_release_formats() -> None:
    assert detect_format("a.dta") == "stata"
    assert detect_format("a.sav") == "spss"
    assert detect_format("a.csv") == "csv"
    assert detect_format("a.parquet") == "parquet"
    with pytest.raises(IngestionError, match="unsupported source format"):
        detect_format("a.txt")


def test_standardise_resolves_metadata_and_preserves_analytical_columns() -> None:
    result, resolution = standardise_source(
        _source(), entry=_entry("pt.csv"), spec=SPEC, source_format="csv"
    )

    for canonical in CANONICAL_METADATA:
        assert canonical in result.columns
    assert list(result["establishment_id"]) == [1, 2, 3]
    assert result["source_file"].iloc[0] == "pt.csv"
    assert result["source_format"].iloc[0] == "csv"
    # The analytical variable is untouched, special code included.
    assert list(result["h1"]) == [1, 0, -9]
    resolved = {row["canonical"]: row["source_column"] for row in resolution}
    assert resolved["sampling_weight"] == "wt"
    assert resolved["n_employees"] == "l1"


def test_missing_required_metadata_is_rejected() -> None:
    frame = _source().drop(columns=["idstd"])

    with pytest.raises(IngestionError, match="required metadata could not be resolved"):
        standardise_source(frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv")


def test_missing_sampling_weight_is_rejected() -> None:
    frame = _source()
    frame.loc[1, "wt"] = None

    with pytest.raises(IngestionError, match="sampling_weight"):
        standardise_source(frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv")


def test_non_positive_sampling_weight_is_rejected() -> None:
    frame = _source()
    frame.loc[0, "wt"] = 0.0

    with pytest.raises(IngestionError, match="non-positive"):
        standardise_source(frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv")


def test_invalid_survey_year_is_rejected() -> None:
    frame = _source(year=[19, 2019, 2019])

    with pytest.raises(IngestionError, match="implausible survey years"):
        standardise_source(frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv")


def test_non_numeric_survey_year_is_rejected() -> None:
    frame = _source(year=["two thousand", 2019, 2019])

    with pytest.raises(IngestionError, match="non-numeric"):
        standardise_source(frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv")


def test_country_and_year_fall_back_to_manifest_provenance() -> None:
    frame = _source().drop(columns=["country", "year"])

    result, _ = standardise_source(
        frame, entry=_entry("pt.csv"), spec=SPEC, source_format="csv"
    )

    assert set(result["country"]) == {"Portugal"}
    assert set(result["survey_year"].astype(int)) == {2019}


def test_ingest_manifest_combines_sources_with_provenance(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.csv"
    _source().to_csv(portugal, index=False)
    spain = raw / "es.csv"
    _source(idstd=[4, 5, 6], country="Spain").to_csv(spain, index=False)
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(portugal, name="PT", country="Portugal"),
            _manifest_row(spain, name="ES", country="Spain"),
        ],
    )

    result = ingest_manifest(manifest, raw_root=raw, spec=SPEC)

    assert len(result.frame) == 6
    assert set(result.frame["source_name"]) == {"PT", "ES"}
    assert list(result.frame.columns[:3]) == ["establishment_id", "country", "survey_year"]
    assert set(result.sources["source_format"]) == {"csv"}
    assert int(result.sources["n_rows"].sum()) == 6


def test_duplicate_establishment_ids_across_sources_are_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.csv"
    _source().to_csv(portugal, index=False)
    spain = raw / "es.csv"
    # Same within-country identifiers reused in a second country.
    _source(country="Spain").to_csv(spain, index=False)
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(portugal, name="PT", country="Portugal"),
            _manifest_row(spain, name="ES", country="Spain"),
        ],
    )

    with pytest.raises(IngestionError, match="not unique across sources"):
        ingest_manifest(manifest, raw_root=raw, spec=SPEC)


def test_duplicate_manifest_entries_are_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.csv"
    _source().to_csv(portugal, index=False)
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(portugal, name="PT", country="Portugal"),
            _manifest_row(portugal, name="PT2", country="Portugal"),
        ],
    )

    with pytest.raises(IngestionError, match="duplicate manifest entry"):
        ingest_manifest(manifest, raw_root=raw, spec=SPEC)


def test_checksum_change_is_detected(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.csv"
    _source().to_csv(portugal, index=False)
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_manifest_row(portugal, name="PT", country="Portugal")])
    # The source file is edited after the manifest recorded it.
    _source(idstd=[7, 8, 9]).to_csv(portugal, index=False)

    with pytest.raises(Exception, match="mismatch"):
        ingest_manifest(manifest, raw_root=raw, spec=SPEC)


def test_empty_manifest_is_rejected_for_ingestion(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [])

    with pytest.raises(IngestionError, match="records no source files"):
        ingest_manifest(manifest, raw_root=tmp_path, spec=SPEC)


def test_build_manifest_rows_describes_local_files(tmp_path: Path) -> None:
    _source().to_csv(tmp_path / "pt.csv", index=False)
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    rows = build_manifest_rows(tmp_path)

    assert list(rows["file_name"]) == ["pt.csv"]
    assert rows["source_format"].iloc[0] == "csv"
    assert len(str(rows["checksum"].iloc[0])) == 64
    # Country and year cannot be inferred from a file name and stay blank.
    assert rows["country"].iloc[0] == ""


def test_project_ingestion_spec_is_loadable() -> None:
    spec = load_ingestion_spec("configs/wbes_ingestion.yml")

    assert "wt" in spec.candidates("sampling_weight", "any-source")
    assert spec.candidates("establishment_id", "any-source")


def test_ingestion_spec_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "spec.yml"
    path.write_text("default:\n  not_a_field: [x]\n", encoding="utf-8")

    with pytest.raises(IngestionError, match="unknown canonical metadata"):
        load_ingestion_spec(path)
