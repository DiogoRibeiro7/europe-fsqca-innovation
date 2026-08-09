"""Synthetic data generator for a fully runnable repository demonstration."""

from __future__ import annotations

import numpy as np
import pandas as pd

COUNTRIES = {
    "north_west": [
        "Austria",
        "Belgium",
        "Denmark",
        "Finland",
        "France",
        "Germany",
        "Ireland",
        "Luxembourg",
        "Netherlands",
        "Sweden",
    ],
    "south": ["Cyprus", "Greece", "Italy", "Malta", "Portugal", "Spain"],
    "central_east": [
        "Bulgaria",
        "Croatia",
        "Czechia",
        "Estonia",
        "Hungary",
        "Latvia",
        "Lithuania",
        "Poland",
        "Romania",
        "Slovakia",
        "Slovenia",
    ],
}


def generate_demo(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic firms with region-dependent innovation recipes."""
    if n < 100:
        raise ValueError("demo sample should contain at least 100 cases")
    rng = np.random.default_rng(seed)
    region = rng.choice(list(COUNTRIES), size=n, p=[0.42, 0.25, 0.33])
    country = np.array([rng.choice(COUNTRIES[str(item)]) for item in region], dtype=object)

    # Correlated latent firm capabilities.
    common = rng.normal(0.0, 1.0, n)
    digital = 50 + 15 * (0.45 * common + rng.normal(0, 0.85, n))
    human = 50 + 15 * (0.40 * common + rng.normal(0, 0.90, n))
    finance = 50 + 15 * (0.30 * common + rng.normal(0, 0.95, n))
    international = 50 + 15 * (0.25 * common + rng.normal(0, 1.00, n))
    management = 50 + 15 * (0.35 * common + rng.normal(0, 0.90, n))
    external_knowledge = 50 + 15 * (0.30 * common + rng.normal(0, 0.95, n))

    # Deliberately asymmetric, equifinal recipes for demonstration only.
    # The outcome is generated from conjunctural strengths rather than an additive
    # coefficient model so the synthetic data exercise the intended fsQCA logic.
    nw = region == "north_west"
    south = region == "south"
    north_strength = np.minimum.reduce([digital, human, international])
    south_strength = np.minimum.reduce([management, finance, human])
    east_strength = np.minimum.reduce([external_knowledge, international, human])
    generic_strength = np.minimum.reduce([digital, management, human]) - 4.0
    regional_strength = np.where(nw, north_strength, np.where(south, south_strength, east_strength))
    innovation = np.maximum(regional_strength, generic_strength) + rng.normal(5.0, 3.0, n)

    def clip(values: np.ndarray) -> np.ndarray:
        return np.clip(values, 0, 100)

    return pd.DataFrame(
        {
            "firm_id": [f"F{i:06d}" for i in range(1, n + 1)],
            "country": country,
            "digital_raw": clip(digital),
            "human_raw": clip(human),
            "finance_raw": clip(finance),
            "international_raw": clip(international),
            "management_raw": clip(management),
            "external_knowledge_raw": clip(external_knowledge),
            "innovation_raw": clip(innovation),
        }
    )
