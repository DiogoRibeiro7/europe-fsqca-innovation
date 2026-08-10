"""Threshold, calibration, sampling and estimand sensitivity analysis."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from itertools import product

import numpy as np
import pandas as pd

from euro_fsqca.config import AnalysisConfig
from euro_fsqca.qca.minimize import minimize_truth_table
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table, contradictory_rows
from euro_fsqca.survey import WeightScheme, resolve_weights


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


def solution_term_set(expression: str) -> set[str]:
    """Return the set of conjunctive terms in a QCA expression."""
    if expression in {"", "0", "1"}:
        return set()
    terms: set[str] = set()
    for term in expression.split("+"):
        literals = sorted(literal.strip() for literal in term.split("*") if literal.strip())
        if literals:
            terms.add("*".join(literals))
    return terms


def term_jaccard(left: str, right: str) -> float:
    """Compare two solutions by their configuration terms rather than literals.

    Two solutions can draw on an identical pool of literals while proposing
    different recipes, so literal-level similarity alone overstates agreement.
    """
    left_terms = solution_term_set(left)
    right_terms = solution_term_set(right)
    union = left_terms | right_terms
    if not union:
        return 1.0
    return len(left_terms & right_terms) / len(union)


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


def _weights_of(frame: pd.DataFrame, weight_column: str | None) -> pd.Series | None:
    if weight_column is None or weight_column not in frame.columns:
        return None
    return frame[weight_column].astype(float)


def _solve(
    frame: pd.DataFrame,
    *,
    conditions: list[str],
    outcome: str,
    thresholds: TruthTableThresholds,
    weight_column: str | None,
    kinds: tuple[str, ...] = ("conservative",),
    directional_expectations: Mapping[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Build a truth table and minimise it for the requested solution kinds."""
    table = build_truth_table(
        frame,
        conditions=conditions,
        outcome=outcome,
        thresholds=thresholds,
        weights=_weights_of(frame, weight_column),
    )
    solutions = {
        kind: minimize_truth_table(
            table,
            conditions=conditions,
            kind=kind,
            directional_expectations=directional_expectations,
        ).expression
        for kind in kinds
    }
    return table, solutions


def threshold_sweep(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    conditions: list[str] | None = None,
    weight_column: str | None = None,
) -> pd.DataFrame:
    """Sweep truth-table thresholds and record solution stability."""
    condition_names = conditions or list(config.conditions)
    rows: list[dict[str, object]] = []
    _, main = _solve(
        calibrated,
        conditions=condition_names,
        outcome=outcome,
        thresholds=config.truth_table.thresholds(),
        weight_column=weight_column,
    )
    main_conservative = main["conservative"]
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
            frequency_basis="cases",
        )
        table, solutions = _solve(
            calibrated,
            conditions=condition_names,
            outcome=outcome,
            thresholds=thresholds,
            weight_column=weight_column,
            kinds=("conservative", "parsimonious"),
        )
        rows.append(
            {
                "consistency_cutoff": consistency,
                "pri_cutoff": pri,
                "frequency_cutoff": frequency,
                "frequency_basis": thresholds.frequency_basis,
                "n_rows_retained": int(
                    (table["frequency_evidence"].astype(float) >= frequency).sum()
                ),
                "n_positive_rows": int(table["positive"].sum()),
                "n_contradictory_rows": len(contradictory_rows(table, thresholds=thresholds)),
                "n_conservative_terms": _term_count(solutions["conservative"]),
                "n_parsimonious_terms": _term_count(solutions["parsimonious"]),
                "conservative_solution": solutions["conservative"],
                "parsimonious_solution": solutions["parsimonious"],
                "conservative_similarity": signed_literal_jaccard(
                    main_conservative, solutions["conservative"]
                ),
                "conservative_term_similarity": term_jaccard(
                    main_conservative, solutions["conservative"]
                ),
                "conservative_change": classify_solution_change(
                    main_conservative, solutions["conservative"]
                ),
            }
        )
    return _with_shares(pd.DataFrame(rows))


def estimand_sweep(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    conditions: list[str] | None = None,
    estimands: list[WeightScheme] | None = None,
) -> pd.DataFrame:
    """Compare solutions under unweighted and survey-weighted estimands.

    The three estimands answer different questions. Unweighted QCA is a
    statement about the sampled establishments, firm-population weighting is a
    statement about the establishment population, and equal-country weighting
    prevents the largest member states from determining a pooled European
    solution. Disagreement between them is a finding, not a nuisance.
    """
    condition_names = conditions or list(config.conditions)
    schemes = estimands or config.survey.estimands
    thresholds = config.truth_table.thresholds()
    rows: list[dict[str, object]] = []
    reference = ""
    for index, scheme in enumerate(schemes):
        weights = resolve_weights(
            calibrated,
            scheme=scheme,
            weight_column=config.survey.weight_column,
            country_column=config.country_column,
        )
        working = calibrated.copy()
        working["_estimand_weight"] = weights
        table, solutions = _solve(
            working,
            conditions=condition_names,
            outcome=outcome,
            thresholds=thresholds,
            weight_column="_estimand_weight",
            kinds=("conservative", "parsimonious"),
        )
        if index == 0:
            reference = solutions["conservative"]
        rows.append(
            {
                "estimand": scheme,
                "n": len(working),
                "sum_weight": float(weights.sum()),
                "n_positive_rows": int(table["positive"].sum()),
                "conservative_solution": solutions["conservative"],
                "parsimonious_solution": solutions["parsimonious"],
                "conservative_similarity": signed_literal_jaccard(
                    reference, solutions["conservative"]
                ),
                "conservative_term_similarity": term_jaccard(
                    reference, solutions["conservative"]
                ),
                "conservative_change": classify_solution_change(
                    reference, solutions["conservative"]
                ),
            }
        )
    return pd.DataFrame(rows)


def region_scheme_comparison(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    schemes: dict[str, dict[str, str]],
    conditions: list[str] | None = None,
    weight_column: str | None = None,
    min_cases: int = 30,
) -> pd.DataFrame:
    """Re-derive regional solutions under alternative regional taxonomies."""
    condition_names = conditions or list(config.conditions)
    thresholds = config.truth_table.thresholds()
    rows: list[dict[str, object]] = []
    for scheme_name, mapping in schemes.items():
        labels = calibrated[config.country_column].astype(str).str.strip().map(mapping)
        for region in sorted(labels.dropna().unique()):
            group = calibrated.loc[labels == region]
            if len(group) < min_cases:
                rows.append(
                    {
                        "scheme": scheme_name,
                        "region": str(region),
                        "n": len(group),
                        "skipped": True,
                        "conservative_solution": "",
                        "parsimonious_solution": "",
                        "n_positive_rows": 0,
                    }
                )
                continue
            table, solutions = _solve(
                group,
                conditions=condition_names,
                outcome=outcome,
                thresholds=thresholds,
                weight_column=weight_column,
                kinds=("conservative", "parsimonious"),
            )
            rows.append(
                {
                    "scheme": scheme_name,
                    "region": str(region),
                    "n": len(group),
                    "skipped": False,
                    "conservative_solution": solutions["conservative"],
                    "parsimonious_solution": solutions["parsimonious"],
                    "n_positive_rows": int(table["positive"].sum()),
                }
            )
    return pd.DataFrame(rows)


def _term_count(expression: str) -> int:
    if expression in {"", "0", "1"}:
        return 0
    return len([term for term in expression.split("+") if term.strip()])


def anchor_sweep(
    raw_frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    calibrator: Callable[[pd.DataFrame, AnalysisConfig], pd.DataFrame],
    conditions: list[str] | None = None,
    weight_column: str | None = None,
) -> pd.DataFrame:
    """Re-run Europe-wide solutions after proportional outer-anchor shifts.

    ``calibrator`` is injected to avoid a circular import with the main pipeline;
    it must be callable as ``calibrator(frame, config_variant)``.
    """
    from copy import deepcopy

    from euro_fsqca.sets.calibration import shift_anchors

    condition_names = conditions or list(config.conditions)
    rows: list[dict[str, object]] = []
    main_calibrated = calibrator(raw_frame, config)
    _, main = _solve(
        main_calibrated,
        conditions=condition_names,
        outcome=config.outcome_name,
        thresholds=config.truth_table.thresholds(),
        weight_column=weight_column,
    )
    main_conservative = main["conservative"]
    for shift in config.robustness.anchor_shift_proportions:
        variant = deepcopy(config)
        for spec in [*variant.conditions.values(), *variant.outcome.values()]:
            spec.anchors = shift_anchors(spec.anchors, shift)
        calibrated = calibrator(raw_frame, variant)
        table, solutions = _solve(
            calibrated,
            conditions=condition_names,
            outcome=variant.outcome_name,
            thresholds=variant.truth_table.thresholds(),
            weight_column=weight_column,
            kinds=("conservative", "parsimonious"),
        )
        rows.append(
            {
                "anchor_shift_proportion": shift,
                "n_positive_rows": int(table["positive"].sum()),
                "conservative_solution": solutions["conservative"],
                "parsimonious_solution": solutions["parsimonious"],
                "conservative_similarity": signed_literal_jaccard(
                    main_conservative, solutions["conservative"]
                ),
                "conservative_term_similarity": term_jaccard(
                    main_conservative, solutions["conservative"]
                ),
                "conservative_change": classify_solution_change(
                    main_conservative, solutions["conservative"]
                ),
            }
        )
    return _with_shares(pd.DataFrame(rows))


def leave_one_group_out(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    group_column: str,
    conditions: list[str] | None = None,
    weight_column: str | None = None,
    min_remaining_cases: int = 30,
) -> pd.DataFrame:
    """Run Europe-wide QCA after removing each group in a column."""
    columns = [
        "group_column",
        "removed_group",
        "n_removed",
        "n_remaining",
        "skipped",
        "reason",
        "conservative_solution",
        "conservative_similarity",
        "conservative_change",
    ]
    if group_column not in calibrated.columns:
        return pd.DataFrame(columns=columns)
    condition_names = conditions or list(config.conditions)
    thresholds = config.truth_table.thresholds()
    _, main = _solve(
        calibrated,
        conditions=condition_names,
        outcome=outcome,
        thresholds=thresholds,
        weight_column=weight_column,
    )
    main_solution = main["conservative"]
    rows: list[dict[str, object]] = []
    for group in sorted(calibrated[group_column].dropna().astype(str).unique()):
        mask = calibrated[group_column].astype(str) == group
        subset = calibrated.loc[~mask].copy()
        if len(subset) < min_remaining_cases:
            rows.append(
                {
                    "group_column": group_column,
                    "removed_group": group,
                    "n_removed": int(mask.sum()),
                    "n_remaining": len(subset),
                    "skipped": True,
                    "reason": "remaining sample below minimum",
                    "conservative_solution": "",
                    "conservative_similarity": float("nan"),
                    "conservative_change": "unavailable",
                }
            )
            continue
        _, solutions = _solve(
            subset,
            conditions=condition_names,
            outcome=outcome,
            thresholds=thresholds,
            weight_column=weight_column,
        )
        rows.append(
            {
                "group_column": group_column,
                "removed_group": group,
                "n_removed": int(mask.sum()),
                "n_remaining": len(subset),
                "skipped": False,
                "reason": "",
                "conservative_solution": solutions["conservative"],
                "conservative_similarity": signed_literal_jaccard(
                    main_solution, solutions["conservative"]
                ),
                "conservative_term_similarity": term_jaccard(
                    main_solution, solutions["conservative"]
                ),
                "conservative_change": classify_solution_change(
                    main_solution, solutions["conservative"]
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def bootstrap_qca(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    n_bootstrap: int,
    seed: int = 42,
    n_jobs: int = 1,
    conditions: list[str] | None = None,
    weight_column: str | None = None,
    strata_column: str | None = None,
) -> pd.DataFrame:
    """Bootstrap calibrated cases and record QCA solution stability.

    When ``strata_column`` is supplied the resampling is stratified, which
    reproduces the sampling design instead of treating the pooled sample as a
    simple random draw.
    """
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be at least 1")
    condition_names = conditions or list(config.conditions)
    seeds = np.random.default_rng(seed).integers(0, 2**32 - 1, size=n_bootstrap).tolist()

    def run(index: int, item: int) -> dict[str, object]:
        return _bootstrap_once(
            calibrated,
            config=config,
            outcome=outcome,
            seed=int(item),
            index=index,
            conditions=condition_names,
            weight_column=weight_column,
            strata_column=strata_column,
        )

    if n_jobs <= 1:
        rows = [run(index, item) for index, item in enumerate(seeds, start=1)]
    else:
        with ThreadPoolExecutor(max_workers=n_jobs) as executor:
            rows = list(
                executor.map(
                    lambda args: run(int(args[0]), int(args[1])),
                    enumerate(seeds, start=1),
                )
            )
    return pd.DataFrame(rows)


def bootstrap_stability(bootstrap: pd.DataFrame) -> pd.DataFrame:
    """Summarise configuration appearance frequencies across bootstrap samples."""
    successes = bootstrap[bootstrap["status"] == "PASS"]
    if successes.empty:
        return pd.DataFrame(columns=["conservative_solution", "n", "appearance_frequency"])
    counts = successes["conservative_solution"].value_counts().reset_index()
    counts.columns = ["conservative_solution", "n"]
    counts["appearance_frequency"] = counts["n"] / len(bootstrap)
    return counts


def bootstrap_term_stability(bootstrap: pd.DataFrame) -> pd.DataFrame:
    """Summarise how often each individual configuration term survives resampling."""
    successes = bootstrap[bootstrap["status"] == "PASS"]
    if successes.empty:
        return pd.DataFrame(columns=["configuration", "n", "appearance_frequency"])
    rows: list[str] = []
    for expression in successes["conservative_solution"]:
        if expression in {"", "0", "1"}:
            continue
        rows.extend(term.strip() for term in str(expression).split("+") if term.strip())
    if not rows:
        return pd.DataFrame(columns=["configuration", "n", "appearance_frequency"])
    counts = pd.Series(rows).value_counts().reset_index()
    counts.columns = ["configuration", "n"]
    counts["appearance_frequency"] = counts["n"] / len(bootstrap)
    return counts


def _stratified_sample(
    frame: pd.DataFrame,
    *,
    strata_column: str | None,
    seed: int,
) -> pd.DataFrame:
    if strata_column is None or strata_column not in frame.columns:
        return frame.sample(n=len(frame), replace=True, random_state=seed)
    parts = [
        group.sample(n=len(group), replace=True, random_state=seed + position)
        for position, (_, group) in enumerate(
            frame.groupby(strata_column, dropna=False, observed=True)
        )
    ]
    return pd.concat(parts)


def _bootstrap_once(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    seed: int,
    index: int,
    conditions: list[str],
    weight_column: str | None,
    strata_column: str | None,
) -> dict[str, object]:
    try:
        sample = _stratified_sample(calibrated, strata_column=strata_column, seed=seed)
        table, solutions = _solve(
            sample,
            conditions=conditions,
            outcome=outcome,
            thresholds=config.truth_table.thresholds(),
            weight_column=weight_column,
        )
        return {
            "bootstrap": index,
            "seed": seed,
            "status": "PASS",
            "failure_reason": "",
            "n": len(sample),
            "n_positive_rows": int(table["positive"].sum()),
            "conservative_solution": solutions["conservative"],
            "n_conservative_terms": _term_count(solutions["conservative"]),
        }
    except Exception as exc:  # pragma: no cover - exercised by malformed external data
        return {
            "bootstrap": index,
            "seed": seed,
            "status": "FAIL",
            "failure_reason": str(exc),
            "n": 0,
            "n_positive_rows": 0,
            "conservative_solution": "",
            "n_conservative_terms": 0,
        }


def _with_shares(result: pd.DataFrame) -> pd.DataFrame:
    if result.empty:
        return result
    for kind in ("conservative", "parsimonious"):
        column = f"{kind}_solution"
        if column in result.columns:
            result[f"{kind}_share"] = result.groupby(column)[column].transform("size") / len(
                result
            )
    return result
