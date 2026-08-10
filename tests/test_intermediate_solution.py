from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.minimize import (
    core_peripheral_table,
    intermediate_solution,
    minimize_truth_table,
    solution_terms,
)


def _table(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _abc_table() -> pd.DataFrame:
    # A*B*C is positive. A*B*~C is unobserved, so the parsimonious solution
    # simplifies to A*B by assuming the outcome occurs without C.
    rows: list[dict[str, object]] = []
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                positive = a == 1 and b == 1 and c == 1
                observed = not (a == 1 and b == 1 and c == 0)
                rows.append(
                    {"A": a, "B": b, "C": c, "observed": observed, "positive": positive}
                )
    return _table(rows)


def test_intermediate_keeps_literal_when_removal_needs_a_difficult_counterfactual() -> None:
    table = _abc_table()

    conservative = minimize_truth_table(table, conditions=["A", "B", "C"], kind="conservative")
    parsimonious = minimize_truth_table(table, conditions=["A", "B", "C"], kind="parsimonious")
    intermediate = intermediate_solution(
        table,
        conditions=["A", "B", "C"],
        directional_expectations={"A": "present", "B": "present", "C": "present"},
    )

    assert conservative.expression == "A*B*C"
    assert parsimonious.expression == "A*B"
    # Dropping C would assume the outcome occurs without a condition expected
    # to contribute, which is a difficult counterfactual, so C is restored.
    assert intermediate.expression == "A*B*C"


def test_intermediate_drops_literal_when_the_counterfactual_is_easy() -> None:
    table = _abc_table()

    intermediate = intermediate_solution(
        table,
        conditions=["A", "B", "C"],
        directional_expectations={"A": "present", "B": "present", "C": "absent"},
    )

    # The counterfactual A*B*~C now agrees with the expectation for C, so its
    # use is easy and the intermediate solution matches the parsimonious one.
    assert intermediate.expression == "A*B"


def test_intermediate_ignores_conditions_without_an_expectation() -> None:
    table = _abc_table()

    intermediate = intermediate_solution(
        table,
        conditions=["A", "B", "C"],
        directional_expectations={"A": "present", "B": "present", "C": "either"},
    )

    assert intermediate.expression == "A*B"


def test_intermediate_lies_between_parsimonious_and_conservative() -> None:
    table = _abc_table()
    conditions = ["A", "B", "C"]
    expectations = {"A": "present", "B": "present", "C": "present"}

    parsimonious = solution_terms(
        minimize_truth_table(table, conditions=conditions, kind="parsimonious"), conditions
    )
    conservative = solution_terms(
        minimize_truth_table(table, conditions=conditions, kind="conservative"), conditions
    )
    intermediate = solution_terms(
        minimize_truth_table(
            table,
            conditions=conditions,
            kind="intermediate",
            directional_expectations=expectations,
        ),
        conditions,
    )

    for term in intermediate:
        literals = set(term.items())
        assert any(set(simple.items()) <= literals for simple in parsimonious)
        assert any(literals <= set(complex_term.items()) for complex_term in conservative)


def test_core_peripheral_classification_marks_parsimonious_literals_as_core() -> None:
    table = _abc_table()
    solution = minimize_truth_table(
        table,
        conditions=["A", "B", "C"],
        kind="intermediate",
        directional_expectations={"A": "present", "B": "present", "C": "present"},
    )

    roles = core_peripheral_table(solution, ["A", "B", "C"])

    lookup = dict(zip(roles["condition"], roles["role"], strict=True))
    assert lookup["A"] == "core"
    assert lookup["B"] == "core"
    assert lookup["C"] == "peripheral"


def test_intermediate_returns_empty_solution_without_positive_rows() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": True, "positive": False},
            {"A": 1, "B": 1, "observed": True, "positive": False},
        ]
    )

    solution = minimize_truth_table(
        table,
        conditions=["A", "B"],
        kind="intermediate",
        directional_expectations={"A": "present", "B": "present"},
    )

    assert solution.expression == "0"
