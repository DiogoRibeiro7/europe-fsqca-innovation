"""Regional taxonomy helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_region_map(path: str | Path, scheme: str) -> dict[str, str]:
    """Load a country-to-region mapping from YAML."""
    with Path(path).open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict) or scheme not in payload:
        raise KeyError(f"regional scheme {scheme!r} is not defined in {path}")
    scheme_data = payload[scheme]
    if not isinstance(scheme_data, dict):
        raise TypeError("regional scheme must map region names to country lists")

    mapping: dict[str, str] = {}
    for region, countries in scheme_data.items():
        if not isinstance(countries, list):
            raise TypeError(f"region {region!r} must contain a country list")
        for country in countries:
            key = str(country).strip()
            if key in mapping:
                raise ValueError(f"country {key!r} appears in multiple regions")
            mapping[key] = str(region)
    return mapping


def attach_regions(
    frame: pd.DataFrame,
    *,
    country_column: str,
    mapping: dict[str, str],
    output_column: str = "macroregion",
) -> pd.DataFrame:
    """Attach regional labels and fail on unmapped countries."""
    if country_column not in frame.columns:
        raise KeyError(f"missing country column: {country_column}")
    result = frame.copy()
    result[output_column] = result[country_column].astype(str).str.strip().map(mapping)
    missing = sorted(result.loc[result[output_column].isna(), country_column].astype(str).unique())
    if missing:
        raise ValueError(f"unmapped countries: {missing}")
    return result
