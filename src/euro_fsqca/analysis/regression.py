"""Conventional net-effect comparison models."""

from __future__ import annotations

import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.generalized_linear_model import GLMResultsWrapper


def fit_fractional_logit(
    frame: pd.DataFrame,
    *,
    outcome: str,
    conditions: list[str],
) -> GLMResultsWrapper:
    """Fit a quasi-binomial-style fractional logit to fuzzy outcome memberships.

    This is a descriptive net-effect comparison, not a validation of fsQCA.
    """
    data = frame[[outcome, *conditions]].dropna()
    exog = sm.add_constant(data[conditions], has_constant="add")
    model = sm.GLM(data[outcome], exog, family=sm.families.Binomial())
    return model.fit(cov_type="HC3")
