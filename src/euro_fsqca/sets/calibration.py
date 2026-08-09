"""Direct calibration of raw measures into fuzzy-set memberships."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from euro_fsqca.config import Anchors


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def direct_calibrate(values: pd.Series, anchors: Anchors) -> pd.Series:
    """Calibrate a monotone fuzzy set using a piecewise logistic direct method.

    The crossover is mapped to 0.5. The exclusion and inclusion anchors are
    mapped to ``1 - idm`` and ``idm`` respectively. Piecewise scaling allows
    asymmetric distances around the crossover while retaining monotonicity.
    Missing raw values remain missing.
    """
    raw = pd.to_numeric(values, errors="coerce").astype(float)
    increasing = anchors.exclusion < anchors.inclusion
    oriented = raw if increasing else -raw
    exclusion = anchors.exclusion if increasing else -anchors.exclusion
    crossover = anchors.crossover if increasing else -anchors.crossover
    inclusion = anchors.inclusion if increasing else -anchors.inclusion

    upper_logit = _logit(anchors.idm)
    arr = oriented.to_numpy(dtype=float)
    logits = np.full(arr.shape, np.nan, dtype=float)

    below = arr < crossover
    above = ~below
    logits[below] = upper_logit * (arr[below] - crossover) / (crossover - exclusion)
    logits[above] = upper_logit * (arr[above] - crossover) / (inclusion - crossover)

    memberships = 1.0 / (1.0 + np.exp(-logits))
    memberships[np.isnan(arr)] = np.nan
    return pd.Series(memberships, index=values.index, name=values.name)


def shift_anchors(anchors: Anchors, proportion: float) -> Anchors:
    """Shift outer anchors toward or away from the crossover for sensitivity tests."""
    if proportion <= -1.0:
        raise ValueError("anchor shift proportion must be greater than -1")
    exclusion = anchors.crossover + (anchors.exclusion - anchors.crossover) * (1 + proportion)
    inclusion = anchors.crossover + (anchors.inclusion - anchors.crossover) * (1 + proportion)
    return Anchors(
        exclusion=exclusion,
        crossover=anchors.crossover,
        inclusion=inclusion,
        idm=anchors.idm,
    )
