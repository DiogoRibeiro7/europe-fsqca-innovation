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


def test_pri_matches_the_canonical_r_engine() -> None:
    # Verified against QCA::truthTable on the synthetic demo: the row 00000 of
    # a five-condition table returned PRI 0.018556. The earlier formula, which
    # subtracted min(x, 1 - y) instead of min(x, y, 1 - y), returned -41.4.
    x = np.array([0.9, 0.8, 0.2, 0.1, 0.6])
    y = np.array([0.7, 0.2, 0.9, 0.4, 0.5])

    fit = sufficiency_fit(x, y)

    intersection = np.minimum(x, y).sum()
    simultaneous = np.minimum(np.minimum(x, y), 1 - y).sum()
    expected = (intersection - simultaneous) / (x.sum() - simultaneous)
    assert fit.pri is not None
    assert math.isclose(fit.pri, expected)
    # PRI is a proportional reduction and cannot be negative for these data.
    assert 0.0 <= fit.pri <= 1.0


def test_pri_never_exceeds_consistency() -> None:
    rng = np.random.default_rng(11)
    for _ in range(50):
        x = rng.uniform(0, 1, 40)
        y = rng.uniform(0, 1, 40)
        fit = sufficiency_fit(x, y)
        assert fit.pri is not None
        assert fit.pri <= fit.consistency + 1e-12
