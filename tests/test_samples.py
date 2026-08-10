from __future__ import annotations

import pandas as pd
import pytest

from euro_fsqca.analysis.samples import assign_period, select_sample, timing_summary
from euro_fsqca.config import AnalysisConfig, SampleFilter, SampleSpec, TimingConfig, load_config


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "firm_id": ["A", "B", "C", "D"],
            "country": ["PT", "PT", "DE", "DE"],
            "n_employees": [4, 25, 120, 30],
            "MGT_raw": [None, 0.4, 0.8, None],
            "survey_year": [2019, 2019, 2021, 2021],
            "wt": [2.0, 3.0, 1.0, 1.0],
        }
    )


def test_sample_filters_restrict_the_population_and_record_attrition() -> None:
    sample = SampleSpec(
        label="management_20plus",
        filters=[
            SampleFilter(column="n_employees", min=20, description="20+ workers"),
            SampleFilter(column="MGT_raw", require_non_missing=True, description="module asked"),
        ],
    )

    selected, recorder = select_sample(_frame(), sample=sample, weight_column="wt")
    attrition = recorder.table()

    assert list(selected["firm_id"]) == ["B", "C"]
    assert list(attrition["n_establishments"]) == [4, 3, 2]
    assert attrition["retained_share"].iloc[-1] == 0.5
    # Weight mass falls faster than the case count when the excluded
    # establishments carry heavier weights.
    assert attrition["weight_mass"].iloc[-1] < attrition["weight_mass"].iloc[0]


def test_missing_filter_column_is_an_error_not_a_silent_pass() -> None:
    sample = SampleSpec(label="x", filters=[SampleFilter(column="absent", min=1)])

    with pytest.raises(KeyError, match="absent"):
        select_sample(_frame(), sample=sample)


def test_assign_period_labels_survey_years() -> None:
    timing = TimingConfig(
        year_column="survey_year", periods={"pre_covid": [2019], "covid": [2021]}
    )

    result = assign_period(_frame(), timing)

    assert list(result["survey_period"]) == ["pre_covid", "pre_covid", "covid", "covid"]


def test_timing_summary_reports_the_innovation_reference_window() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = assign_period(_frame(), config.timing)

    summary = timing_summary(frame, config=config)

    portugal = summary[summary["country"] == "PT"].iloc[0]
    assert portugal["min_year"] == 2019
    # Innovation questions look back three years from the interview.
    assert portugal["reference_window_start"] == 2016


def test_config_rejects_a_sample_referencing_unknown_conditions() -> None:
    config = load_config("configs/analysis.demo.yml")
    payload = config.model_dump()
    payload["samples"] = {
        "bad": {"label": "bad", "primary": True, "conditions": ["NOT_A_CONDITION"]}
    }

    with pytest.raises(ValueError, match="unknown conditions"):
        AnalysisConfig.model_validate(payload)


def test_config_defaults_to_a_single_primary_sample() -> None:
    config = load_config("configs/analysis.demo.yml")
    payload = config.model_dump()
    payload.pop("samples")

    rebuilt = AnalysisConfig.model_validate(payload)

    assert list(rebuilt.samples) == ["primary"]
    assert rebuilt.primary_sample.conditions == list(config.conditions)
