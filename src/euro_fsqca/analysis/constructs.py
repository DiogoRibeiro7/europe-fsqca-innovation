"""Pre-calibration diagnostics for configured innovation constructs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from euro_fsqca.config import AnalysisConfig, SetSpec
from euro_fsqca.data.io import write_table
from euro_fsqca.sets.composites import build_composite


def construct_values(frame: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    """Build raw configured construct values before fuzzy calibration."""
    result = pd.DataFrame(index=frame.index)
    for column in [config.case_id, config.country_column, "macroregion", "region"]:
        if column in frame.columns and column not in result.columns:
            result[column] = frame[column]
    for name, spec in {**config.conditions, **config.outcome}.items():
        result[name] = _raw_values(frame, spec)
    return result


def construct_summary(values: pd.DataFrame, *, constructs: list[str]) -> pd.DataFrame:
    """Summarise construct distributions, missingness, and outliers."""
    rows: list[dict[str, object]] = []
    for construct in constructs:
        series = pd.to_numeric(values[construct], errors="coerce")
        valid = series.dropna()
        rows.append(
            {
                "construct": construct,
                "n": int(len(series)),
                "n_non_missing": int(valid.shape[0]),
                "missing_share": float(series.isna().mean()) if len(series) else 0.0,
                "mean": float(valid.mean()) if not valid.empty else float("nan"),
                "std": float(valid.std(ddof=0)) if len(valid) > 1 else float("nan"),
                "min": float(valid.min()) if not valid.empty else float("nan"),
                "p25": _quantile(valid, 0.25),
                "median": _quantile(valid, 0.50),
                "p75": _quantile(valid, 0.75),
                "max": float(valid.max()) if not valid.empty else float("nan"),
                "n_outliers_iqr": _iqr_outliers(valid),
                "effective_sample_size": int(valid.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def construct_group_summary(
    values: pd.DataFrame,
    *,
    constructs: list[str],
    group_column: str,
) -> pd.DataFrame:
    """Summarise constructs by country or region."""
    if group_column not in values.columns:
        return pd.DataFrame(
            columns=[
                group_column,
                "construct",
                "n",
                "n_non_missing",
                "missing_share",
                "mean",
                "median",
            ]
        )
    rows: list[dict[str, object]] = []
    for group, subset in values.groupby(group_column, dropna=False, observed=True):
        for construct in constructs:
            series = pd.to_numeric(subset[construct], errors="coerce")
            valid = series.dropna()
            rows.append(
                {
                    group_column: group,
                    "construct": construct,
                    "n": int(len(series)),
                    "n_non_missing": int(valid.shape[0]),
                    "missing_share": float(series.isna().mean()) if len(series) else 0.0,
                    "mean": float(valid.mean()) if not valid.empty else float("nan"),
                    "median": _quantile(valid, 0.50),
                }
            )
    return pd.DataFrame(rows)


def construct_correlations(values: pd.DataFrame, *, constructs: list[str]) -> pd.DataFrame:
    """Return pairwise construct correlations in long format."""
    numeric = values[constructs].apply(pd.to_numeric, errors="coerce")
    corr = numeric.corr()
    rows: list[dict[str, object]] = []
    for left in constructs:
        for right in constructs:
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "correlation": float(corr.loc[left, right])
                    if not pd.isna(corr.loc[left, right])
                    else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def component_correlations(frame: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    """Return correlations among components for configured multi-item constructs."""
    rows: list[dict[str, object]] = []
    for name, spec in {**config.conditions, **config.outcome}.items():
        if spec.composite is None or len(spec.composite.columns) < 2:
            continue
        columns = spec.composite.columns
        corr = frame[columns].apply(pd.to_numeric, errors="coerce").corr()
        for left in columns:
            for right in columns:
                rows.append(
                    {
                        "construct": name,
                        "left": left,
                        "right": right,
                        "correlation": float(corr.loc[left, right])
                        if not pd.isna(corr.loc[left, right])
                        else float("nan"),
                    }
                )
    return pd.DataFrame(rows, columns=["construct", "left", "right", "correlation"])


def write_construct_diagnostics(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    output_dir: str | Path,
) -> None:
    """Write construct diagnostics to a directory."""
    target = Path(output_dir)
    values = construct_values(frame, config)
    constructs = [*config.conditions, config.outcome_name]
    write_table(construct_summary(values, constructs=constructs), target / "construct_summary.csv")
    write_table(
        construct_group_summary(values, constructs=constructs, group_column=config.country_column),
        target / "construct_country_summary.csv",
    )
    write_table(
        construct_group_summary(values, constructs=constructs, group_column="macroregion"),
        target / "construct_region_summary.csv",
    )
    write_table(
        construct_correlations(values, constructs=constructs),
        target / "construct_correlations.csv",
    )
    write_table(component_correlations(frame, config), target / "component_correlations.csv")


def _raw_values(frame: pd.DataFrame, spec: SetSpec) -> pd.Series:
    if spec.source is not None:
        if spec.source not in frame.columns:
            raise KeyError(f"missing source column: {spec.source}")
        return pd.to_numeric(frame[spec.source], errors="coerce")
    if spec.composite is None:
        raise ValueError("set must define a source or composite")
    return build_composite(frame, spec.composite)


def _quantile(series: pd.Series, q: float) -> float:
    return float(series.quantile(q)) if not series.empty else float("nan")


def _iqr_outliers(series: pd.Series) -> int:
    if series.empty:
        return 0
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if np.isclose(float(iqr), 0.0):
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((series < lower) | (series > upper)).sum())
