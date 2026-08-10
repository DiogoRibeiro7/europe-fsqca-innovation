"""Configurational complementarity and substitution tests.

Counting how often two conditions appear together in solution terms measures
co-occurrence, not complementarity. Complementarity is a claim about the
conjunction outperforming its parts; substitution is a claim about two
conditions being interchangeable within an otherwise identical context. Both
are tested here directly against the calibrated data and against the structure
of the solution, and both are reported separately from co-occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from euro_fsqca.qca.fuzzy import fuzzy_and, fuzzy_or, sufficiency_fit


@dataclass(frozen=True)
class ComplementarityThresholds:
    """Decision rule for classifying a condition pair."""

    sufficiency: float = 0.80
    margin: float = 0.05
    min_relevant_cases: int = 10


def condition_cooccurrence(
    configurations: dict[str, list[dict[str, bool]]],
) -> pd.DataFrame:
    """Count condition-pair co-occurrence in sufficient configurations.

    This is descriptive bookkeeping over solution terms. It is not evidence of
    complementarity; see :func:`configurational_complementarity`.
    """
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


def configurational_complementarity(
    frame: pd.DataFrame,
    *,
    conditions: list[str],
    outcome: str,
    weights: pd.Series | np.ndarray | None = None,
    thresholds: ComplementarityThresholds | None = None,
) -> pd.DataFrame:
    """Test every condition pair for complementarity or substitution.

    For each pair the sufficiency of the conjunction ``A*B`` is compared with
    the sufficiency of each condition alone, and the sufficiency of the
    disjunction ``A+B`` is compared with both. Two conditions are complements
    when neither alone is sufficient but their conjunction is, and substitutes
    when either alone is sufficient so that the union adds coverage without
    losing consistency.
    """
    rule = thresholds or ComplementarityThresholds()
    weight_values = None if weights is None else np.asarray(weights, dtype=float)
    y = frame[outcome].to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for left, right in combinations(conditions, 2):
        a = frame[left].to_numpy(dtype=float)
        b = frame[right].to_numpy(dtype=float)
        conjunction = fuzzy_and(a, b)
        disjunction = fuzzy_or(a, b)
        fit_a = sufficiency_fit(a, y, weights=weight_values)
        fit_b = sufficiency_fit(b, y, weights=weight_values)
        fit_and = sufficiency_fit(conjunction, y, weights=weight_values)
        fit_or = sufficiency_fit(disjunction, y, weights=weight_values)
        relevant = int((conjunction > 0.5).sum())
        best_single = max(fit_a.consistency, fit_b.consistency)
        gain = fit_and.consistency - best_single
        coverage_loss = max(fit_a.coverage, fit_b.coverage) - fit_and.coverage
        rows.append(
            {
                "left": left,
                "right": right,
                "n_relevant_conjunction": relevant,
                "consistency_left": fit_a.consistency,
                "consistency_right": fit_b.consistency,
                "consistency_conjunction": fit_and.consistency,
                "consistency_disjunction": fit_or.consistency,
                "coverage_left": fit_a.coverage,
                "coverage_right": fit_b.coverage,
                "coverage_conjunction": fit_and.coverage,
                "coverage_disjunction": fit_or.coverage,
                "conjunctural_gain": gain,
                "coverage_cost": coverage_loss,
                "relation": _classify(
                    fit_a.consistency,
                    fit_b.consistency,
                    fit_and.consistency,
                    fit_or.consistency,
                    relevant=relevant,
                    rule=rule,
                ),
            }
        )
    return pd.DataFrame(rows)


def term_substitutability(terms: list[dict[str, bool]]) -> pd.DataFrame:
    """Find conditions that are interchangeable within an identical context.

    Two solution terms that agree on every literal except one, where each holds
    a different condition, identify a substitution: within that shared context
    either condition produces the outcome.
    """
    rows: list[dict[str, object]] = []
    for (left_index, left), (right_index, right) in combinations(enumerate(terms, start=1), 2):
        shared = {
            condition: value
            for condition, value in left.items()
            if right.get(condition) == value
        }
        left_unique = {k: v for k, v in left.items() if k not in shared}
        right_unique = {k: v for k, v in right.items() if k not in shared}
        if len(left_unique) != 1 or len(right_unique) != 1:
            continue
        left_condition, left_value = next(iter(left_unique.items()))
        right_condition, right_value = next(iter(right_unique.items()))
        if left_condition == right_condition:
            continue
        rows.append(
            {
                "term_left": left_index,
                "term_right": right_index,
                "shared_context": _render(shared),
                "substitute_left": _literal(left_condition, left_value),
                "substitute_right": _literal(right_condition, right_value),
                "context_size": len(shared),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "term_left",
            "term_right",
            "shared_context",
            "substitute_left",
            "substitute_right",
            "context_size",
        ],
    )


def _classify(
    consistency_left: float,
    consistency_right: float,
    consistency_and: float,
    consistency_or: float,
    *,
    relevant: int,
    rule: ComplementarityThresholds,
) -> str:
    if relevant < rule.min_relevant_cases or np.isnan(consistency_and):
        return "insufficient_evidence"
    both_single_sufficient = (
        consistency_left >= rule.sufficiency and consistency_right >= rule.sufficiency
    )
    neither_single_sufficient = (
        consistency_left < rule.sufficiency and consistency_right < rule.sufficiency
    )
    if both_single_sufficient and consistency_or >= rule.sufficiency:
        return "substitutes"
    if (
        neither_single_sufficient
        and consistency_and >= rule.sufficiency
        and consistency_and - max(consistency_left, consistency_right) >= rule.margin
    ):
        return "complements"
    if consistency_and - max(consistency_left, consistency_right) >= rule.margin:
        return "conjunctural_gain_without_sufficiency"
    return "independent"


def _pair_type(left: bool, right: bool) -> str:
    if left and right:
        return "positive_positive"
    if not left and not right:
        return "negative_negative"
    return "positive_negative"


def _literal(condition: str, present: bool) -> str:
    return f"{'' if present else '~'}{condition}"


def _render(literals: dict[str, bool]) -> str:
    if not literals:
        return "1"
    return "*".join(_literal(name, value) for name, value in literals.items())
