from __future__ import annotations

import math

import numpy as np

from euro_fsqca.qca.fuzzy import necessity_fit, sufficiency_fit


def test_perfect_sufficiency() -> None:
    x = np.array([0.1, 0.4, 0.8, 0.9])
    y = np.array([0.2, 0.5, 0.9, 1.0])
    fit = sufficiency_fit(x, y)
    assert math.isclose(fit.consistency, 1.0)
    assert fit.coverage < 1.0


def test_perfect_necessity() -> None:
    x = np.array([0.2, 0.5, 0.9, 1.0])
    y = np.array([0.1, 0.4, 0.8, 0.9])
    fit = necessity_fit(x, y)
    assert math.isclose(fit.consistency, 1.0)
    assert fit.coverage < 1.0
