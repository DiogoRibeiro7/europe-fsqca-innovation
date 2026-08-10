"""Analytical-sample construction with an explicit attrition record.

Requiring every condition to be observed can silently change the population a
solution refers to. Each sample therefore records how many establishments and
how much weight mass survive each documented rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from euro_fsqca.config import AnalysisConfig, SampleFilter, SampleSpec, TimingConfig


@dataclass
class AttritionRecorder:
    """Accumulates population counts as inclusion rules are applied."""

    sample: str
    weight_column: str | None = None
    rows: list[dict[str, object]] = field(default_factory=list)

    def record(self, frame: pd.DataFrame, *, step: str, rule: str) -> None:
        """Record the population remaining after one step."""
        self.rows.append(
            {
                "sample": self.sample,
                "step": step,
                "rule": rule,
                "n_establishments": len(frame),
                "weight_mass": self._weight_mass(frame),
                "n_countries": self._distinct(frame, "country"),
            }
        )

    def table(self) -> pd.DataFrame:
        """Return the attrition table with per-step losses."""
        table = pd.DataFrame(self.rows)
        if table.empty:
            return table
        table["n_dropped"] = table["n_establishments"].shift(1) - table["n_establishments"]
        table.loc[table.index[0], "n_dropped"] = 0
        start = float(table["n_establishments"].iloc[0])
        table["retained_share"] = table["n_establishments"] / start if start else float("nan")
        return table

    def _weight_mass(self, frame: pd.DataFrame) -> float:
        if not self.weight_column or self.weight_column not in frame.columns:
            return float(len(frame))
        return float(pd.to_numeric(frame[self.weight_column], errors="coerce").sum())

    def _distinct(self, frame: pd.DataFrame, column: str) -> int:
        if column not in frame.columns:
            return 0
        return int(frame[column].nunique(dropna=True))


def filter_mask(frame: pd.DataFrame, rule: SampleFilter) -> pd.Series:
    """Return the inclusion mask implied by one documented filter."""
    if rule.column not in frame.columns:
        raise KeyError(f"sample filter references missing column: {rule.column}")
    column = frame[rule.column]
    mask = pd.Series(True, index=frame.index)
    if rule.require_non_missing:
        mask &= column.notna()
    if rule.min is not None or rule.max is not None:
        numeric = pd.to_numeric(column, errors="coerce")
        if rule.min is not None:
            mask &= numeric >= rule.min
        if rule.max is not None:
            mask &= numeric <= rule.max
    if rule.isin is not None:
        allowed = {str(value) for value in rule.isin}
        mask &= column.astype(str).isin(allowed)
    return mask.fillna(False).astype(bool)


def select_sample(
    frame: pd.DataFrame,
    *,
    sample: SampleSpec,
    weight_column: str | None = None,
) -> tuple[pd.DataFrame, AttritionRecorder]:
    """Apply a sample definition to the pre-calibration table."""
    recorder = AttritionRecorder(sample=sample.label, weight_column=weight_column)
    recorder.record(frame, step="start", rule="harmonised analytical table")
    selected = frame
    for rule in sample.filters:
        selected = selected.loc[filter_mask(selected, rule)]
        recorder.record(
            selected,
            step="filter",
            rule=rule.description or _rule_text(rule),
        )
    return selected.copy(), recorder


def assign_period(frame: pd.DataFrame, timing: TimingConfig) -> pd.DataFrame:
    """Attach a survey-period label derived from the configured survey year."""
    if not timing.periods or not timing.year_column:
        return frame
    if timing.year_column not in frame.columns:
        raise KeyError(f"missing survey year column: {timing.year_column}")
    lookup = {year: label for label, years in timing.periods.items() for year in years}
    years = pd.to_numeric(frame[timing.year_column], errors="coerce")
    result = frame.copy()
    result[timing.period_column] = years.map(
        lambda value: lookup.get(_as_year(value), "unassigned")
    )
    return result


def timing_summary(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
) -> pd.DataFrame:
    """Summarise fieldwork timing and the innovation reference window by country."""
    year_column = config.timing.year_column
    if not year_column or year_column not in frame.columns:
        return pd.DataFrame(
            columns=[
                "country",
                "n",
                "survey_years",
                "min_year",
                "max_year",
                "reference_window_start",
                "reference_window_end",
                "periods",
            ]
        )
    reference = config.timing.reference_period_years
    rows: list[dict[str, object]] = []
    for country, group in frame.groupby(config.country_column, observed=True):
        years = pd.to_numeric(group[year_column], errors="coerce").dropna().astype(int)
        if years.empty:
            continue
        periods = (
            sorted(group[config.timing.period_column].astype(str).unique())
            if config.timing.period_column in group.columns
            else []
        )
        rows.append(
            {
                "country": str(country),
                "n": len(group),
                "survey_years": ";".join(str(year) for year in sorted(years.unique())),
                "min_year": int(years.min()),
                "max_year": int(years.max()),
                "reference_window_start": int(years.min()) - reference,
                "reference_window_end": int(years.max()),
                "periods": ";".join(periods),
            }
        )
    return pd.DataFrame(rows).sort_values("country", ignore_index=True)


def _rule_text(rule: SampleFilter) -> str:
    parts: list[str] = []
    if rule.require_non_missing:
        parts.append("observed")
    if rule.min is not None:
        parts.append(f">= {rule.min:g}")
    if rule.max is not None:
        parts.append(f"<= {rule.max:g}")
    if rule.isin is not None:
        parts.append("in " + ";".join(str(value) for value in rule.isin))
    return f"{rule.column} {' and '.join(parts)}"


def _as_year(value: float) -> int:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return -1
    return int(value)
