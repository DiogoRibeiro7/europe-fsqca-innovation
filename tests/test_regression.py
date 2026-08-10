from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from euro_fsqca.analysis.regression import fit_net_effect_model


def _frame(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(2)
    digital = rng.uniform(0, 1, n)
    human = rng.uniform(0, 1, n)
    return pd.DataFrame(
        {
            "DIG_raw": digital,
            "HC_raw": human,
            "INN_raw": np.clip(0.2 + 0.5 * digital + 0.2 * human, 0, 1),
            "country": rng.choice(["PT", "DE", "PL"], n),
            "sector": rng.choice(["manufacturing", "services"], n),
            "sampling_weight": rng.lognormal(0, 0.4, n),
        }
    )


def test_model_uses_weights_controls_and_clustered_errors() -> None:
    model = fit_net_effect_model(
        _frame(),
        outcome_column="INN_raw",
        condition_columns=["DIG_raw", "HC_raw"],
        control_columns=["country", "sector"],
        weight_column="sampling_weight",
        cluster_column="country",
    )

    terms = list(model.coefficients["term"])
    assert "DIG_raw" in terms
    # Categorical controls enter as dummies with a reference level dropped.
    assert any(term.startswith("country_") for term in terms)
    assert any(term.startswith("sector_") for term in terms)
    assert model.specification["cov_type"] == "cluster"
    assert model.specification["weight_column"] == "sampling_weight"


def test_weighting_changes_the_estimates() -> None:
    frame = _frame()
    unweighted = fit_net_effect_model(
        frame, outcome_column="INN_raw", condition_columns=["DIG_raw", "HC_raw"]
    )
    weighted = fit_net_effect_model(
        frame,
        outcome_column="INN_raw",
        condition_columns=["DIG_raw", "HC_raw"],
        weight_column="sampling_weight",
    )

    assert not np.allclose(
        unweighted.coefficients["estimate"].to_numpy(),
        weighted.coefficients["estimate"].to_numpy(),
    )


def test_model_rejects_an_outcome_outside_the_unit_interval() -> None:
    frame = _frame()
    frame["INN_raw"] = frame["INN_raw"] * 100

    with pytest.raises(ValueError, match="unit interval"):
        fit_net_effect_model(
            frame, outcome_column="INN_raw", condition_columns=["DIG_raw", "HC_raw"]
        )
