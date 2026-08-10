"""Synthetic data generator for a fully runnable repository demonstration.

The generator imitates the *structure* of a stratified establishment survey —
unequal sampling weights, size and sector strata, staggered fieldwork years —
so that the design-aware code paths are exercised. It imitates nothing about
the substantive content of the World Bank Enterprise Surveys and must never be
read as evidence about European firms.
"""

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

SECTORS = ["manufacturing", "retail", "other_services"]
SIZE_CLASSES = ["small", "medium", "large"]
SURVEY_YEARS = [2018, 2019, 2020, 2021, 2022]


def generate_demo(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic establishments with region-dependent innovation recipes."""
    if n < 100:
        raise ValueError("demo sample should contain at least 100 cases")
    rng = np.random.default_rng(seed)
    region = rng.choice(list(COUNTRIES), size=n, p=[0.42, 0.25, 0.33])
    country = np.array([rng.choice(COUNTRIES[str(item)]) for item in region], dtype=object)
    sector = rng.choice(SECTORS, size=n, p=[0.40, 0.25, 0.35])
    size_class = rng.choice(SIZE_CLASSES, size=n, p=[0.55, 0.30, 0.15])

    # Fieldwork is staggered by country, as it was across EU-27 between 2018
    # and 2022, so the innovation reference window differs between respondents.
    country_year = {
        name: int(rng.choice(SURVEY_YEARS))
        for name in sorted({str(value) for value in country})
    }
    survey_year = np.array([country_year[str(value)] for value in country], dtype=int)

    # Larger strata are deliberately over-sampled, so their weights are smaller.
    base_weight = np.select(
        [size_class == "small", size_class == "medium"],
        [4.0, 1.6],
        default=0.5,
    )
    sampling_weight = base_weight * rng.lognormal(0.0, 0.35, n)
    n_employees = np.select(
        [size_class == "small", size_class == "medium"],
        [rng.integers(5, 20, n), rng.integers(20, 100, n)],
        default=rng.integers(100, 900, n),
    ).astype(int)

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

    frame = pd.DataFrame(
        {
            "firm_id": [f"F{i:06d}" for i in range(1, n + 1)],
            "country": country,
            "sector": sector,
            "size_class": size_class,
            "n_employees": n_employees,
            "survey_year": survey_year,
            "sampling_weight": sampling_weight,
            "stratum": [
                f"{c}|{s}|{z}" for c, s, z in zip(country, sector, size_class, strict=True)
            ],
            "digital_raw": clip(digital),
            "human_raw": clip(human),
            "finance_raw": clip(finance),
            "international_raw": clip(international),
            "management_raw": clip(management),
            "external_knowledge_raw": clip(external_knowledge),
            "innovation_raw": clip(innovation),
        }
    )
    # Management practices are only asked of larger establishments, which is the
    # structural feature that makes MGT a restricted-sample condition.
    frame.loc[frame["n_employees"] < 20, "management_raw"] = np.nan
    return frame
