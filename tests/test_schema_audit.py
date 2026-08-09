from __future__ import annotations

import json

import pandas as pd

from euro_fsqca.data.schema import SchemaDataset, schema_audit


def test_schema_audit_marks_cross_file_availability() -> None:
    portugal = SchemaDataset(
        source_name="PT",
        country="Portugal",
        survey_year="2024",
        wbes_version="v1",
        frame=pd.DataFrame({"a": [1, 2], "b": [1, None]}),
    )
    spain = SchemaDataset(
        source_name="ES",
        country="Spain",
        survey_year="2024",
        wbes_version="v1",
        frame=pd.DataFrame({"a": [1, 99], "c": ["x", "y"]}),
    )

    audit = schema_audit([portugal, spain])

    a_rows = audit[audit["column"] == "a"]
    b_rows = audit[audit["column"] == "b"]
    assert set(a_rows["availability"]) == {"all"}
    assert set(b_rows["availability"]) == {"some"}
    assert "Spain" not in json.loads(str(b_rows.iloc[0]["countries_present"]))


def test_schema_audit_reports_potential_missing_codes() -> None:
    dataset = SchemaDataset(
        source_name="PT",
        country="Portugal",
        survey_year="2024",
        wbes_version="v1",
        frame=pd.DataFrame({"finance": [1, 2, -9, 99]}),
    )

    audit = schema_audit([dataset])

    codes = json.loads(str(audit.loc[0, "missing_value_codes"]))
    assert codes == ["-9", "99"]


def test_schema_audit_handles_no_sources() -> None:
    audit = schema_audit([])

    assert audit.empty
    assert "column" in audit.columns
