from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from euro_fsqca.qca.fuzzy import necessity_fit, sufficiency_fit
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table
from euro_fsqca.survey import (
    design_effect,
    effective_sample_size,
    resolve_weights,
    weight_diagnostics,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "country": ["PT", "PT", "PT", "DE"],
            "wt": [1.0, 1.0, 1.0, 9.0],
        }
    )


def test_unweighted_scheme_gives_unit_weights() -> None:
    weights = resolve_weights(_frame(), scheme="unweighted")

    assert list(weights) == [1.0, 1.0, 1.0, 1.0]


def test_firm_population_scheme_normalises_to_sample_size() -> None:
    weights = resolve_weights(_frame(), scheme="firm_population", weight_column="wt")

    assert math.isclose(float(weights.sum()), 4.0)
    # The single heavily weighted establishment keeps its relative influence.
    assert weights.iloc[3] > weights.iloc[0] * 8


def test_equal_country_scheme_balances_countries() -> None:
    frame = _frame()
    weights = resolve_weights(
        frame, scheme="equal_country", weight_column="wt", country_column="country"
    )
    totals = weights.groupby(frame["country"]).sum()

    assert math.isclose(float(totals["PT"]), float(totals["DE"]))


def test_weight_scheme_rejects_invalid_weights() -> None:
    frame = pd.DataFrame({"country": ["PT"], "wt": [0.0]})

    with pytest.raises(ValueError, match="non-positive"):
        resolve_weights(frame, scheme="firm_population", weight_column="wt")


def test_effective_sample_size_penalises_unequal_weights() -> None:
    equal = np.ones(10)
    unequal = np.array([1.0] * 9 + [91.0])

    assert math.isclose(effective_sample_size(equal), 10.0)
    assert effective_sample_size(unequal) < 3.0
    assert design_effect(unequal) > 3.0


def test_weight_diagnostics_reports_group_concentration() -> None:
    frame = _frame()
    weights = resolve_weights(frame, scheme="firm_population", weight_column="wt")

    report = weight_diagnostics(frame, weights=weights, group_columns=["country"])

    assert set(report["scope"]) == {"total", "country"}
    assert "effective_sample_size" in report.columns


def test_weighted_sufficiency_differs_from_unweighted() -> None:
    x = np.array([0.9, 0.9, 0.9])
    y = np.array([0.9, 0.9, 0.1])
    heavy_on_contradiction = np.array([1.0, 1.0, 20.0])

    unweighted = sufficiency_fit(x, y)
    weighted = sufficiency_fit(x, y, weights=heavy_on_contradiction)

    assert weighted.consistency < unweighted.consistency
    assert math.isclose(
        weighted.consistency,
        (0.9 + 0.9 + 20 * 0.1) / (0.9 + 0.9 + 20 * 0.9),
    )


def test_weighted_necessity_uses_weights() -> None:
    x = np.array([0.9, 0.2])
    y = np.array([0.9, 0.9])

    unweighted = necessity_fit(x, y)
    weighted = necessity_fit(x, y, weights=np.array([1.0, 5.0]))

    assert weighted.consistency < unweighted.consistency


def test_truth_table_reports_weighted_and_effective_frequency() -> None:
    frame = pd.DataFrame(
        {
            "A": [0.9, 0.9, 0.9, 0.1],
            "Y": [0.9, 0.9, 0.9, 0.1],
        }
    )
    weights = pd.Series([1.0, 1.0, 30.0, 1.0])

    table = build_truth_table(
        frame,
        conditions=["A"],
        outcome="Y",
        thresholds=TruthTableThresholds(
            frequency=3, consistency=0.8, pri=0.5, frequency_basis="effective"
        ),
        weights=weights,
    )

    row = table[table["A"] == 1].iloc[0]
    assert row["frequency"] == 3
    assert math.isclose(float(row["weighted_frequency"]), 32.0)
    # One dominant establishment carries most of the weight, so the row holds
    # far less evidence than its weight mass suggests and stays excluded.
    assert float(row["effective_frequency"]) < 2.0
    assert not bool(row["positive"])


def test_weighted_frequency_basis_can_include_rows_case_counting_excludes() -> None:
    frame = pd.DataFrame({"A": [0.9, 0.9, 0.1], "Y": [0.9, 0.9, 0.1]})
    weights = pd.Series([5.0, 5.0, 1.0])

    by_cases = build_truth_table(
        frame,
        conditions=["A"],
        outcome="Y",
        thresholds=TruthTableThresholds(frequency=3, consistency=0.8, pri=0.5),
        weights=weights,
    )
    by_weight = build_truth_table(
        frame,
        conditions=["A"],
        outcome="Y",
        thresholds=TruthTableThresholds(
            frequency=3, consistency=0.8, pri=0.5, frequency_basis="weighted"
        ),
        weights=weights,
    )

    assert not bool(by_cases[by_cases["A"] == 1].iloc[0]["positive"])
    assert bool(by_weight[by_weight["A"] == 1].iloc[0]["positive"])


def test_canonical_thresholds_always_count_cases() -> None:
    from euro_fsqca.config import load_config

    config = load_config("configs/analysis.demo.yml")

    # Row inclusion in the canonical analysis is not a configurable design
    # choice: a non-standard n.cut could not be reproduced by the R engine.
    assert config.truth_table.thresholds().frequency_basis == "cases"


def test_weighted_exploration_requires_a_weight_column() -> None:
    from euro_fsqca.config import AnalysisConfig, load_config

    config = load_config("configs/analysis.demo.yml")
    payload = config.model_dump()
    payload["survey"]["weight_column"] = None
    payload["survey"]["primary_estimand"] = "unweighted"
    payload["survey"]["estimands"] = ["unweighted"]
    payload["robustness"]["weighted_truth_table_exploration"] = True

    with pytest.raises(ValueError, match="weighted truth-table exploration"):
        AnalysisConfig.model_validate(payload)
