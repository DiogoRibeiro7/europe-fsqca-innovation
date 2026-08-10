"""Transparent Boolean minimisation for truth-table solutions."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from itertools import product

import pandas as pd
import sympy as sp

SolutionKind = str


@dataclass(frozen=True)
class BooleanSolution:
    """Conservative, parsimonious, or intermediate Boolean solution."""

    kind: SolutionKind
    expression: str
    sympy_expression: sp.logic.boolalg.Boolean
    terms: tuple[dict[str, bool], ...] = field(default_factory=tuple)
    parsimonious_origin: tuple[dict[str, bool], ...] = field(default_factory=tuple)


def _minterm(row: pd.Series, conditions: list[str]) -> list[int]:
    return [int(row[condition]) for condition in conditions]


def _format_expression(expression: sp.logic.boolalg.Boolean, conditions: list[str]) -> str:
    """Convert a SymPy DNF expression to conventional QCA notation."""
    symbol_map = {str(sp.Symbol(condition)): condition for condition in conditions}
    order = {condition: index for index, condition in enumerate(conditions)}
    if expression is sp.true:
        return "1"
    if expression is sp.false:
        return "0"

    def sort_key(text: str) -> tuple[int, str]:
        condition = text[1:] if text.startswith("~") else text
        return (order.get(condition, len(order)), text)

    def render(node: sp.logic.boolalg.Boolean) -> str:
        if isinstance(node, sp.Symbol):
            return symbol_map[str(node)]
        if isinstance(node, sp.Not):
            return f"~{render(node.args[0])}"
        if isinstance(node, sp.And):
            return "*".join(sorted((render(arg) for arg in node.args), key=sort_key))
        if isinstance(node, sp.Or):
            return " + ".join(sorted((render(arg) for arg in node.args), key=sort_key))
        return str(node)

    return render(expression)


def solution_terms(
    solution: BooleanSolution,
    conditions: list[str],
) -> list[dict[str, bool]]:
    """Extract conjunctions from a Boolean solution in configured condition order."""
    if solution.terms:
        return [
            {condition: term[condition] for condition in conditions if condition in term}
            for term in solution.terms
        ]
    return terms_from_expression(solution.sympy_expression, conditions)


def terms_from_expression(
    expression: sp.logic.boolalg.Boolean,
    conditions: list[str],
) -> list[dict[str, bool]]:
    """Extract conjunctions from a SymPy DNF expression."""
    dnf = sp.to_dnf(expression, simplify=True)
    if dnf is sp.false:
        return []
    disjuncts = dnf.args if isinstance(dnf, sp.Or) else (dnf,)
    terms: list[dict[str, bool]] = []
    for disjunct in disjuncts:
        conjuncts = disjunct.args if isinstance(disjunct, sp.And) else (disjunct,)
        literals: dict[str, bool] = {}
        for literal in conjuncts:
            if isinstance(literal, sp.Symbol):
                literals[str(literal)] = True
            elif isinstance(literal, sp.Not) and isinstance(literal.args[0], sp.Symbol):
                literals[str(literal.args[0])] = False
        if literals:
            terms.append(
                {
                    condition: literals[condition]
                    for condition in conditions
                    if condition in literals
                }
            )
    return terms


def expression_from_terms(
    terms: list[dict[str, bool]],
    conditions: list[str],
) -> sp.logic.boolalg.Boolean:
    """Build a DNF SymPy expression from explicit conjunctions."""
    if not terms:
        return sp.false
    disjuncts = []
    for term in terms:
        literals = [
            sp.Symbol(condition) if term[condition] else sp.Not(sp.Symbol(condition))
            for condition in conditions
            if condition in term
        ]
        disjuncts.append(sp.And(*literals) if len(literals) > 1 else literals[0])
    return sp.Or(*disjuncts) if len(disjuncts) > 1 else disjuncts[0]


def minimize_truth_table(
    truth_table: pd.DataFrame,
    *,
    conditions: list[str],
    kind: SolutionKind = "conservative",
    directional_expectations: Mapping[str, str] | None = None,
) -> BooleanSolution:
    """Minimise positive truth-table rows using exact SOP minimisation.

    ``conservative`` uses no logical remainders. ``parsimonious`` treats
    unobserved rows as don't-cares while preserving observed negative rows.
    ``intermediate`` admits only remainders that are easy counterfactuals
    under the declared directional expectations.
    """
    if kind not in {"conservative", "parsimonious", "intermediate"}:
        raise ValueError("kind must be conservative, parsimonious or intermediate")
    if kind == "intermediate":
        return intermediate_solution(
            truth_table,
            conditions=conditions,
            directional_expectations=directional_expectations or {},
        )

    symbols = [sp.Symbol(condition) for condition in conditions]
    positives = [
        _minterm(row, conditions) for _, row in truth_table[truth_table["positive"]].iterrows()
    ]
    if not positives:
        return BooleanSolution(kind=kind, expression="0", sympy_expression=sp.false)

    dontcares: list[list[int]] = []
    if kind == "parsimonious":
        dontcares = [
            _minterm(row, conditions) for _, row in truth_table[~truth_table["observed"]].iterrows()
        ]

    expression = sp.SOPform(symbols, positives, dontcares=dontcares)
    return BooleanSolution(
        kind=kind,
        expression=_format_expression(expression, conditions),
        sympy_expression=expression,
        terms=tuple(terms_from_expression(expression, conditions)),
    )


def intermediate_solution(
    truth_table: pd.DataFrame,
    *,
    conditions: list[str],
    directional_expectations: Mapping[str, str],
) -> BooleanSolution:
    """Derive the intermediate solution using easy counterfactuals only.

    Each parsimonious implicant is expanded back towards the conservative
    solution by restoring every literal whose removal required a *difficult*
    counterfactual, that is, an unobserved row in which the condition takes the
    value opposite to its declared directional expectation. Conditions declared
    ``either`` impose no restriction, so their removal is always admissible.
    The result is a superset of the parsimonious and a subset of the
    conservative solution, which is what licenses core/peripheral claims.
    """
    parsimonious = minimize_truth_table(truth_table, conditions=conditions, kind="parsimonious")
    parsimonious_terms = solution_terms(parsimonious, conditions)
    if not parsimonious_terms:
        return BooleanSolution(kind="intermediate", expression="0", sympy_expression=sp.false)

    positive_rows = {
        tuple(_minterm(row, conditions))
        for _, row in truth_table[truth_table["positive"]].iterrows()
    }
    remainder_rows = {
        tuple(_minterm(row, conditions))
        for _, row in truth_table[~truth_table["observed"].astype(bool)].iterrows()
    }

    derived: list[tuple[dict[str, bool], dict[str, bool]]] = []
    for parsimonious_term in parsimonious_terms:
        restored = _restore_difficult_literals(
            parsimonious_term,
            conditions=conditions,
            expectations=directional_expectations,
            positive_rows=positive_rows,
            remainder_rows=remainder_rows,
        )
        derived.append((restored, parsimonious_term))

    kept = _drop_redundant_terms(derived)
    terms = [term for term, _ in kept]
    origins = [origin for _, origin in kept]
    expression = expression_from_terms(terms, conditions)
    return BooleanSolution(
        kind="intermediate",
        expression=_format_expression(expression, conditions),
        sympy_expression=expression,
        terms=tuple(terms),
        parsimonious_origin=tuple(origins),
    )


def core_peripheral_table(solution: BooleanSolution, conditions: list[str]) -> pd.DataFrame:
    """Classify intermediate-solution literals as core or peripheral.

    A literal that survives into the parsimonious solution is a core condition;
    one present only in the intermediate solution is peripheral.
    """
    rows: list[dict[str, object]] = []
    terms = solution_terms(solution, conditions)
    origins = list(solution.parsimonious_origin) or [{} for _ in terms]
    for index, (term, origin) in enumerate(zip(terms, origins, strict=False), start=1):
        for condition, present in term.items():
            in_parsimonious = origin.get(condition) == present
            rows.append(
                {
                    "solution": solution.kind,
                    "term": index,
                    "configuration": format_literals(term),
                    "condition": condition,
                    "polarity": "present" if present else "absent",
                    "role": "core" if in_parsimonious else "peripheral",
                }
            )
    return pd.DataFrame(
        rows,
        columns=["solution", "term", "configuration", "condition", "polarity", "role"],
    )


def format_literals(literals: dict[str, bool]) -> str:
    """Render a conjunction in conventional QCA notation."""
    if not literals:
        return "1"
    return "*".join(f"{'' if present else '~'}{name}" for name, present in literals.items())


def _restore_difficult_literals(
    term: dict[str, bool],
    *,
    conditions: list[str],
    expectations: Mapping[str, str],
    positive_rows: set[tuple[int, ...]],
    remainder_rows: set[tuple[int, ...]],
) -> dict[str, bool]:
    """Add back literals whose removal relied on a difficult counterfactual."""
    expansion = list(_expansion(term, conditions))
    additions: dict[str, bool] = {}
    for position, condition in enumerate(conditions):
        if condition in term:
            continue
        direction = expectations.get(condition, "either")
        if direction not in {"present", "absent"}:
            continue
        expected_bit = 1 if direction == "present" else 0
        contrary_bit = 1 - expected_bit
        used_difficult = any(
            bits[position] == contrary_bit and bits in remainder_rows for bits in expansion
        )
        if used_difficult:
            additions[condition] = bool(expected_bit)
    if not additions:
        return dict(term)

    candidate = {**term, **additions}
    if _covers_positive(candidate, conditions, positive_rows):
        return _ordered(candidate, conditions)
    # Restoring every literal can empty the term when the covered positive rows
    # all sit on the contrary side. Restore only those that keep the term grounded.
    grounded = dict(term)
    for condition, value in additions.items():
        trial = {**grounded, condition: value}
        if _covers_positive(trial, conditions, positive_rows):
            grounded = trial
    return _ordered(grounded, conditions)


def _expansion(term: dict[str, bool], conditions: list[str]) -> Iterator[tuple[int, ...]]:
    """Yield every truth-table row consistent with a conjunction."""
    free = [condition for condition in conditions if condition not in term]
    fixed = {
        conditions.index(condition): int(value) for condition, value in term.items()
    }
    for combination in product([0, 1], repeat=len(free)):
        bits = [0] * len(conditions)
        for index, value in fixed.items():
            bits[index] = value
        for condition, value in zip(free, combination, strict=True):
            bits[conditions.index(condition)] = value
        yield tuple(bits)


def _covers_positive(
    term: dict[str, bool],
    conditions: list[str],
    positive_rows: set[tuple[int, ...]],
) -> bool:
    return any(bits in positive_rows for bits in _expansion(term, conditions))


def _drop_redundant_terms(
    derived: list[tuple[dict[str, bool], dict[str, bool]]],
) -> list[tuple[dict[str, bool], dict[str, bool]]]:
    """Remove duplicated terms and terms subsumed by a simpler term."""
    unique: list[tuple[dict[str, bool], dict[str, bool]]] = []
    seen: set[frozenset[tuple[str, bool]]] = set()
    for term, origin in derived:
        key = frozenset(term.items())
        if key not in seen:
            seen.add(key)
            unique.append((term, origin))
    kept: list[tuple[dict[str, bool], dict[str, bool]]] = []
    for term, origin in unique:
        literals = frozenset(term.items())
        subsumed = any(
            frozenset(other.items()) < literals for other, _ in unique if other is not term
        )
        if not subsumed:
            kept.append((term, origin))
    return kept


def _ordered(term: dict[str, bool], conditions: list[str]) -> dict[str, bool]:
    return {condition: term[condition] for condition in conditions if condition in term}
