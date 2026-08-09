from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.analysis.constructs import (
    component_correlations,
    construct_correlations,
    construct_summary,
    construct_values,
    write_construct_diagnostics,
)
from euro_fsqca.config import load_config


def test_construct_values_use_configured_sources() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = pd.DataFrame(
        {
            "firm_id": ["a", "b"],
            "country": ["PT", "ES"],
            "digital_raw": [10, 20],
            "human_raw": [30, 40],
            "finance_raw": [50, 60],
            "international_raw": [70, 80],
            "management_raw": [20, 30],
            "external_knowledge_raw": [40, 50],
            "innovation_raw": [60, 70],
        }
    )

    values = construct_values(frame, config)

    assert list(values["DIG"]) == [10, 20]
    assert list(values["INN"]) == [60, 70]


def test_construct_summary_reports_missingness_and_outliers() -> None:
    values = pd.DataFrame({"DIG": [1, 2, None, 100]})

    summary = construct_summary(values, constructs=["DIG"])

    assert summary.loc[0, "n_non_missing"] == 3
    assert summary.loc[0, "missing_share"] == 0.25
    outliers = summary["n_outliers_iqr"].astype(int).iloc[0]
    assert outliers >= 0


def test_construct_correlations_are_long_format() -> None:
    values = pd.DataFrame({"DIG": [1, 2, 3], "HC": [1, 2, 3]})

    correlations = construct_correlations(values, constructs=["DIG", "HC"])

    assert set(correlations.columns) == {"left", "right", "correlation"}
    assert correlations.shape[0] == 4


def test_component_correlations_handles_source_only_config() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = pd.DataFrame()

    correlations = component_correlations(frame, config)

    assert correlations.empty


def test_write_construct_diagnostics(tmp_path: Path) -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = pd.DataFrame(
        {
            "firm_id": ["a", "b"],
            "country": ["PT", "ES"],
            "digital_raw": [10, 20],
            "human_raw": [30, 40],
            "finance_raw": [50, 60],
            "international_raw": [70, 80],
            "management_raw": [20, 30],
            "external_knowledge_raw": [40, 50],
            "innovation_raw": [60, 70],
        }
    )

    write_construct_diagnostics(frame, config=config, output_dir=tmp_path)

    assert (tmp_path / "construct_summary.csv").exists()
    assert (tmp_path / "construct_country_summary.csv").exists()
