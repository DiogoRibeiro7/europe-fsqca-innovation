from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyreadstat
import pytest

from euro_fsqca.data.io import read_table_with_metadata
from euro_fsqca.data.provenance import MANIFEST_COLUMNS, compute_sha256
from euro_fsqca.data.schema import (
    SchemaDataset,
    label_agreement,
    schema_artifacts_from_manifest,
    schema_audit,
)

# Two WBES-like variables whose names say nothing without the question text.
PORTUGAL_LABELS = {
    "h1": "In the last three years, has this establishment introduced a new product?",
    "wk2": "Number of permanent full-time employees at end of last fiscal year",
}
SPAIN_LABELS = {
    "h1": "In the last three years, has this establishment introduced a new process?",
    "wk2": "Number of permanent full-time employees at end of last fiscal year",
}
VALUE_LABELS = {"h1": {1.0: "Yes", 2.0: "No", -9.0: "Don't know"}}


def _write_stata(path: Path, labels: dict[str, str]) -> None:
    frame = pd.DataFrame(
        {"idstd": [1.0, 2.0, 3.0], "h1": [1.0, 2.0, -9.0], "wk2": [8.0, 40.0, 90.0]}
    )
    pyreadstat.write_dta(
        frame, str(path), column_labels=labels, variable_value_labels=VALUE_LABELS
    )


def _write_spss(path: Path, labels: dict[str, str]) -> None:
    frame = pd.DataFrame(
        {"idstd": [4.0, 5.0, 6.0], "h1": [1.0, 1.0, 2.0], "wk2": [12.0, 60.0, 200.0]}
    )
    pyreadstat.write_sav(
        frame, str(path), column_labels=labels, variable_value_labels=VALUE_LABELS
    )


def test_stata_variable_and_value_labels_survive_reading(tmp_path: Path) -> None:
    source = tmp_path / "pt.dta"
    _write_stata(source, PORTUGAL_LABELS)

    result = read_table_with_metadata(source)

    assert result.metadata.available
    assert result.metadata.column_labels["h1"] == PORTUGAL_LABELS["h1"]
    assert result.metadata.value_labels["h1"][-9.0] == "Don't know"
    assert list(result.frame["h1"]) == [1.0, 2.0, -9.0]


def test_spss_variable_labels_survive_reading(tmp_path: Path) -> None:
    source = tmp_path / "es.sav"
    _write_spss(source, SPAIN_LABELS)

    result = read_table_with_metadata(source)

    assert result.metadata.column_labels["h1"] == SPAIN_LABELS["h1"]


def test_csv_reports_no_labels_rather_than_inventing_them(tmp_path: Path) -> None:
    source = tmp_path / "pt.csv"
    pd.DataFrame({"h1": [1, 2]}).to_csv(source, index=False)

    result = read_table_with_metadata(source)

    assert not result.metadata.available
    assert result.metadata.column_labels == {}


def test_audit_records_labels_and_value_labels() -> None:
    dataset = SchemaDataset(
        source_name="PT",
        country="Portugal",
        survey_year="2019",
        wbes_version="v1",
        frame=pd.DataFrame({"h1": [1, 2, -9]}),
        labels=PORTUGAL_LABELS,
        value_labels={"h1": {1: "Yes", 2: "No", -9: "Don't know"}},
    )

    audit = schema_audit([dataset])

    row = audit[audit["column"] == "h1"].iloc[0]
    assert row["label"] == PORTUGAL_LABELS["h1"]
    assert json.loads(str(row["value_labels"]))["-9"] == "Don't know"


def test_label_agreement_detects_the_same_name_asking_different_questions() -> None:
    portugal = SchemaDataset(
        source_name="PT",
        country="Portugal",
        survey_year="2019",
        wbes_version="v1",
        frame=pd.DataFrame({"h1": [1], "wk2": [8]}),
        labels=PORTUGAL_LABELS,
    )
    spain = SchemaDataset(
        source_name="ES",
        country="Spain",
        survey_year="2020",
        wbes_version="v1",
        frame=pd.DataFrame({"h1": [1], "wk2": [9]}),
        labels=SPAIN_LABELS,
    )

    # Same variable name, different question: comparable by name, not in fact.
    assert label_agreement([portugal, spain], "h1") == "conflicting"
    assert label_agreement([portugal, spain], "wk2") == "identical"


def test_unlabelled_variable_is_reported_as_such() -> None:
    dataset = SchemaDataset(
        source_name="PT",
        country="Portugal",
        survey_year="2019",
        wbes_version="v1",
        frame=pd.DataFrame({"h1": [1]}),
    )

    assert label_agreement([dataset], "h1") == "no_label"


def test_schema_artifacts_are_written_from_labelled_sources(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.dta"
    spain = raw / "es.sav"
    _write_stata(portugal, PORTUGAL_LABELS)
    _write_spss(spain, SPAIN_LABELS)

    manifest = tmp_path / "manifest.csv"
    rows = [
        ["PT", "restricted", "2026-08-10", "Portugal", "2019", "v1", "pt.dta", "stata",
         compute_sha256(portugal), str(portugal.stat().st_size), "pending"],
        ["ES", "restricted", "2026-08-10", "Spain", "2020", "v1", "es.sav", "spss",
         compute_sha256(spain), str(spain.stat().st_size), "pending"],
    ]
    manifest.write_text(
        "\n".join([",".join(MANIFEST_COLUMNS), *(",".join(row) for row in rows)]) + "\n",
        encoding="utf-8",
    )

    paths = schema_artifacts_from_manifest(
        manifest, raw_root=raw, output_dir=tmp_path / "outputs"
    )

    assert paths["inventory"].exists()
    assert paths["comparison"].exists()
    inventory = pd.read_parquet(paths["inventory"])
    assert set(inventory["source_name"]) == {"PT", "ES"}
    assert inventory.loc[inventory["column"] == "h1", "label"].str.len().gt(0).all()

    comparison = pd.read_csv(paths["comparison"])
    lookup = dict(zip(comparison["column"], comparison["label_agreement"], strict=True))
    # h1 is present in both releases but asks a different question in each.
    assert lookup["h1"] == "conflicting"
    assert lookup["wk2"] == "identical"


def test_readiness_accepts_the_generated_audit(tmp_path: Path) -> None:
    from euro_fsqca.readiness import assess_readiness

    root = Path(__file__).resolve().parents[1]
    raw = tmp_path / "raw"
    raw.mkdir()
    portugal = raw / "pt.dta"
    _write_stata(portugal, PORTUGAL_LABELS)
    manifest = tmp_path / "manifest.csv"
    row = ["PT", "restricted", "2026-08-10", "Portugal", "2019", "v1", "pt.dta", "stata",
           compute_sha256(portugal), str(portugal.stat().st_size), "pending"]
    manifest.write_text(
        "\n".join([",".join(MANIFEST_COLUMNS), ",".join(row)]) + "\n", encoding="utf-8"
    )
    paths = schema_artifacts_from_manifest(
        manifest, raw_root=raw, output_dir=tmp_path / "outputs"
    )

    report = assess_readiness(
        config_path=root / "configs" / "analysis.demo.yml",
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=manifest,
        raw_root=raw,
        schema_audit_path=paths["audit"],
    )

    assert report[report["check"] == "schema_audit"].iloc[0]["status"] == "ok"
    assert report[report["check"] == "data_manifest"].iloc[0]["status"] == "ok"


@pytest.mark.parametrize("suffix", [".dta", ".sav"])
def test_special_codes_are_preserved_not_silently_converted(
    tmp_path: Path, suffix: str
) -> None:
    source = tmp_path / f"pt{suffix}"
    if suffix == ".dta":
        _write_stata(source, PORTUGAL_LABELS)
    else:
        _write_spss(source, SPAIN_LABELS)

    frame = read_table_with_metadata(source).frame

    # Ingestion must not decide what -9 means; harmonisation does that later,
    # against the documented value labels.
    assert frame["h1"].notna().all()
