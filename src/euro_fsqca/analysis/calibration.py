"""Diagnostics for direct fuzzy-set calibration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.analysis.constructs import construct_values
from euro_fsqca.config import AnalysisConfig, Anchors
from euro_fsqca.data.io import write_table
from euro_fsqca.sets.calibration import direct_calibrate


def calibration_summary(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    near_crossover: float = 0.01,
) -> pd.DataFrame:
    """Summarise anchor placement, membership bounds, and monotonicity."""
    raw_values = construct_values(frame, config)
    rows: list[dict[str, object]] = []
    for name, spec in {**config.conditions, **config.outcome}.items():
        raw = pd.to_numeric(raw_values[name], errors="coerce")
        membership = direct_calibrate(raw, spec.anchors)
        tolerance = abs(spec.anchors.inclusion - spec.anchors.exclusion) * near_crossover
        increasing = spec.anchors.exclusion < spec.anchors.inclusion
        below_exclusion = (
            raw <= spec.anchors.exclusion if increasing else raw >= spec.anchors.exclusion
        )
        above_inclusion = (
            raw >= spec.anchors.inclusion if increasing else raw <= spec.anchors.inclusion
        )
        near = (raw - spec.anchors.crossover).abs() <= tolerance
        bounded = (membership.dropna() >= 0.0) & (membership.dropna() <= 1.0)
        rows.append(
            {
                "set_name": name,
                "exclusion": spec.anchors.exclusion,
                "crossover": spec.anchors.crossover,
                "inclusion": spec.anchors.inclusion,
                "idm": spec.anchors.idm,
                "n": len(raw),
                "n_non_missing": int(raw.notna().sum()),
                "n_below_full_non_membership": int(below_exclusion.sum()),
                "n_near_crossover": int(near.sum()),
                "n_above_full_membership": int(above_inclusion.sum()),
                "n_exact_0_5": int((membership == 0.5).sum()),
                "membership_min": float(membership.min(skipna=True)),
                "membership_max": float(membership.max(skipna=True)),
                "bounds_ok": bool(bounded.all()),
                "monotone_ok": _monotone_ok(raw, membership, spec.anchors),
            }
        )
    return pd.DataFrame(rows)


def calibration_group_summary(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    group_column: str,
) -> pd.DataFrame:
    """Summarise calibrated membership distributions by group."""
    raw_values = construct_values(frame, config)
    if group_column not in raw_values.columns:
        return pd.DataFrame(
            columns=[
                group_column,
                "set_name",
                "n",
                "n_non_missing",
                "mean",
                "median",
                "min",
                "max",
            ]
        )
    rows: list[dict[str, object]] = []
    for group, subset in raw_values.groupby(group_column, dropna=False, observed=True):
        for name, spec in {**config.conditions, **config.outcome}.items():
            membership = direct_calibrate(
                pd.to_numeric(subset[name], errors="coerce"),
                spec.anchors,
            )
            rows.append(
                {
                    group_column: group,
                    "set_name": name,
                    "n": len(membership),
                    "n_non_missing": int(membership.notna().sum()),
                    "mean": float(membership.mean(skipna=True)),
                    "median": float(membership.median(skipna=True)),
                    "min": float(membership.min(skipna=True)),
                    "max": float(membership.max(skipna=True)),
                }
            )
    return pd.DataFrame(rows)


def write_calibration_diagnostics(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    output_dir: str | Path,
) -> None:
    """Write calibration diagnostics to a directory."""
    target = Path(output_dir)
    write_table(calibration_summary(frame, config=config), target / "calibration_summary.csv")
    write_table(
        calibration_group_summary(frame, config=config, group_column=config.country_column),
        target / "calibration_country_summary.csv",
    )
    write_table(
        calibration_group_summary(frame, config=config, group_column="macroregion"),
        target / "calibration_region_summary.csv",
    )


def _monotone_ok(raw: pd.Series, membership: pd.Series, anchors: Anchors) -> bool:
    data = pd.DataFrame({"raw": raw, "membership": membership}).dropna().sort_values("raw")
    if data.empty:
        return True
    diffs = data["membership"].diff().dropna()
    if anchors.exclusion < anchors.inclusion:
        return bool((diffs >= -1e-12).all())
    return bool((diffs <= 1e-12).all())
