from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.minimize import minimize_truth_table


def _table(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_minimization_handles_single_implicant() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": True, "positive": False},
            {"A": 0, "B": 1, "observed": True, "positive": False},
            {"A": 1, "B": 0, "observed": True, "positive": True},
            {"A": 1, "B": 1, "observed": True, "positive": True},
        ]
    )

    solution = minimize_truth_table(table, conditions=["A", "B"], kind="conservative")

    assert solution.expression == "A"


def test_minimization_handles_multiple_implicants() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": True, "positive": False},
            {"A": 0, "B": 1, "observed": True, "positive": True},
            {"A": 1, "B": 0, "observed": True, "positive": True},
            {"A": 1, "B": 1, "observed": True, "positive": False},
        ]
    )

    solution = minimize_truth_table(table, conditions=["A", "B"], kind="conservative")

    assert solution.expression == "A*~B + ~A*B"


def test_minimization_removes_redundant_literals() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": True, "positive": False},
            {"A": 0, "B": 1, "observed": True, "positive": False},
            {"A": 1, "B": 0, "observed": True, "positive": True},
            {"A": 1, "B": 1, "observed": True, "positive": True},
        ]
    )

    solution = minimize_truth_table(table, conditions=["A", "B"], kind="conservative")

    assert solution.expression != "A*~B + A*B"
    assert solution.expression == "A"


def test_parsimonious_solution_uses_logical_remainders() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": True, "positive": False},
            {"A": 0, "B": 1, "observed": False, "positive": False},
            {"A": 1, "B": 0, "observed": True, "positive": True},
            {"A": 1, "B": 1, "observed": False, "positive": False},
        ]
    )

    conservative = minimize_truth_table(table, conditions=["A", "B"], kind="conservative")
    parsimonious = minimize_truth_table(table, conditions=["A", "B"], kind="parsimonious")

    assert conservative.expression == "A*~B"
    assert parsimonious.expression == "A"


def test_parsimonious_solution_preserves_observed_negative_rows() -> None:
    table = _table(
        [
            {"A": 0, "B": 0, "observed": False, "positive": False},
            {"A": 0, "B": 1, "observed": False, "positive": False},
            {"A": 1, "B": 0, "observed": True, "positive": True},
            {"A": 1, "B": 1, "observed": True, "positive": False},
        ]
    )

    solution = minimize_truth_table(table, conditions=["A", "B"], kind="parsimonious")

    assert solution.expression == "~B"
