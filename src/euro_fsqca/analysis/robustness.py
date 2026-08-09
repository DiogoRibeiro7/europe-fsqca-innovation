"""Threshold and calibration sensitivity analysis."""

from __future__ import annotations

from collections.abc import Callable
from itertools import product

import pandas as pd

from euro_fsqca.config import AnalysisConfig
from euro_fsqca.qca.minimize import minimize_truth_table
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table


def signed_literals(expression: str) -> set[str]:
    """Extract signed literals from a QCA expression string."""
    if expression in {"", "0", "1"}:
        return set()
    literals: set[str] = set()
    for term in expression.split("+"):
        for literal in term.strip().split("*"):
            text = literal.strip()
            if text:
                literals.add(text)
    return literals


def signed_literal_jaccard(left: str, right: str) -> float:
    """Calculate Jaccard similarity between signed-literal sets."""
    left_literals = signed_literals(left)
    right_literals = signed_literals(right)
    union = left_literals | right_literals
    if not union:
        return 1.0
    return len(left_literals & right_literals) / len(union)


def classify_solution_change(reference: str, candidate: str) -> str:
    """Classify the structural relation between two QCA expressions."""
    if reference == candidate:
        return "same_configuration"
    reference_literals = signed_literals(reference)
    candidate_literals = signed_literals(candidate)
    if not reference_literals or not candidate_literals:
        return "unrelated_configuration"
    unsigned_reference = {literal.lstrip("~") for literal in reference_literals}
    unsigned_candidate = {literal.lstrip("~") for literal in candidate_literals}
    if unsigned_reference == unsigned_candidate and reference_literals != candidate_literals:
        return "polarity_change"
    if (
        reference_literals < candidate_literals
        and len(candidate_literals - reference_literals) == 1
    ):
        return "one_added_condition"
    if (
        candidate_literals < reference_literals
        and len(reference_literals - candidate_literals) == 1
    ):
        return "one_removed_condition"
    return "unrelated_configuration"


def threshold_sweep(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
) -> pd.DataFrame:
    """Sweep truth-table thresholds and record solution stability."""
    conditions = list(config.conditions)
    rows: list[dict[str, object]] = []
    grid = product(
        config.robustness.consistency_cutoffs,
        config.robustness.pri_cutoffs,
        config.robustness.frequency_cutoffs,
    )
    for consistency, pri, frequency in grid:
        thresholds = TruthTableThresholds(
            frequency=frequency,
            consistency=consistency,
            pri=pri,
        )
        table = build_truth_table(
            calibrated,
            conditions=conditions,
            outcome=outcome,
            thresholds=thresholds,
        )
        conservative = minimize_truth_table(table, conditions=conditions, kind="conservative")
        parsimonious = minimize_truth_table(table, conditions=conditions, kind="parsimonious")
        rows.append(
            {
                "consistency_cutoff": consistency,
                "pri_cutoff": pri,
                "frequency_cutoff": frequency,
                "n_positive_rows": int(table["positive"].sum()),
                "conservative_solution": conservative.expression,
                "parsimonious_solution": parsimonious.expression,
            }
        )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["conservative_share"] = result.groupby("conservative_solution")[
            "conservative_solution"
        ].transform("size") / len(result)
        result["parsimonious_share"] = result.groupby("parsimonious_solution")[
            "parsimonious_solution"
        ].transform("size") / len(result)
    return result


def anchor_sweep(
    raw_frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    calibrator: Callable[[pd.DataFrame, AnalysisConfig], pd.DataFrame],
) -> pd.DataFrame:
    """Re-run Europe-wide solutions after proportional outer-anchor shifts.

    ``calibrator`` is injected to avoid a circular import with the main pipeline;
    it must be callable as ``calibrator(frame, config_variant)``.
    """
    from copy import deepcopy

    from euro_fsqca.sets.calibration import shift_anchors

    rows: list[dict[str, object]] = []
    main_calibrated = calibrator(raw_frame, config)
    main_outcome = config.outcome_name
    main_thresholds = TruthTableThresholds(
        frequency=config.truth_table.frequency_cutoff,
        consistency=config.truth_table.consistency_cutoff,
        pri=config.truth_table.pri_cutoff,
    )
    main_table = build_truth_table(
        main_calibrated,
        conditions=list(config.conditions),
        outcome=main_outcome,
        thresholds=main_thresholds,
    )
    main_conservative = minimize_truth_table(
        main_table,
        conditions=list(config.conditions),
        kind="conservative",
    )
    for shift in config.robustness.anchor_shift_proportions:
        variant = deepcopy(config)
        for spec in [*variant.conditions.values(), *variant.outcome.values()]:
            spec.anchors = shift_anchors(spec.anchors, shift)
        calibrated = calibrator(raw_frame, variant)
        outcome = variant.outcome_name
        thresholds = TruthTableThresholds(
            frequency=variant.truth_table.frequency_cutoff,
            consistency=variant.truth_table.consistency_cutoff,
            pri=variant.truth_table.pri_cutoff,
        )
        table = build_truth_table(
            calibrated,
            conditions=list(variant.conditions),
            outcome=outcome,
            thresholds=thresholds,
        )
        conservative = minimize_truth_table(
            table,
            conditions=list(variant.conditions),
            kind="conservative",
        )
        parsimonious = minimize_truth_table(
            table,
            conditions=list(variant.conditions),
            kind="parsimonious",
        )
        rows.append(
            {
                "anchor_shift_proportion": shift,
                "n_positive_rows": int(table["positive"].sum()),
                "conservative_solution": conservative.expression,
                "parsimonious_solution": parsimonious.expression,
                "conservative_similarity": signed_literal_jaccard(
                    main_conservative.expression,
                    conservative.expression,
                ),
                "conservative_change": classify_solution_change(
                    main_conservative.expression,
                    conservative.expression,
                ),
            }
        )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["conservative_share"] = result.groupby("conservative_solution")[
            "conservative_solution"
        ].transform("size") / len(result)
        result["parsimonious_share"] = result.groupby("parsimonious_solution")[
            "parsimonious_solution"
        ].transform("size") / len(result)
    return result
