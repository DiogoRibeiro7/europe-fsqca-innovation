"""End-to-end reproducible analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sympy as sp

from euro_fsqca.analysis.conjunctural import (
    condition_cooccurrence,
    conjunctural_dependence,
    term_substitutability,
)
from euro_fsqca.analysis.portability import (
    PortabilityThresholds,
    bootstrap_directed_portability,
    country_portability,
    directed_portability,
    evaluate_portability,
)
from euro_fsqca.analysis.robustness import (
    anchor_sweep,
    bootstrap_qca,
    bootstrap_stability,
    bootstrap_term_stability,
    classify_solution_change,
    estimand_sweep,
    leave_one_group_out,
    region_scheme_comparison,
    signed_literal_jaccard,
    threshold_sweep,
)
from euro_fsqca.analysis.samples import assign_period, select_sample, timing_summary
from euro_fsqca.config import AnalysisConfig, SampleSpec, SetSpec
from euro_fsqca.data.regions import attach_regions, load_region_map
from euro_fsqca.qca.diagnostics import difficult_rows, diversity_diagnostics
from euro_fsqca.qca.fuzzy import fuzzy_and, fuzzy_not, fuzzy_or, sufficiency_fit
from euro_fsqca.qca.minimize import (
    core_peripheral_table,
    format_literals,
    minimize_truth_table,
    solution_terms,
)
from euro_fsqca.qca.necessity import necessity_table
from euro_fsqca.qca.truth_table import (
    TruthTableThresholds,
    build_truth_table,
    contradictory_rows,
    truth_table_diagnostics,
)
from euro_fsqca.sets.calibration import direct_calibrate
from euro_fsqca.sets.composites import build_composite
from euro_fsqca.survey import (
    ANALYSIS_WEIGHT_COLUMN,
    WeightScheme,
    resolve_weights,
    weight_diagnostics,
)

SOLUTION_KINDS = ("conservative", "parsimonious", "intermediate")


def calibrate_frame(
    frame: pd.DataFrame,
    config: AnalysisConfig,
    *,
    names: list[str] | None = None,
) -> pd.DataFrame:
    """Construct and calibrate configured conditions while preserving design columns.

    Survey weights, strata, timing, sector and size are carried through to the
    calibrated table. They are needed for design-aware estimation and for the
    subgroup robustness checks, and dropping them here would make those checks
    silently impossible.
    """
    identifiers = [config.case_id, config.country_column]
    passthrough = [
        column
        for column in [*config.passthrough_columns(), config.timing.period_column]
        if column in frame.columns and column not in identifiers
    ]
    calibrated = frame[[*identifiers, *passthrough]].copy()
    specs: dict[str, SetSpec] = {**config.conditions, **config.outcome}
    selected = names if names is not None else list(specs)
    for name in selected:
        if name not in specs:
            raise KeyError(f"unknown calibrated set: {name}")
        spec = specs[name]
        if spec.source is not None:
            if spec.source not in frame.columns:
                raise KeyError(f"missing source column for {name}: {spec.source}")
            raw = pd.to_numeric(frame[spec.source], errors="coerce")
            calibrated[f"{name}_raw"] = raw
        else:
            assert spec.composite is not None
            raw = build_composite(frame, spec.composite)
            calibrated[f"{name}_raw"] = raw
        calibrated[name] = direct_calibrate(raw, spec.anchors)
    return calibrated


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


def _term_membership(frame: pd.DataFrame, literals: dict[str, bool]) -> np.ndarray:
    operands = [
        frame[name].to_numpy(dtype=float) if present else 1.0 - frame[name].to_numpy(dtype=float)
        for name, present in literals.items()
    ]
    return fuzzy_and(*operands)


def _estimand_columns(config: AnalysisConfig) -> dict[WeightScheme, str]:
    """Map each configured estimand to its weight column in the calibrated frame."""
    return {scheme: f"weight_{scheme}" for scheme in config.survey.estimands}


def _write_analysis_cases(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    conditions: list[str],
    outcome: str,
    group_dir: Path,
) -> None:
    """Export the exact cases and calibrated sets analysed by one group."""
    identifiers = [
        column
        for column in [
            config.case_id,
            config.country_column,
            "macroregion",
            config.timing.year_column,
            config.timing.period_column,
            "sector",
            "size_class",
            config.survey.strata_column,
            ANALYSIS_WEIGHT_COLUMN,
        ]
        if column and column in frame.columns
    ]
    columns = [*dict.fromkeys(identifiers), *conditions, outcome]
    frame[columns].to_csv(group_dir / "analysis_cases.csv", index=False)


def _run_group(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    conditions: list[str],
    outcome: str,
    label: str,
    output_dir: Path,
) -> dict[str, Any]:
    group_dir = output_dir / label
    group_dir.mkdir(parents=True, exist_ok=True)
    thresholds = config.truth_table.thresholds()
    weights = frame[ANALYSIS_WEIGHT_COLUMN] if ANALYSIS_WEIGHT_COLUMN in frame.columns else None

    # The exact cases this group analysed. The canonical R engine consumes this
    # file rather than the pooled table, so a regional validation cannot
    # silently be run against the whole European sample.
    _write_analysis_cases(
        frame, config=config, conditions=conditions, outcome=outcome, group_dir=group_dir
    )

    necessity = necessity_table(
        frame, conditions=conditions, outcome=outcome, weights=weights
    )
    truth = build_truth_table(
        frame,
        conditions=conditions,
        outcome=outcome,
        thresholds=thresholds,
        weights=weights,
    )
    solutions = {
        kind: minimize_truth_table(
            truth,
            conditions=conditions,
            kind=kind,
            directional_expectations=config.directional_expectations,
        )
        for kind in SOLUTION_KINDS
    }

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
    core_peripheral_table(solutions["intermediate"], conditions).to_csv(
        group_dir / "core_peripheral.csv",
        index=False,
    )

    estimands = _estimand_columns(config)
    solution_rows: list[dict[str, object]] = []
    for solution in solutions.values():
        membership = _membership_from_sympy(frame, solution.sympy_expression)
        for estimand, column in estimands.items():
            estimand_weights = frame[column].to_numpy() if column in frame.columns else None
            fit = sufficiency_fit(
                membership,
                frame[outcome].to_numpy(dtype=float),
                weights=estimand_weights,
            )
            solution_rows.append(
                {
                    "solution": solution.kind,
                    "estimand": estimand,
                    "primary_estimand": estimand == config.survey.primary_estimand,
                    "expression": solution.expression,
                    "consistency": fit.consistency,
                    "coverage": fit.coverage,
                    "pri": fit.pri,
                }
            )
    pd.DataFrame(solution_rows).to_csv(group_dir / "solutions.csv", index=False)

    term_rows: list[dict[str, object]] = []
    for solution in solutions.values():
        for term_index, literals in enumerate(solution_terms(solution, conditions), start=1):
            membership = _term_membership(frame, literals)
            for estimand, column in estimands.items():
                estimand_weights = frame[column].to_numpy() if column in frame.columns else None
                fit = sufficiency_fit(
                    membership,
                    frame[outcome].to_numpy(dtype=float),
                    weights=estimand_weights,
                )
                term_rows.append(
                    {
                        "solution": solution.kind,
                        "term": term_index,
                        "estimand": estimand,
                        "primary_estimand": estimand == config.survey.primary_estimand,
                        "configuration": format_literals(literals),
                        "configuration_json": json.dumps(literals, sort_keys=True),
                        "n_relevant_establishments": int((membership > 0.5).sum()),
                        "country_distribution": _distribution_json(frame, "country", membership),
                        "regional_distribution": _distribution_json(
                            frame, "macroregion", membership
                        ),
                        "consistency": fit.consistency,
                        "coverage": fit.coverage,
                        "pri": fit.pri,
                    }
                )
    pd.DataFrame(term_rows).to_csv(group_dir / "solution_terms.csv", index=False)

    intermediate_terms = solution_terms(solutions["intermediate"], conditions)
    term_substitutability(intermediate_terms).to_csv(
        group_dir / "term_substitutability.csv", index=False
    )

    return {
        "label": label,
        "n": len(frame),
        "weight_mass": float(weights.sum()) if weights is not None else float(len(frame)),
        "frequency_cutoff": thresholds.frequency,
        "consistency_cutoff": thresholds.consistency,
        "pri_cutoff": thresholds.pri,
        "frequency_basis": thresholds.frequency_basis,
        "conservative": solutions["conservative"].expression,
        "parsimonious": solutions["parsimonious"].expression,
        "intermediate": solutions["intermediate"].expression,
        "n_positive_rows": int(truth["positive"].sum()),
        "conservative_object": solutions["conservative"],
        "intermediate_object": solutions["intermediate"],
    }


def _prepare_sample(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    sample: SampleSpec,
    mapping: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Select, calibrate and weight one analytical sample."""
    conditions = list(sample.conditions or config.conditions)
    outcome = config.outcome_name
    selected, recorder = select_sample(
        frame, sample=sample, weight_column=config.survey.weight_column
    )
    selected = assign_period(selected, config.timing)
    calibrated = calibrate_frame(selected, config, names=[*conditions, outcome])
    calibrated = attach_regions(
        calibrated,
        country_column=config.country_column,
        mapping=mapping,
    )
    complete = calibrated[[*conditions, outcome]].notna().all(axis=1)
    calibrated = calibrated.loc[complete].copy()
    recorder.record(
        calibrated,
        step="complete_calibrated_sets",
        rule=f"observed values for {', '.join([*conditions, outcome])}",
    )
    for scheme, column in _estimand_columns(config).items():
        calibrated[column] = resolve_weights(
            calibrated,
            scheme=scheme,
            weight_column=config.survey.weight_column,
            country_column=config.country_column,
        )
    calibrated[ANALYSIS_WEIGHT_COLUMN] = calibrated[
        _estimand_columns(config)[config.survey.primary_estimand]
    ]
    return calibrated, recorder.table(), conditions


def _run_sample(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    sample: SampleSpec,
    mapping: dict[str, str],
    alternative_schemes: dict[str, dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    """Run the complete analysis for one analytical sample."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outcome = config.outcome_name
    calibrated, attrition, conditions = _prepare_sample(
        frame, config=config, sample=sample, mapping=mapping
    )
    calibrated.to_csv(output_dir / "calibrated_memberships.csv", index=False)
    attrition.to_csv(output_dir / "analytical_sample.csv", index=False)
    weight_diagnostics(
        calibrated,
        weights=calibrated[ANALYSIS_WEIGHT_COLUMN],
        group_columns=[config.country_column, "macroregion"],
    ).to_csv(output_dir / "weight_diagnostics.csv", index=False)
    timing_summary(calibrated, config=config).to_csv(output_dir / "survey_timing.csv", index=False)

    summaries: list[dict[str, Any]] = []
    europe = _run_group(
        calibrated,
        config=config,
        conditions=conditions,
        outcome=outcome,
        label="europe",
        output_dir=output_dir,
    )
    summaries.append(_public(europe))

    regional_objects: dict[str, dict[str, Any]] = {}
    directed_configurations: dict[str, list[dict[str, bool]]] = {}
    for region, group in calibrated.groupby("macroregion", observed=True):
        result = _run_group(
            group,
            config=config,
            conditions=conditions,
            outcome=outcome,
            label=f"region_{str(region).lower()}",
            output_dir=output_dir,
        )
        summaries.append(_public(result))
        regional_objects[str(region)] = result
        region_terms = solution_terms(result["conservative_object"], conditions)
        if region_terms:
            directed_configurations[str(region)] = region_terms

    europe_terms = solution_terms(europe["conservative_object"], conditions)
    _write_regional_comparison(
        summaries,
        europe_terms=europe_terms,
        regional_objects=regional_objects,
        conditions=conditions,
        calibrated=calibrated,
        outcome=outcome,
        output_dir=output_dir,
    )

    # Causal asymmetry: repeat the full analysis for the negated outcome.
    negative = calibrated.copy()
    neg_outcome = f"NOT_{outcome}"
    negative[neg_outcome] = 1.0 - negative[outcome]
    negative_result = _run_group(
        negative,
        config=config,
        conditions=conditions,
        outcome=neg_outcome,
        label="europe_negative_outcome",
        output_dir=output_dir,
    )

    _write_portability(
        calibrated,
        config=config,
        conditions=conditions,
        outcome=outcome,
        europe_terms=europe_terms,
        directed_configurations=directed_configurations,
        output_dir=output_dir,
    )
    _write_conjunctural_diagnostics(
        calibrated,
        config=config,
        conditions=conditions,
        outcome=outcome,
        europe_terms=europe_terms,
        directed_configurations=directed_configurations,
        intermediate_terms=solution_terms(europe["intermediate_object"], conditions),
        output_dir=output_dir,
    )
    if config.robustness.enabled:
        _write_robustness(
            frame,
            calibrated,
            config=config,
            sample=sample,
            conditions=conditions,
            outcome=outcome,
            alternative_schemes=alternative_schemes,
            output_dir=output_dir,
        )

    return {
        "sample": sample.label,
        "primary": sample.primary,
        "conditions": conditions,
        "output_dir": str(output_dir),
        "groups": summaries,
        "negative_outcome": _public(negative_result),
        "n_complete_calibrated": len(calibrated),
        "weight_mass": float(calibrated[ANALYSIS_WEIGHT_COLUMN].sum()),
        "regions": calibrated["macroregion"].value_counts().to_dict(),
        "attrition": attrition.to_dict(orient="records"),
    }


def run_analysis(
    frame: pd.DataFrame,
    *,
    config: AnalysisConfig,
    config_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run every configured analytical sample end to end."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    regions_path = Path(config.regions_file)
    if not regions_path.is_absolute():
        regions_path = Path(config_path).resolve().parent.parent / regions_path
    mapping = load_region_map(regions_path, config.primary_region_scheme)
    alternative_schemes: dict[str, dict[str, str]] = {}
    if config.robustness.alternative_region_scheme:
        alternative_schemes[config.robustness.alternative_region_scheme] = load_region_map(
            regions_path, config.robustness.alternative_region_scheme
        )

    outcome = config.outcome_name
    with (target / "qca_specification.json").open("w", encoding="utf-8") as stream:
        json.dump(_specification(config, outcome), stream, indent=2)

    sample_results: list[dict[str, Any]] = []
    attrition_frames: list[pd.DataFrame] = []
    for sample in config.samples.values():
        sample_dir = target if sample.primary else target / f"sample_{sample.label}"
        result = _run_sample(
            frame,
            config=config,
            sample=sample,
            mapping=mapping,
            alternative_schemes=alternative_schemes,
            output_dir=sample_dir,
        )
        sample_results.append(result)
        attrition = pd.DataFrame(result["attrition"])
        if not attrition.empty:
            attrition_frames.append(attrition)
    if attrition_frames:
        pd.concat(attrition_frames, ignore_index=True).to_csv(
            target / "analytical_samples.csv", index=False
        )

    primary = next(item for item in sample_results if item["primary"])
    summary_payload: dict[str, Any] = {
        "samples": sample_results,
        "primary_sample": primary["sample"],
        "groups": primary["groups"],
        "negative_outcome": primary["negative_outcome"],
        "n_complete_calibrated": primary["n_complete_calibrated"],
        "regions": primary["regions"],
        "estimand": config.survey.primary_estimand,
    }
    with (target / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary_payload, stream, indent=2, default=str)
    return summary_payload


def _specification(config: AnalysisConfig, outcome: str) -> dict[str, Any]:
    return {
        "conditions": list(config.conditions),
        "outcome": outcome,
        "frequency_cutoff": config.truth_table.frequency_cutoff,
        "consistency_cutoff": config.truth_table.consistency_cutoff,
        "pri_cutoff": config.truth_table.pri_cutoff,
        "frequency_basis": "cases",
        "canonical_engine": "CRAN QCA; the Python minimiser is the cross-check",
        "logical_remainder_policy": {
            "conservative": "observed positive rows only",
            "parsimonious": "unobserved rows treated as logical remainders",
            "intermediate": "easy counterfactuals only, given directional expectations",
        },
        "directional_expectations": config.directional_expectations,
        "calibration_scope": "common Europe-wide anchors",
        "survey_design": {
            "weight_column": config.survey.weight_column,
            "strata_column": config.survey.strata_column,
            "primary_estimand": config.survey.primary_estimand,
            "estimands": list(config.survey.estimands),
        },
        "timing": {
            "year_column": config.timing.year_column,
            "reference_period_years": config.timing.reference_period_years,
            "periods": config.timing.periods,
        },
        "samples": {
            key: {
                "label": sample.label,
                "primary": sample.primary,
                "conditions": sample.conditions,
                "description": sample.description,
                "filters": [rule.model_dump() for rule in sample.filters],
            }
            for key, sample in config.samples.items()
        },
    }


def _write_regional_comparison(
    summaries: list[dict[str, Any]],
    *,
    europe_terms: list[dict[str, bool]],
    regional_objects: dict[str, dict[str, Any]],
    conditions: list[str],
    calibrated: pd.DataFrame,
    outcome: str,
    output_dir: Path,
) -> None:
    """Compare regional solutions with the pooled solution term by term."""
    europe = next((summary for summary in summaries if summary["label"] == "europe"), None)
    if europe is None:
        return
    total_n = int(europe["n"])
    europe_keys = {format_literals(term) for term in europe_terms}
    rows: list[dict[str, Any]] = []
    term_rows: list[dict[str, Any]] = []
    for region, result in regional_objects.items():
        region_terms = solution_terms(result["conservative_object"], conditions)
        region_keys = {format_literals(term) for term in region_terms}
        shared = region_keys & europe_keys
        n_cases = int(result["n"])
        rows.append(
            {
                "region": region,
                "n_cases": n_cases,
                "weight_mass": result["weight_mass"],
                "relative_prevalence": n_cases / total_n if total_n else 0.0,
                "frequency_cutoff": result["frequency_cutoff"],
                "consistency_cutoff": result["consistency_cutoff"],
                "pri_cutoff": result["pri_cutoff"],
                "conservative_solution": result["conservative"],
                "parsimonious_solution": result["parsimonious"],
                "intermediate_solution": result["intermediate"],
                "n_positive_rows": result["n_positive_rows"],
                "n_terms": len(region_terms),
                "n_terms_shared_with_europe": len(shared),
                "n_terms_region_specific": len(region_keys - europe_keys),
                "n_europe_terms_absent": len(europe_keys - region_keys),
                "shared_term_share": len(shared) / len(region_keys) if region_keys else 0.0,
                "conservative_similarity": signed_literal_jaccard(
                    europe["conservative"], result["conservative"]
                ),
                "conservative_change": classify_solution_change(
                    europe["conservative"], result["conservative"]
                ),
                "conservative_matches_europe": result["conservative"] == europe["conservative"],
                "parsimonious_matches_europe": result["parsimonious"] == europe["parsimonious"],
            }
        )
        for literals in region_terms:
            key = format_literals(literals)
            membership = _term_membership(calibrated, literals)
            fit = sufficiency_fit(
                membership,
                calibrated[outcome].to_numpy(dtype=float),
                weights=(
                    calibrated[ANALYSIS_WEIGHT_COLUMN].to_numpy()
                    if ANALYSIS_WEIGHT_COLUMN in calibrated.columns
                    else None
                ),
            )
            term_rows.append(
                {
                    "region": region,
                    "configuration": key,
                    "status": "shared_with_europe" if key in europe_keys else "region_specific",
                    "pooled_consistency": fit.consistency,
                    "pooled_coverage": fit.coverage,
                    "pooled_pri": fit.pri,
                }
            )
        for key in sorted(europe_keys - region_keys):
            term_rows.append(
                {
                    "region": region,
                    "configuration": key,
                    "status": "europe_term_absent_in_region",
                    "pooled_consistency": float("nan"),
                    "pooled_coverage": float("nan"),
                    "pooled_pri": float("nan"),
                }
            )
    pd.DataFrame(rows).to_csv(output_dir / "regional_comparison.csv", index=False)
    pd.DataFrame(
        term_rows,
        columns=[
            "region",
            "configuration",
            "status",
            "pooled_consistency",
            "pooled_coverage",
            "pooled_pri",
        ],
    ).to_csv(output_dir / "regional_term_comparison.csv", index=False)


def _write_portability(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    conditions: list[str],
    outcome: str,
    europe_terms: list[dict[str, bool]],
    directed_configurations: dict[str, list[dict[str, bool]]],
    output_dir: Path,
) -> None:
    replicates = config.robustness.portability_bootstrap_replicates
    rule = PortabilityThresholds(consistency=config.truth_table.consistency_cutoff)
    portability_rows: list[pd.DataFrame] = []
    for index, literals in enumerate(europe_terms, start=1):
        summary = evaluate_portability(
            calibrated,
            literals=literals,
            outcome=outcome,
            region_column="macroregion",
            weight_column=ANALYSIS_WEIGHT_COLUMN,
        )
        term_table = summary.table.copy()
        term_table.insert(0, "term", index)
        term_table.insert(1, "configuration", format_literals(literals))
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
    portability.to_csv(output_dir / "portability.csv", index=False)

    directed_table, directed_matrix, directed_network = directed_portability(
        calibrated,
        configurations=directed_configurations,
        outcome=outcome,
        region_column="macroregion",
        weight_column=ANALYSIS_WEIGHT_COLUMN,
        thresholds=rule,
        n_bootstrap=replicates,
        seed=config.robustness.random_seed,
    )
    directed_table.to_csv(output_dir / "portability_directed.csv", index=False)
    directed_matrix.to_csv(output_dir / "portability_matrix.csv", index=False)
    directed_network.to_csv(output_dir / "portability_network.csv", index=False)

    bootstrap_directed_portability(
        calibrated,
        outcome=outcome,
        conditions=conditions,
        thresholds=config.truth_table.thresholds(),
        region_column="macroregion",
        weight_column=ANALYSIS_WEIGHT_COLUMN,
        n_bootstrap=config.robustness.portability_discovery_replicates,
        seed=config.robustness.random_seed,
        portability=rule,
    ).to_csv(output_dir / "portability_bootstrap.csv", index=False)

    country_configurations = {"europe": europe_terms, **directed_configurations}
    country_portability(
        calibrated,
        configurations=country_configurations,
        outcome=outcome,
        country_column=config.country_column,
        weight_column=ANALYSIS_WEIGHT_COLUMN,
    ).to_csv(output_dir / "country_portability.csv", index=False)


def _write_conjunctural_diagnostics(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    conditions: list[str],
    outcome: str,
    europe_terms: list[dict[str, bool]],
    directed_configurations: dict[str, list[dict[str, bool]]],
    intermediate_terms: list[dict[str, bool]],
    output_dir: Path,
) -> None:
    configurations = {"europe": europe_terms, **directed_configurations}
    condition_cooccurrence(configurations).to_csv(
        output_dir / "condition_cooccurrence.csv", index=False
    )
    conjunctural_dependence(
        calibrated,
        conditions=conditions,
        outcome=outcome,
        weights=(
            calibrated[ANALYSIS_WEIGHT_COLUMN]
            if ANALYSIS_WEIGHT_COLUMN in calibrated.columns
            else None
        ),
    ).to_csv(output_dir / "conjunctural_dependence.csv", index=False)
    term_substitutability(intermediate_terms).to_csv(
        output_dir / "substitutability.csv", index=False
    )


def _write_weighted_truth_table_exploration(
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    conditions: list[str],
    outcome: str,
    output_dir: Path,
) -> None:
    """Compare row inclusion under case, weight-mass and effective-n rules.

    This is an appendix, not an analysis. Row existence in the canonical truth
    table counts sampled establishments, because that is what the standard
    procedure and the CRAN ``QCA`` package implement. Weighted row existence is
    shown here only so the consequences of the design can be inspected.
    """
    target = output_dir / "exploratory"
    target.mkdir(parents=True, exist_ok=True)
    # The question is what the *survey design* would do to row inclusion, so
    # this uses the published weights even when the primary estimand does not.
    population_column = _estimand_columns(config).get("firm_population")
    weights = (
        calibrated[population_column]
        if population_column and population_column in calibrated.columns
        else calibrated[ANALYSIS_WEIGHT_COLUMN]
    )
    base = config.truth_table
    frames: list[pd.DataFrame] = []
    for basis in ("cases", "weighted", "effective"):
        table = build_truth_table(
            calibrated,
            conditions=conditions,
            outcome=outcome,
            thresholds=TruthTableThresholds(
                frequency=base.frequency_cutoff,
                consistency=base.consistency_cutoff,
                pri=base.pri_cutoff,
                frequency_basis=basis,
            ),
            weights=weights,
        )
        frames.append(
            table[["row", "frequency", "weighted_frequency", "effective_frequency", "positive"]]
            .assign(frequency_basis=basis)
        )
    comparison = pd.concat(frames, ignore_index=True)
    comparison["canonical"] = comparison["frequency_basis"] == "cases"
    comparison.to_csv(target / "weighted_truth_table_comparison.csv", index=False)


def _write_robustness(
    raw_frame: pd.DataFrame,
    calibrated: pd.DataFrame,
    *,
    config: AnalysisConfig,
    sample: SampleSpec,
    conditions: list[str],
    outcome: str,
    alternative_schemes: dict[str, dict[str, str]],
    output_dir: Path,
) -> None:
    if config.robustness.weighted_truth_table_exploration:
        _write_weighted_truth_table_exploration(
            calibrated,
            config=config,
            conditions=conditions,
            outcome=outcome,
            output_dir=output_dir,
        )
    threshold_sweep(
        calibrated,
        config=config,
        outcome=outcome,
        conditions=conditions,
        weight_column=ANALYSIS_WEIGHT_COLUMN,
    ).to_csv(output_dir / "threshold_sensitivity.csv", index=False)

    def calibrator(frame: pd.DataFrame, variant: AnalysisConfig) -> pd.DataFrame:
        selected, _ = select_sample(
            frame, sample=sample, weight_column=variant.survey.weight_column
        )
        calibrated_variant = calibrate_frame(
            selected, variant, names=[*conditions, variant.outcome_name]
        )
        calibrated_variant = calibrated_variant.dropna(
            subset=[*conditions, variant.outcome_name]
        )
        for scheme, column in _estimand_columns(variant).items():
            calibrated_variant[column] = resolve_weights(
                calibrated_variant,
                scheme=scheme,
                weight_column=variant.survey.weight_column,
                country_column=variant.country_column,
            )
        calibrated_variant[ANALYSIS_WEIGHT_COLUMN] = calibrated_variant[
            _estimand_columns(variant)[variant.survey.primary_estimand]
        ]
        return calibrated_variant

    anchor_sweep(
        raw_frame,
        config=config,
        calibrator=calibrator,
        conditions=conditions,
        weight_column=ANALYSIS_WEIGHT_COLUMN,
    ).to_csv(output_dir / "calibration_sensitivity.csv", index=False)

    estimand_sweep(
        calibrated,
        config=config,
        outcome=outcome,
        conditions=conditions,
    ).to_csv(output_dir / "estimand_sensitivity.csv", index=False)

    omission_groups = [config.country_column, "sector", "size_class"]
    if config.timing.periods:
        omission_groups.append(config.timing.period_column)
    for group_column in omission_groups:
        if group_column not in calibrated.columns:
            continue
        name = "country" if group_column == config.country_column else group_column
        leave_one_group_out(
            calibrated,
            config=config,
            outcome=outcome,
            group_column=group_column,
            conditions=conditions,
            weight_column=ANALYSIS_WEIGHT_COLUMN,
        ).to_csv(output_dir / f"leave_one_{name}_out.csv", index=False)

    if alternative_schemes:
        region_scheme_comparison(
            calibrated,
            config=config,
            outcome=outcome,
            schemes=alternative_schemes,
            conditions=conditions,
            weight_column=ANALYSIS_WEIGHT_COLUMN,
        ).to_csv(output_dir / "regional_taxonomy_robustness.csv", index=False)

    replicates = config.robustness.bootstrap_replicates
    if replicates:
        bootstrap = bootstrap_qca(
            calibrated,
            config=config,
            outcome=outcome,
            n_bootstrap=replicates,
            seed=config.robustness.random_seed,
            conditions=conditions,
            weight_column=ANALYSIS_WEIGHT_COLUMN,
            strata_column=config.survey.strata_column,
        )
        bootstrap.to_csv(output_dir / "bootstrap_draws.csv", index=False)
        bootstrap_stability(bootstrap).to_csv(
            output_dir / "bootstrap_stability.csv", index=False
        )
        bootstrap_term_stability(bootstrap).to_csv(
            output_dir / "bootstrap_term_stability.csv", index=False
        )


def _public(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.endswith("_object")}


def _distribution_json(frame: pd.DataFrame, column: str, membership: np.ndarray) -> str:
    if column not in frame.columns:
        return "{}"
    relevant = pd.Series(membership > 0.5, index=frame.index)
    counts = frame.loc[relevant, column].value_counts(dropna=False).to_dict()
    return json.dumps({str(key): int(value) for key, value in counts.items()}, sort_keys=True)
