"""End-to-end reproducible analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sympy as sp

from euro_fsqca.analysis.complementarity import condition_pair_matrix
from euro_fsqca.analysis.portability import (
    country_portability,
    directed_portability,
    evaluate_portability,
)
from euro_fsqca.analysis.regression import fit_fractional_logit
from euro_fsqca.analysis.robustness import anchor_sweep, leave_one_group_out, threshold_sweep
from euro_fsqca.config import AnalysisConfig, SetSpec
from euro_fsqca.data.regions import attach_regions, load_region_map
from euro_fsqca.qca.diagnostics import difficult_rows, diversity_diagnostics
from euro_fsqca.qca.fuzzy import fuzzy_and, fuzzy_not, fuzzy_or, sufficiency_fit
from euro_fsqca.qca.minimize import BooleanSolution, minimize_truth_table
from euro_fsqca.qca.necessity import necessity_table
from euro_fsqca.qca.truth_table import (
    TruthTableThresholds,
    build_truth_table,
    contradictory_rows,
    truth_table_diagnostics,
)
from euro_fsqca.sets.calibration import direct_calibrate
from euro_fsqca.sets.composites import build_composite


def calibrate_frame(frame: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    """Construct and calibrate all configured conditions and the outcome."""
    calibrated = frame[[config.case_id, config.country_column]].copy()
    specs: dict[str, SetSpec] = {**config.conditions, **config.outcome}
    for name, spec in specs.items():
        if spec.source is not None:
            if spec.source not in frame.columns:
                raise KeyError(f"missing source column for {name}: {spec.source}")
            raw = pd.to_numeric(frame[spec.source], errors="coerce")
        else:
            assert spec.composite is not None
            raw = build_composite(frame, spec.composite)
        calibrated[name] = direct_calibrate(raw, spec.anchors)
    return calibrated


def _thresholds(config: AnalysisConfig) -> TruthTableThresholds:
    return TruthTableThresholds(
        frequency=config.truth_table.frequency_cutoff,
        consistency=config.truth_table.consistency_cutoff,
        pri=config.truth_table.pri_cutoff,
    )


def _terms_from_solution(solution: BooleanSolution, conditions: list[str]) -> list[dict[str, bool]]:
    """Extract conjunctions from a SymPy DNF solution."""
    expression = sp.to_dnf(solution.sympy_expression, simplify=True)
    if expression is sp.false:
        return []
    disjuncts = expression.args if isinstance(expression, sp.Or) else (expression,)
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



def _membership_from_sympy(frame: pd.DataFrame, expression: sp.logic.boolalg.Boolean) -> np.ndarray:
    """Evaluate a Boolean solution over fuzzy memberships."""
    if expression is sp.true:
        return np.ones(len(frame), dtype=float)
    if expression is sp.false:
        return np.zeros(len(frame), dtype=float)
    if isinstance(expression, sp.Symbol):
        return frame[str(expression)].to_numpy(dtype=float)
    if isinstance(expression, sp.Not):
        return fuzzy_not(_membership_from_sympy(frame, expression.args[0]))
    if isinstance(expression, sp.And):
        return fuzzy_and(*[_membership_from_sympy(frame, arg) for arg in expression.args])
    if isinstance(expression, sp.Or):
        return fuzzy_or(*[_membership_from_sympy(frame, arg) for arg in expression.args])
    raise TypeError(f"unsupported Boolean expression: {type(expression)!r}")


def _run_group(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    outcome: str,
    label: str,
    output_dir: Path,
) -> dict[str, Any]:
    conditions = list(config.conditions)
    group_dir = output_dir / label
    group_dir.mkdir(parents=True, exist_ok=True)
    thresholds = _thresholds(config)

    necessity = necessity_table(frame, conditions=conditions, outcome=outcome)
    truth = build_truth_table(
        frame,
        conditions=conditions,
        outcome=outcome,
        thresholds=thresholds,
    )
    conservative = minimize_truth_table(truth, conditions=conditions, kind="conservative")
    parsimonious = minimize_truth_table(truth, conditions=conditions, kind="parsimonious")

    necessity.to_csv(group_dir / "necessity.csv", index=False)
    truth.to_csv(group_dir / "truth_table.csv", index=False)
    truth_table_diagnostics(truth, thresholds=thresholds).to_csv(
        group_dir / "truth_table_diagnostics.csv",
        index=False,
    )
    contradictory_rows(truth, thresholds=thresholds).to_csv(
        group_dir / "contradictory_rows.csv",
        index=False,
    )
    diversity_diagnostics(truth, thresholds=thresholds).to_csv(
        group_dir / "diversity_diagnostics.csv",
        index=False,
    )
    difficult_rows(truth, thresholds=thresholds).to_csv(
        group_dir / "difficult_rows.csv",
        index=False,
    )
    solution_rows: list[dict[str, object]] = []
    for solution in (conservative, parsimonious):
        membership = _membership_from_sympy(frame, solution.sympy_expression)
        fit = sufficiency_fit(membership, frame[outcome].to_numpy(dtype=float))
        solution_rows.append(
            {
                "solution": solution.kind,
                "expression": solution.expression,
                "consistency": fit.consistency,
                "coverage": fit.coverage,
                "pri": fit.pri,
            }
        )
    pd.DataFrame(solution_rows).to_csv(group_dir / "solutions.csv", index=False)

    term_rows: list[dict[str, object]] = []
    for solution in (conservative, parsimonious):
        for term_index, literals in enumerate(_terms_from_solution(solution, conditions), start=1):
            # Build each term directly from its fuzzy literals for case-level fit.
            operands = [
                (
                    frame[name].to_numpy(dtype=float)
                    if present
                    else 1.0 - frame[name].to_numpy(dtype=float)
                )
                for name, present in literals.items()
            ]
            membership = fuzzy_and(*operands)
            fit = sufficiency_fit(membership, frame[outcome].to_numpy(dtype=float))
            term_rows.append(
                {
                    "solution": solution.kind,
                    "term": term_index,
                    "configuration": json.dumps(literals, sort_keys=True),
                    "n_relevant_establishments": int((membership > 0.5).sum()),
                    "country_distribution": _distribution_json(frame, "country", membership),
                    "regional_distribution": _distribution_json(frame, "macroregion", membership),
                    "consistency": fit.consistency,
                    "coverage": fit.coverage,
                    "pri": fit.pri,
                }
            )
    pd.DataFrame(term_rows).to_csv(group_dir / "solution_terms.csv", index=False)

    return {
        "label": label,
        "n": len(frame),
        "frequency_cutoff": thresholds.frequency,
        "consistency_cutoff": thresholds.consistency,
        "pri_cutoff": thresholds.pri,
        "conservative": conservative.expression,
        "parsimonious": parsimonious.expression,
        "n_positive_rows": int(truth["positive"].sum()),
        "conservative_object": conservative,
    }


def run_analysis(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    config_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run pan-European, regional, asymmetric, robustness and regression analyses."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    calibrated = calibrate_frame(frame, config)
    regions_path = Path(config.regions_file)
    if not regions_path.is_absolute():
        regions_path = Path(config_path).resolve().parent.parent / regions_path
    mapping = load_region_map(regions_path, config.primary_region_scheme)
    calibrated = attach_regions(
        calibrated,
        country_column=config.country_column,
        mapping=mapping,
    )
    calibrated.to_csv(target / "calibrated_memberships.csv", index=False)

    outcome = config.outcome_name
    conditions = list(config.conditions)
    qca_specification = {
        "conditions": conditions,
        "outcome": outcome,
        "frequency_cutoff": config.truth_table.frequency_cutoff,
        "consistency_cutoff": config.truth_table.consistency_cutoff,
        "pri_cutoff": config.truth_table.pri_cutoff,
        "logical_remainder_policy": {
            "conservative": "observed positive rows only",
            "parsimonious": "unobserved rows treated as logical remainders",
        },
        "calibration_scope": "common Europe-wide anchors",
    }
    with (target / "qca_specification.json").open("w", encoding="utf-8") as stream:
        json.dump(qca_specification, stream, indent=2)
    summaries: list[dict[str, Any]] = []
    directed_configurations: dict[str, list[dict[str, bool]]] = {}
    europe = _run_group(
        calibrated, config=config, outcome=outcome, label="europe", output_dir=target
    )
    summaries.append({key: value for key, value in europe.items() if key != "conservative_object"})

    for region, group in calibrated.groupby("macroregion", observed=True):
        result = _run_group(
            group,
            config=config,
            outcome=outcome,
            label=f"region_{str(region).lower()}",
            output_dir=target,
        )
        summaries.append(
            {key: value for key, value in result.items() if key != "conservative_object"}
        )
        region_terms = _terms_from_solution(result["conservative_object"], conditions)
        if region_terms:
            directed_configurations[str(region)] = region_terms
    pd.DataFrame(_regional_comparison_rows(summaries)).to_csv(
        target / "regional_comparison.csv",
        index=False,
    )

    # Causal asymmetry: repeat the full analysis for the negated outcome.
    negative = calibrated.copy()
    negative[f"NOT_{outcome}"] = 1.0 - negative[outcome]
    neg_outcome = f"NOT_{outcome}"
    negative_result = _run_group(
        negative,
        config=config,
        outcome=neg_outcome,
        label="europe_negative_outcome",
        output_dir=target,
    )

    # Portability of each pan-European conservative term across the same regional calibration.
    portability_rows: list[pd.DataFrame] = []
    terms = _terms_from_solution(europe["conservative_object"], conditions)
    country_configurations: dict[str, list[dict[str, bool]]] = {"europe": terms}
    for index, literals in enumerate(terms, start=1):
        summary = evaluate_portability(
            calibrated,
            literals=literals,
            outcome=outcome,
            region_column="macroregion",
        )
        term_table = summary.table.copy()
        term_table.insert(0, "term", index)
        term_table.insert(1, "configuration", json.dumps(literals, sort_keys=True))
        term_table["consistency_sd"] = summary.consistency_sd
        term_table["consistency_range"] = summary.consistency_range
        portability_rows.append(term_table)
    portability = (
        pd.concat(portability_rows, ignore_index=True)
        if portability_rows
        else pd.DataFrame(
            columns=[
                "term",
                "configuration",
                "region",
                "n",
                "consistency",
                "coverage",
                "pri",
                "consistency_sd",
                "consistency_range",
            ]
        )
    )
    portability.to_csv(target / "portability.csv", index=False)
    complementarity_configurations: dict[str, list[dict[str, bool]]] = {"europe": terms}
    directed_table, directed_matrix, directed_network = directed_portability(
        calibrated,
        configurations=directed_configurations,
        outcome=outcome,
        region_column="macroregion",
    )
    directed_table.to_csv(target / "portability_directed.csv", index=False)
    directed_matrix.to_csv(target / "portability_matrix.csv", index=False)
    directed_network.to_csv(target / "portability_network.csv", index=False)
    country_configurations.update(directed_configurations)
    complementarity_configurations.update(directed_configurations)
    condition_pair_matrix(complementarity_configurations).to_csv(
        target / "complementarity_pairs.csv",
        index=False,
    )
    country_portability(
        calibrated,
        configurations=country_configurations,
        outcome=outcome,
        country_column=config.country_column,
    ).to_csv(target / "country_portability.csv", index=False)

    # Threshold sensitivity on the European sample.
    if config.robustness.enabled:
        threshold_sweep(calibrated, config=config, outcome=outcome).to_csv(
            target / "threshold_sensitivity.csv", index=False
        )
        anchor_sweep(frame, config=config, calibrator=calibrate_frame).to_csv(
            target / "anchor_sensitivity.csv", index=False
        )
        leave_one_group_out(
            calibrated,
            config=config,
            outcome=outcome,
            group_column=config.country_column,
        ).to_csv(target / "leave_one_country_out.csv", index=False)
        for optional_group in ["sector", "size_class"]:
            if optional_group in calibrated.columns:
                leave_one_group_out(
                    calibrated,
                    config=config,
                    outcome=outcome,
                    group_column=optional_group,
                ).to_csv(target / f"leave_one_{optional_group}_out.csv", index=False)

    # Net-effect comparison. Fuzzy outcomes are modeled with a fractional logit.
    regression = fit_fractional_logit(calibrated, outcome=outcome, conditions=conditions)
    coefficients = pd.DataFrame(
        {
            "term": regression.params.index,
            "estimate": regression.params.values,
            "std_error": regression.bse.values,
            "p_value": regression.pvalues.values,
            "ci_lower": regression.conf_int()[0].values,
            "ci_upper": regression.conf_int()[1].values,
        }
    )
    coefficients.to_csv(target / "fractional_logit.csv", index=False)

    summary_payload: dict[str, Any] = {
        "groups": summaries,
        "negative_outcome": {
            key: value for key, value in negative_result.items() if key != "conservative_object"
        },
        "n_complete_calibrated": int(calibrated[[*conditions, outcome]].dropna().shape[0]),
        "regions": calibrated["macroregion"].value_counts().to_dict(),
    }
    with (target / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary_payload, stream, indent=2, default=str)
    return summary_payload


def _distribution_json(frame: pd.DataFrame, column: str, membership: np.ndarray) -> str:
    if column not in frame.columns:
        return "{}"
    relevant = pd.Series(membership > 0.5, index=frame.index)
    counts = frame.loc[relevant, column].value_counts(dropna=False).to_dict()
    return json.dumps({str(key): int(value) for key, value in counts.items()}, sort_keys=True)


def _regional_comparison_rows(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    europe = next((summary for summary in summaries if summary["label"] == "europe"), None)
    if europe is None:
        return []
    total_n = int(europe["n"])
    rows: list[dict[str, Any]] = []
    for summary in summaries:
        if summary["label"] == "europe":
            continue
        n_cases = int(summary["n"])
        rows.append(
            {
                "region": str(summary["label"]).removeprefix("region_"),
                "n_cases": n_cases,
                "relative_prevalence": n_cases / total_n if total_n else 0.0,
                "frequency_cutoff": summary["frequency_cutoff"],
                "consistency_cutoff": summary["consistency_cutoff"],
                "pri_cutoff": summary["pri_cutoff"],
                "conservative_solution": summary["conservative"],
                "parsimonious_solution": summary["parsimonious"],
                "n_positive_rows": summary["n_positive_rows"],
                "conservative_matches_europe": summary["conservative"] == europe["conservative"],
                "parsimonious_matches_europe": summary["parsimonious"] == europe["parsimonious"],
            }
        )
    return rows
