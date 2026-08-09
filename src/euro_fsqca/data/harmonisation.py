"""Diagnostics for harmonised firm-level analytical data."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

REQUIRED_ESTABLISHMENT_IDENTIFIERS = [
    "firm_id",
    "country",
    "region",
    "survey_year",
    "sector",
    "size_class",
    "source_dataset",
]


@dataclass(frozen=True)
class ExclusionRule:
    """A documented rule that flags observations for exclusion."""

    rule_id: str
    reason: str
    predicate: Callable[[pd.DataFrame], pd.Series]


def recode_special_missing(
    frame: pd.DataFrame,
    *,
    rules: Mapping[str, Mapping[object, str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert documented special missing codes to missing values and log counts."""
    result = frame.copy()
    rows: list[dict[str, object]] = []
    for column, codes in rules.items():
        if column not in result.columns:
            rows.append(
                {
                    "column": column,
                    "code": "",
                    "meaning": "column_missing",
                    "n_affected": 0,
                    "countries_affected": "",
                }
            )
            continue
        for code, meaning in codes.items():
            mask = result[column] == code
            rows.append(
                {
                    "column": column,
                    "code": code,
                    "meaning": meaning,
                    "n_affected": int(mask.sum()),
                    "countries_affected": _countries(result, mask),
                }
            )
            result.loc[mask, column] = np.nan
    return result, pd.DataFrame(rows)


def harmonisation_report(
    frame: pd.DataFrame,
    *,
    case_id: str = "firm_id",
    required_identifiers: list[str] | None = None,
    categorical_allowed: Mapping[str, set[object]] | None = None,
    continuous_ranges: Mapping[str, tuple[float, float]] | None = None,
    z_threshold: float = 4.0,
) -> pd.DataFrame:
    """Create diagnostics for a harmonised firm-level table."""
    identifiers = required_identifiers or REQUIRED_ESTABLISHMENT_IDENTIFIERS
    categorical_allowed = categorical_allowed or {}
    continuous_ranges = continuous_ranges or {}
    rows: list[dict[str, object]] = []

    for column in identifiers:
        if column not in frame.columns:
            rows.append(_issue("missing_identifier", column, "required identifier absent", 0, ""))

    for column in frame.columns:
        missing = frame[column].isna()
        if missing.any():
            rows.append(
                _issue(
                    "missingness",
                    str(column),
                    "missing values",
                    int(missing.sum()),
                    _countries(frame, missing),
                )
            )

    if case_id in frame.columns:
        duplicates = frame[case_id].duplicated(keep=False)
        if duplicates.any():
            rows.append(
                _issue(
                    "duplicate_observation",
                    case_id,
                    "duplicate case identifier",
                    int(duplicates.sum()),
                    _countries(frame, duplicates),
                )
            )

    for column, allowed in categorical_allowed.items():
        if column not in frame.columns:
            rows.append(_issue("missing_categorical", column, "categorical column absent", 0, ""))
            continue
        observed = set(frame[column].dropna().unique().tolist())
        unexpected = observed - allowed
        if unexpected:
            mask = frame[column].isin(unexpected)
            rows.append(
                _issue(
                    "unexpected_category",
                    column,
                    ";".join(sorted(str(value) for value in unexpected)),
                    int(mask.sum()),
                    _countries(frame, mask),
                )
            )

    for column, (minimum, maximum) in continuous_ranges.items():
        if column not in frame.columns:
            rows.append(_issue("missing_continuous", column, "continuous column absent", 0, ""))
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        impossible = numeric.notna() & ((numeric < minimum) | (numeric > maximum))
        if impossible.any():
            rows.append(
                _issue(
                    "impossible_value",
                    column,
                    f"outside [{minimum}, {maximum}]",
                    int(impossible.sum()),
                    _countries(frame, impossible),
                )
            )
        valid = numeric.dropna()
        if len(valid) > 1 and not np.isclose(float(valid.std(ddof=0)), 0.0):
            z_scores = (numeric - float(valid.mean())) / float(valid.std(ddof=0))
            extreme = z_scores.abs() > z_threshold
            if extreme.any():
                rows.append(
                    _issue(
                        "extreme_value",
                        column,
                        f"absolute z-score above {z_threshold}",
                        int(extreme.sum()),
                        _countries(frame, extreme),
                    )
                )

    if not rows:
        rows.append(_issue("ok", "", "no diagnostics triggered", 0, ""))
    return pd.DataFrame(rows)


def build_exclusion_log(frame: pd.DataFrame, rules: list[ExclusionRule]) -> pd.DataFrame:
    """Apply exclusion rules and report affected observations."""
    rows: list[dict[str, object]] = []
    for rule in rules:
        mask = rule.predicate(frame).fillna(False).astype(bool)
        rows.append(
            {
                "rule_id": rule.rule_id,
                "reason": rule.reason,
                "n_affected": int(mask.sum()),
                "countries_affected": _countries(frame, mask),
            }
        )
    if not rows:
        rows.append(
            {
                "rule_id": "none",
                "reason": "no exclusion rules configured",
                "n_affected": 0,
                "countries_affected": "",
            }
        )
    return pd.DataFrame(rows)


def _issue(
    issue_type: str,
    column: str,
    detail: str,
    n_affected: int,
    countries_affected: str,
) -> dict[str, object]:
    return {
        "issue_type": issue_type,
        "column": column,
        "detail": detail,
        "n_affected": n_affected,
        "countries_affected": countries_affected,
    }


def _countries(frame: pd.DataFrame, mask: pd.Series) -> str:
    if "country" not in frame.columns:
        return ""
    return ";".join(sorted(str(value) for value in frame.loc[mask, "country"].dropna().unique()))
