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
        rows.append(
            {
                "region": str(region),
                "n": len(group),
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
