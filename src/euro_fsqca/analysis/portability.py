"""Cross-regional portability diagnostics for sufficient configurations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from euro_fsqca.qca.fuzzy import configuration_membership, sufficiency_fit


@dataclass(frozen=True)
class PortabilitySummary:
    """Regional fit and heterogeneity for one configuration."""

    table: pd.DataFrame
    consistency_sd: float
    consistency_range: float


def evaluate_portability(
    frame: pd.DataFrame,
    *,
    literals: dict[str, bool],
    outcome: str,
    region_column: str = "macroregion",
) -> PortabilitySummary:
    """Evaluate identical fuzzy configuration membership in each region."""
    rows: list[dict[str, object]] = []
    for region, group in frame.groupby(region_column, observed=True):
        membership = configuration_membership(group, literals)
        fit = sufficiency_fit(membership.to_numpy(), group[outcome].to_numpy(dtype=float))
        relevant = membership > 0.5
        contradiction = relevant & (group[outcome] <= 0.5)
        rows.append(
            {
                "region": str(region),
                "n": len(group),
                "available_cases": int(relevant.sum()),
                "availability": float(relevant.mean()) if len(relevant) else 0.0,
                "contradiction_rate": float(contradiction.sum() / relevant.sum())
                if int(relevant.sum())
                else float("nan"),
                "consistency": fit.consistency,
                "coverage": fit.coverage,
                "pri": fit.pri,
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
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate source-region configurations in every other target region."""
    rows: list[dict[str, object]] = []
    regions = sorted(str(region) for region in frame[region_column].dropna().unique())
    for source_region, source_terms in configurations.items():
        for term_index, literals in enumerate(source_terms, start=1):
            for target_region in regions:
                if target_region == source_region:
                    continue
                group = frame[frame[region_column].astype(str) == target_region]
                membership = configuration_membership(group, literals)
                fit = sufficiency_fit(membership.to_numpy(), group[outcome].to_numpy(dtype=float))
                relevant = membership > 0.5
                contradiction = relevant & (group[outcome] <= 0.5)
                available_cases = int(relevant.sum())
                rows.append(
                    {
                        "source_region": source_region,
                        "source_term": term_index,
                        "target_region": target_region,
                        "configuration": _format_literals(literals),
                        "target_n": int(len(group)),
                        "available_cases": available_cases,
                        "availability": float(relevant.mean()) if len(relevant) else 0.0,
                        "consistency": fit.consistency,
                        "coverage": fit.coverage,
                        "pri": fit.pri,
                        "contradiction_rate": float(contradiction.sum() / available_cases)
                        if available_cases
                        else float("nan"),
                    }
                )
    table = pd.DataFrame(rows)
    if table.empty:
        return table, pd.DataFrame(), pd.DataFrame()
    matrix = table.pivot_table(
        index="source_region",
        columns="target_region",
        values="consistency",
        aggfunc="mean",
    ).reset_index()
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
            "availability",
            "available_cases",
        ]
    ]
    return table, matrix, network


def country_portability(
    frame: pd.DataFrame,
    *,
    configurations: dict[str, list[dict[str, bool]]],
    outcome: str,
    country_column: str = "country",
    min_cases: int = 30,
) -> pd.DataFrame:
    """Evaluate known configurations within each country."""
    rows: list[dict[str, object]] = []
    for source, source_terms in configurations.items():
        for term_index, literals in enumerate(source_terms, start=1):
            for country, group in frame.groupby(country_column, observed=True):
                membership = configuration_membership(group, literals)
                fit = sufficiency_fit(membership.to_numpy(), group[outcome].to_numpy(dtype=float))
                relevant = membership > 0.5
                contradiction = relevant & (group[outcome] <= 0.5)
                available_cases = int(relevant.sum())
                rows.append(
                    {
                        "source": source,
                        "term": term_index,
                        "configuration": _format_literals(literals),
                        "country": str(country),
                        "n": int(len(group)),
                        "weak_sample": int(len(group)) < min_cases,
                        "available_cases": available_cases,
                        "availability": float(relevant.mean()) if len(relevant) else 0.0,
                        "consistency": fit.consistency,
                        "coverage": fit.coverage,
                        "pri": fit.pri,
                        "contradiction_rate": float(contradiction.sum() / available_cases)
                        if available_cases
                        else float("nan"),
                    }
                )
    return pd.DataFrame(rows)


def _format_literals(literals: dict[str, bool]) -> str:
    return "*".join(f"{'' if present else '~'}{name}" for name, present in sorted(literals.items()))
