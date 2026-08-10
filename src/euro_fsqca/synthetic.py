"""Known-structure synthetic scenarios for QCA validation."""

from __future__ import annotations

from typing import Literal, cast

import numpy as np
import pandas as pd

ScenarioName = Literal["dig_hc", "dual_path", "asymmetric_path"]


def generate_known_scenario(
    scenario: ScenarioName,
    *,
    n: int = 1000,
    seed: int = 42,
    noise: float = 0.05,
) -> pd.DataFrame:
    """Generate calibrated synthetic data with a known sufficient structure."""
    if n < 50:
        raise ValueError("n must be at least 50")
    rng = np.random.default_rng(seed)
    conditions = {
        name: rng.uniform(0.0, 1.0, n)
        for name in ["DIG", "HC", "FIN", "INT", "MGT", "EXTK"]
    }
    outcome = _scenario_outcome(scenario, conditions)
    if noise:
        outcome = np.clip(outcome + rng.normal(0.0, noise, n), 0.0, 1.0)
    return pd.DataFrame(
        {
            "firm_id": [f"S{i:06d}" for i in range(1, n + 1)],
            "country": rng.choice(["Portugal", "Spain", "Germany"], size=n),
            **conditions,
            "INN": outcome,
        }
    )


def _scenario_outcome(scenario: ScenarioName, c: dict[str, np.ndarray]) -> np.ndarray:
    if scenario == "dig_hc":
        return cast(np.ndarray, np.minimum(c["DIG"], c["HC"]))
    if scenario == "dual_path":
        return cast(
            np.ndarray,
            np.maximum(np.minimum(c["FIN"], c["INT"]), np.minimum(c["MGT"], c["EXTK"])),
        )
    if scenario == "asymmetric_path":
        return cast(
            np.ndarray,
            np.maximum(
                np.minimum.reduce([c["DIG"], c["HC"], c["INT"]]),
                np.minimum(1.0 - c["FIN"], c["MGT"]),
            ),
        )
    raise ValueError(f"unknown scenario: {scenario}")
