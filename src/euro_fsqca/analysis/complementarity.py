"""Configurational complementarity diagnostics."""

from __future__ import annotations

from itertools import combinations

import pandas as pd


def condition_pair_matrix(
    configurations: dict[str, list[dict[str, bool]]],
) -> pd.DataFrame:
    """Count condition-pair co-occurrence in sufficient configurations."""
    rows: list[dict[str, object]] = []
    for source, terms in configurations.items():
        for term_index, literals in enumerate(terms, start=1):
            for left, right in combinations(sorted(literals), 2):
                rows.append(
                    {
                        "source": source,
                        "term": term_index,
                        "left": left,
                        "right": right,
                        "left_polarity": "present" if literals[left] else "absent",
                        "right_polarity": "present" if literals[right] else "absent",
                        "pair_type": _pair_type(literals[left], literals[right]),
                    }
                )
    if not rows:
        return pd.DataFrame(
            columns=[
                "source",
                "left",
                "right",
                "left_polarity",
                "right_polarity",
                "pair_type",
                "n_terms",
            ]
        )
    return (
        pd.DataFrame(rows)
        .groupby(["source", "left", "right", "left_polarity", "right_polarity", "pair_type"])
        .size()
        .reset_index(name="n_terms")
    )


def _pair_type(left: bool, right: bool) -> str:
    if left and right:
        return "positive_positive"
    if not left and not right:
        return "negative_negative"
    return "positive_negative"
