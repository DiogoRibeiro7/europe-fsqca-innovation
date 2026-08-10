"""Conventional net-effect comparison model.

The point of this model is contrast, not validation: net associations under an
additive model versus asymmetric sufficient configurations under fsQCA. To be
worth reporting the contrast has to be estimated on the observed innovation
outcome rather than on its fuzzy calibration, and it has to respect the survey
design and the composition of the pooled sample. A model that ignores weights,
country, survey year, sector and size answers a question nobody asked.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True)
class NetEffectModel:
    """Fitted comparison model and the design choices behind it."""

    coefficients: pd.DataFrame
    specification: dict[str, object]


def fit_net_effect_model(
    frame: pd.DataFrame,
    *,
    outcome_column: str,
    condition_columns: list[str],
    control_columns: list[str] | None = None,
    weight_column: str | None = None,
    cluster_column: str | None = None,
) -> NetEffectModel:
    """Fit a survey-weighted fractional logit on the observed outcome.

    ``outcome_column`` must be the observed innovation measure on the unit
    interval, not a calibrated set membership. Categorical controls enter as
    dummies with the first level dropped. Weights enter the pseudo-likelihood
    and standard errors are clustered on ``cluster_column``, which should be
    the country so that within-country design correlation is absorbed.
    """
    controls = list(control_columns or [])
    required = [outcome_column, *condition_columns, *controls]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"missing model columns: {missing}")

    data = frame[required].copy()
    if weight_column is not None:
        if weight_column not in frame.columns:
            raise KeyError(f"missing weight column: {weight_column}")
        data["_weight"] = pd.to_numeric(frame[weight_column], errors="coerce")
    if cluster_column is not None:
        if cluster_column not in frame.columns:
            raise KeyError(f"missing cluster column: {cluster_column}")
        data["_cluster"] = frame[cluster_column].astype(str)
    data = data.dropna()

    outcome = pd.to_numeric(data[outcome_column], errors="coerce")
    if outcome.min() < 0.0 or outcome.max() > 1.0:
        raise ValueError(
            f"{outcome_column} must lie on the unit interval for a fractional logit"
        )

    design = data[condition_columns].apply(pd.to_numeric, errors="coerce")
    for control in controls:
        series = data[control]
        if pd.api.types.is_numeric_dtype(series) and series.nunique() > 12:
            design[control] = pd.to_numeric(series, errors="coerce")
        else:
            dummies = pd.get_dummies(series.astype(str), prefix=control, drop_first=True)
            design = pd.concat([design, dummies.astype(float)], axis=1)
    exog = sm.add_constant(design, has_constant="add")

    weights = (
        data["_weight"].to_numpy(dtype=float)
        if weight_column is not None
        else np.ones(len(data), dtype=float)
    )
    if weight_column is not None and len(weights):
        weights = weights / weights.sum() * len(weights)

    model = sm.GLM(
        outcome.to_numpy(dtype=float),
        exog.to_numpy(dtype=float),
        family=sm.families.Binomial(),
        freq_weights=weights,
    )
    if cluster_column is not None:
        groups = pd.factorize(data["_cluster"])[0]
        result = model.fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        result = model.fit(cov_type="HC3")

    confidence = result.conf_int()
    coefficients = pd.DataFrame(
        {
            "term": list(exog.columns),
            "estimate": np.asarray(result.params, dtype=float),
            "std_error": np.asarray(result.bse, dtype=float),
            "p_value": np.asarray(result.pvalues, dtype=float),
            "ci_lower": np.asarray(confidence, dtype=float)[:, 0],
            "ci_upper": np.asarray(confidence, dtype=float)[:, 1],
        }
    )
    specification: dict[str, object] = {
        "outcome": outcome_column,
        "outcome_scale": "observed innovation measure on the unit interval",
        "conditions": condition_columns,
        "controls": controls,
        "weight_column": weight_column,
        "weighting": "survey weights rescaled to sum to the sample size"
        if weight_column
        else "unweighted",
        "cluster_column": cluster_column,
        "cov_type": "cluster" if cluster_column else "HC3",
        "n": len(data),
        "interpretation": (
            "Net associations under an additive model. Not a test of the "
            "configurational results and not comparable term by term."
        ),
    }
    return NetEffectModel(coefficients=coefficients, specification=specification)
