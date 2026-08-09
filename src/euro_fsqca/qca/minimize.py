"""Transparent Boolean minimisation for truth-table solutions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import sympy as sp


@dataclass(frozen=True)
class BooleanSolution:
    """Conservative or parsimonious Boolean solution."""

    kind: str
    expression: str
    sympy_expression: sp.logic.boolalg.Boolean


def _minterm(row: pd.Series, conditions: list[str]) -> list[int]:
    return [int(row[condition]) for condition in conditions]


def _format_expression(expression: sp.logic.boolalg.Boolean, conditions: list[str]) -> str:
    """Convert a SymPy DNF expression to conventional QCA notation."""
    symbol_map = {str(sp.Symbol(condition)): condition for condition in conditions}
    if expression is sp.true:
        return "1"
    if expression is sp.false:
        return "0"

    def render(node: sp.logic.boolalg.Boolean) -> str:
        if isinstance(node, sp.Symbol):
            return symbol_map[str(node)]
        if isinstance(node, sp.Not):
            return f"~{render(node.args[0])}"
        if isinstance(node, sp.And):
            return "*".join(render(arg) for arg in node.args)
        if isinstance(node, sp.Or):
            return " + ".join(render(arg) for arg in node.args)
        return str(node)

    return render(expression)


def minimize_truth_table(
    truth_table: pd.DataFrame,
    *,
    conditions: list[str],
    kind: str = "conservative",
) -> BooleanSolution:
    """Minimise positive truth-table rows using exact SOP minimisation.

    ``conservative`` uses no logical remainders. ``parsimonious`` treats
    unobserved rows as don't-cares while preserving observed negative rows.
    Intermediate solutions are delegated to the optional R/QCA cross-check.
    """
    if kind not in {"conservative", "parsimonious"}:
        raise ValueError("kind must be conservative or parsimonious")
    symbols = [sp.Symbol(condition) for condition in conditions]
    positives = [
        _minterm(row, conditions)
        for _, row in truth_table[truth_table["positive"]].iterrows()
    ]
    if not positives:
        return BooleanSolution(kind=kind, expression="0", sympy_expression=sp.false)

    dontcares: list[list[int]] = []
    if kind == "parsimonious":
        dontcares = [
            _minterm(row, conditions)
            for _, row in truth_table[~truth_table["observed"]].iterrows()
        ]

    expression = sp.SOPform(symbols, positives, dontcares=dontcares)
    return BooleanSolution(
        kind=kind,
        expression=_format_expression(expression, conditions),
        sympy_expression=expression,
    )
