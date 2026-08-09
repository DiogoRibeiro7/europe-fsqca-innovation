from __future__ import annotations

import pandas as pd

from euro_fsqca.data.harmonisation import (
    ExclusionRule,
    build_exclusion_log,
    harmonisation_report,
    recode_special_missing,
)


def test_recode_special_missing_logs_semantics() -> None:
    frame = pd.DataFrame({"country": ["PT", "ES", "PT"], "x": [1, -9, 98]})

    recoded, log = recode_special_missing(
        frame,
        rules={"x": {-9: "do not know", 98: "not applicable"}},
    )

    assert recoded["x"].isna().sum() == 2
    assert set(log["meaning"]) == {"do not know", "not applicable"}
    assert log["n_affected"].sum() == 2


def test_harmonisation_report_flags_core_issues() -> None:
    frame = pd.DataFrame(
        {
            "firm_id": ["a", "a", "b"],
            "country": ["PT", "PT", "ES"],
            "sector": ["A", "Z", "B"],
            "value": [1, 500, None],
        }
    )

    report = harmonisation_report(
        frame,
        required_identifiers=["firm_id", "country", "survey_year"],
        categorical_allowed={"sector": {"A", "B"}},
        continuous_ranges={"value": (0, 100)},
    )

    assert "missing_identifier" in set(report["issue_type"])
    assert "duplicate_observation" in set(report["issue_type"])
    assert "unexpected_category" in set(report["issue_type"])
    assert "impossible_value" in set(report["issue_type"])


def test_exclusion_log_records_rule_counts() -> None:
    frame = pd.DataFrame({"country": ["PT", "ES", "PT"], "x": [1, None, 3]})

    log = build_exclusion_log(
        frame,
        [
            ExclusionRule(
                rule_id="missing_x",
                reason="x is required",
                predicate=lambda data: data["x"].isna(),
            )
        ],
    )

    assert log.loc[0, "rule_id"] == "missing_x"
    assert log.loc[0, "n_affected"] == 1
    assert log.loc[0, "countries_affected"] == "ES"
