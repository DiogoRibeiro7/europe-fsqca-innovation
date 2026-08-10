"""Cross-regional portability diagnostics for sufficient configurations.

The unit of portability is the individual configuration term, not a solution
string. A term discovered in a source region is re-evaluated in each target
region under the same Europe-wide calibration, with bootstrap uncertainty for
both the source discovery step and the target evaluation step. Directionality
is retained throughout: a Southern recipe travelling North is a different claim
from a Northern recipe travelling South.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from euro_fsqca.qca.fuzzy import configuration_membership, sufficiency_fit
from euro_fsqca.qca.minimize import format_literals, minimize_truth_table, solution_terms
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table


@dataclass(frozen=True)
class PortabilitySummary:
    """Regional fit and heterogeneity for one configuration."""

    table: pd.DataFrame
    consistency_sd: float
    consistency_range: float


@dataclass(frozen=True)
class PortabilityThresholds:
    """Decision rule for calling a configuration portable to a target region."""

    consistency: float = 0.80
    min_available_cases: int = 10


def _weights_of(frame: pd.DataFrame, weight_column: str | None) -> pd.Series | None:
    if weight_column is None or weight_column not in frame.columns:
        return None
    return frame[weight_column].astype(float)


@dataclass(frozen=True)
class TargetFit:
    """Fit of one configuration inside one target group."""

    n: int
    available_cases: int
    availability: float
    consistency: float
    coverage: float
    pri: float
    contradiction_rate: float

    def as_row(self) -> dict[str, object]:
        """Return the fit as a table row."""
        return {
            "n": self.n,
            "available_cases": self.available_cases,
            "availability": self.availability,
            "consistency": self.consistency,
            "coverage": self.coverage,
            "pri": self.pri,
            "contradiction_rate": self.contradiction_rate,
        }


def _fit_row(
    group: pd.DataFrame,
    *,
    literals: dict[str, bool],
    outcome: str,
    weight_column: str | None,
) -> TargetFit:
    membership = configuration_membership(group, literals)
    weights = _weights_of(group, weight_column)
    fit = sufficiency_fit(
        membership.to_numpy(),
        group[outcome].to_numpy(dtype=float),
        weights=None if weights is None else weights.to_numpy(),
    )
    relevant = membership > 0.5
    contradiction = relevant & (group[outcome] <= 0.5)
    available_cases = int(relevant.sum())
    return TargetFit(
        n=len(group),
        available_cases=available_cases,
        availability=float(relevant.mean()) if len(relevant) else 0.0,
        consistency=fit.consistency,
        coverage=fit.coverage,
        pri=fit.pri if fit.pri is not None else float("nan"),
        contradiction_rate=(
            float(contradiction.sum() / available_cases) if available_cases else float("nan")
        ),
    )


def evaluate_portability(
    frame: pd.DataFrame,
    *,
    literals: dict[str, bool],
    outcome: str,
    region_column: str = "macroregion",
    weight_column: str | None = None,
) -> PortabilitySummary:
    """Evaluate identical fuzzy configuration membership in each region."""
    rows: list[dict[str, object]] = []
    for region, group in frame.groupby(region_column, observed=True):
        rows.append(
            {
                "region": str(region),
                **_fit_row(
                    group, literals=literals, outcome=outcome, weight_column=weight_column
                ).as_row(),
            }
        )
    table = pd.DataFrame(rows).sort_values("region", ignore_index=True)
    consistencies = table["consistency"].dropna().to_numpy(dtype=float)
    sd = float(np.std(consistencies, ddof=0)) if len(consistencies) else float("nan")
    spread = float(np.ptp(consistencies)) if len(consistencies) else float("nan")
    return PortabilitySummary(table=table, consistency_sd=sd, consistency_range=spread)


def directed_portability(
    frame: pd.DataFrame,
    *,
    configurations: dict[str, list[dict[str, bool]]],
    outcome: str,
    region_column: str = "macroregion",
    weight_column: str | None = None,
    thresholds: PortabilityThresholds | None = None,
    n_bootstrap: int = 0,
    seed: int = 42,
    confidence: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate source-region configurations in every other target region."""
    rule = thresholds or PortabilityThresholds()
    rows: list[dict[str, object]] = []
    regions = sorted(str(region) for region in frame[region_column].dropna().unique())
    for source_region, source_terms in configurations.items():
        for term_index, literals in enumerate(source_terms, start=1):
            for target_region in regions:
                if target_region == source_region:
                    continue
                group = frame[frame[region_column].astype(str) == target_region]
                metrics = _fit_row(
                    group, literals=literals, outcome=outcome, weight_column=weight_column
                )
                interval = _bootstrap_consistency(
                    group,
                    literals=literals,
                    outcome=outcome,
                    weight_column=weight_column,
                    n_bootstrap=n_bootstrap,
                    seed=seed + term_index,
                    confidence=confidence,
                )
                consistency = metrics.consistency
                available_cases = metrics.available_cases
                rows.append(
                    {
                        "source_region": source_region,
                        "source_term": term_index,
                        "target_region": target_region,
                        "configuration": format_literals(literals),
                        "target_n": metrics.n,
                        "available_cases": available_cases,
                        "availability": metrics.availability,
                        "consistency": consistency,
                        "coverage": metrics.coverage,
                        "pri": metrics.pri,
                        "contradiction_rate": metrics.contradiction_rate,
                        "consistency_ci_lower": interval[0],
                        "consistency_ci_upper": interval[1],
                        "n_bootstrap": n_bootstrap,
                        "portable": bool(
                            consistency >= rule.consistency
                            and available_cases >= rule.min_available_cases
                        ),
                        "portable_lower_bound": bool(
                            not np.isnan(interval[0]) and interval[0] >= rule.consistency
                        ),
                    }
                )
    table = pd.DataFrame(rows)
    if table.empty:
        return table, pd.DataFrame(), pd.DataFrame()
    matrix = portability_matrix(table)
    network = table.rename(
        columns={
            "source_region": "source",
            "target_region": "target",
            "consistency": "weight",
        }
    )[
        [
            "source",
            "target",
            "source_term",
            "configuration",
            "weight",
            "consistency_ci_lower",
            "consistency_ci_upper",
            "availability",
            "available_cases",
            "portable",
        ]
    ]
    return table, matrix, network


def portability_matrix(table: pd.DataFrame) -> pd.DataFrame:
    """Aggregate directed term-level portability to region pairs.

    Averaging consistency across structurally different terms has no clean
    substantive meaning, so the headline aggregate is the share of source terms
    that clear the portability rule in the target region. Consistency is
    summarised by its median and by an availability-weighted mean, and both are
    reported alongside the term count they rest on.
    """
    if table.empty:
        return pd.DataFrame(
            columns=[
                "source_region",
                "target_region",
                "n_terms",
                "n_portable",
                "share_portable",
                "consistency_median",
                "consistency_min",
                "consistency_max",
                "consistency_availability_weighted_mean",
                "mean_available_cases",
            ]
        )
    rows: list[dict[str, object]] = []
    for (source, target), group in table.groupby(
        ["source_region", "target_region"], observed=True
    ):
        consistency = group["consistency"].astype(float)
        available = group["available_cases"].astype(float)
        valid = consistency.notna() & (available > 0)
        weighted_mean = (
            float(np.average(consistency[valid], weights=available[valid]))
            if bool(valid.any())
            else float("nan")
        )
        rows.append(
            {
                "source_region": str(source),
                "target_region": str(target),
                "n_terms": len(group),
                "n_portable": int(group["portable"].sum()),
                "share_portable": float(group["portable"].mean()),
                "consistency_median": float(consistency.median()),
                "consistency_min": float(consistency.min()),
                "consistency_max": float(consistency.max()),
                "consistency_availability_weighted_mean": weighted_mean,
                "mean_available_cases": float(available.mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["source_region", "target_region"], ignore_index=True
    )


def bootstrap_directed_portability(
    frame: pd.DataFrame,
    *,
    outcome: str,
    conditions: list[str],
    thresholds: TruthTableThresholds,
    region_column: str = "macroregion",
    weight_column: str | None = None,
    n_bootstrap: int = 100,
    seed: int = 42,
    portability: PortabilityThresholds | None = None,
) -> pd.DataFrame:
    """Bootstrap source-region solution discovery and target-region evaluation.

    Each replicate resamples the source region, re-derives its conservative
    solution, and evaluates every discovered term in a resampled target region.
    The result separates two distinct uncertainties: whether a configuration is
    a stable feature of the source region at all, and whether it transfers.
    """
    rule = portability or PortabilityThresholds()
    regions = sorted(str(region) for region in frame[region_column].dropna().unique())
    if n_bootstrap < 1 or len(regions) < 2:
        return pd.DataFrame(
            columns=[
                "source_region",
                "target_region",
                "configuration",
                "n_bootstrap",
                "discovery_frequency",
                "consistency_mean",
                "consistency_ci_lower",
                "consistency_ci_upper",
                "portable_frequency",
            ]
        )
    rng = np.random.default_rng(seed)
    records: list[dict[str, object]] = []
    for source_region in regions:
        source_frame = frame[frame[region_column].astype(str) == source_region]
        if source_frame.empty:
            continue
        for replicate in range(n_bootstrap):
            source_sample = source_frame.sample(
                n=len(source_frame), replace=True, random_state=int(rng.integers(0, 2**31 - 1))
            )
            table = build_truth_table(
                source_sample,
                conditions=conditions,
                outcome=outcome,
                thresholds=thresholds,
                weights=_weights_of(source_sample, weight_column),
            )
            solution = minimize_truth_table(table, conditions=conditions, kind="conservative")
            for literals in solution_terms(solution, conditions):
                for target_region in regions:
                    if target_region == source_region:
                        continue
                    target_frame = frame[frame[region_column].astype(str) == target_region]
                    target_sample = target_frame.sample(
                        n=len(target_frame),
                        replace=True,
                        random_state=int(rng.integers(0, 2**31 - 1)),
                    )
                    metrics = _fit_row(
                        target_sample,
                        literals=literals,
                        outcome=outcome,
                        weight_column=weight_column,
                    )
                    records.append(
                        {
                            "source_region": source_region,
                            "target_region": target_region,
                            "configuration": format_literals(literals),
                            "replicate": replicate,
                            "consistency": metrics.consistency,
                            "available_cases": metrics.available_cases,
                            "portable": bool(
                                metrics.consistency >= rule.consistency
                                and metrics.available_cases >= rule.min_available_cases
                            ),
                        }
                    )
    if not records:
        return pd.DataFrame(
            columns=[
                "source_region",
                "target_region",
                "configuration",
                "n_bootstrap",
                "discovery_frequency",
                "consistency_mean",
                "consistency_ci_lower",
                "consistency_ci_upper",
                "portable_frequency",
            ]
        )
    draws = pd.DataFrame(records)
    rows: list[dict[str, object]] = []
    for (source, target, configuration), group in draws.groupby(
        ["source_region", "target_region", "configuration"], observed=True
    ):
        consistency = group["consistency"].astype(float).dropna()
        replicates = group["replicate"].nunique()
        rows.append(
            {
                "source_region": str(source),
                "target_region": str(target),
                "configuration": str(configuration),
                "n_bootstrap": int(n_bootstrap),
                "discovery_frequency": float(replicates / n_bootstrap),
                "consistency_mean": float(consistency.mean()) if not consistency.empty else np.nan,
                "consistency_ci_lower": (
                    float(np.quantile(consistency, 0.025)) if not consistency.empty else np.nan
                ),
                "consistency_ci_upper": (
                    float(np.quantile(consistency, 0.975)) if not consistency.empty else np.nan
                ),
                "portable_frequency": float(group["portable"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["source_region", "target_region", "discovery_frequency"],
        ascending=[True, True, False],
        ignore_index=True,
    )


def country_portability(
    frame: pd.DataFrame,
    *,
    configurations: dict[str, list[dict[str, bool]]],
    outcome: str,
    country_column: str = "country",
    weight_column: str | None = None,
    min_cases: int = 30,
) -> pd.DataFrame:
    """Evaluate known configurations within each country."""
    rows: list[dict[str, object]] = []
    for source, source_terms in configurations.items():
        for term_index, literals in enumerate(source_terms, start=1):
            for country, group in frame.groupby(country_column, observed=True):
                metrics = _fit_row(
                    group, literals=literals, outcome=outcome, weight_column=weight_column
                )
                rows.append(
                    {
                        "source": source,
                        "term": term_index,
                        "configuration": format_literals(literals),
                        "country": str(country),
                        "weak_sample": metrics.n < min_cases,
                        **metrics.as_row(),
                    }
                )
    return pd.DataFrame(rows)


def _bootstrap_consistency(
    group: pd.DataFrame,
    *,
    literals: dict[str, bool],
    outcome: str,
    weight_column: str | None,
    n_bootstrap: int,
    seed: int,
    confidence: float,
) -> tuple[float, float]:
    """Return a percentile interval for target-region consistency."""
    if n_bootstrap < 1 or group.empty:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    membership = configuration_membership(group, literals).to_numpy(dtype=float)
    outcome_values = group[outcome].to_numpy(dtype=float)
    weights = _weights_of(group, weight_column)
    weight_values = None if weights is None else weights.to_numpy(dtype=float)
    n_cases = len(group)
    draws: list[float] = []
    for _ in range(n_bootstrap):
        index = rng.integers(0, n_cases, size=n_cases)
        fit = sufficiency_fit(
            membership[index],
            outcome_values[index],
            weights=None if weight_values is None else weight_values[index],
        )
        if not np.isnan(fit.consistency):
            draws.append(fit.consistency)
    if not draws:
        return (float("nan"), float("nan"))
    alpha = (1.0 - confidence) / 2.0
    return (
        float(np.quantile(draws, alpha)),
        float(np.quantile(draws, 1.0 - alpha)),
    )
