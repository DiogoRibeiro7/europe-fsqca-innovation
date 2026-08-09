from __future__ import annotations

import math

import pandas as pd

from euro_fsqca.config import Anchors
from euro_fsqca.sets.calibration import direct_calibrate


def test_direct_calibration_hits_anchors() -> None:
    anchors = Anchors(exclusion=0.0, crossover=50.0, inclusion=100.0, idm=0.95)
    values = pd.Series([0.0, 50.0, 100.0])
    calibrated = direct_calibrate(values, anchors)

    assert math.isclose(calibrated.iloc[0], 0.05, abs_tol=1e-12)
    assert math.isclose(calibrated.iloc[1], 0.50, abs_tol=1e-12)
    assert math.isclose(calibrated.iloc[2], 0.95, abs_tol=1e-12)


def test_decreasing_calibration_is_supported() -> None:
    anchors = Anchors(exclusion=100.0, crossover=50.0, inclusion=0.0, idm=0.95)
    values = pd.Series([0.0, 50.0, 100.0])
    calibrated = direct_calibrate(values, anchors)

    assert calibrated.iloc[0] > calibrated.iloc[1] > calibrated.iloc[2]
