from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from euro_fsqca.config import AnalysisConfig, load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame, run_analysis
from euro_fsqca.survey import ANALYSIS_WEIGHT_COLUMN


def _demo_config() -> tuple[Path, AnalysisConfig]:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs" / "analysis.demo.yml"
    config = load_config(config_path)
    config.robustness.consistency_cutoffs = [0.80]
    config.robustness.pri_cutoffs = [0.50]
    config.robustness.frequency_cutoffs = [3]
    config.robustness.bootstrap_replicates = 3
    config.robustness.portability_bootstrap_replicates = 3
    return config_path, config


def test_end_to_end_demo(tmp_path: Path) -> None:
    config_path, config = _demo_config()
    frame = generate_demo(n=600, seed=7)
    output = tmp_path / "results"
    summary = run_analysis(
        frame,
        config=config,
        config_path=config_path,
        output_dir=output,
    )

    assert summary["primary_sample"] == "primary"
    assert summary["n_complete_calibrated"] > 0
    for name in [
        "qca_specification.json",
        "analytical_samples.csv",
        "weight_diagnostics.csv",
        "survey_timing.csv",
        "regional_comparison.csv",
        "regional_term_comparison.csv",
        "portability.csv",
        "portability_directed.csv",
        "portability_matrix.csv",
        "portability_network.csv",
        "portability_bootstrap.csv",
        "country_portability.csv",
        "condition_cooccurrence.csv",
        "conjunctural_dependence.csv",
        "substitutability.csv",
        "threshold_sensitivity.csv",
        "calibration_sensitivity.csv",
        "estimand_sensitivity.csv",
        "bootstrap_stability.csv",
        "bootstrap_term_stability.csv",
        "regional_taxonomy_robustness.csv",
        "leave_one_country_out.csv",
    ]:
        assert (output / name).exists(), name
    for name in [
        "truth_table.csv",
        "truth_table_diagnostics.csv",
        "contradictory_rows.csv",
        "diversity_diagnostics.csv",
        "difficult_rows.csv",
        "solution_terms.csv",
        "solutions.csv",
        "core_peripheral.csv",
    ]:
        assert (output / "europe" / name).exists(), name


def test_pipeline_runs_the_declared_management_extension(tmp_path: Path) -> None:
    config_path, config = _demo_config()
    frame = generate_demo(n=800, seed=11)
    output = tmp_path / "results"
    summary = run_analysis(
        frame, config=config, config_path=config_path, output_dir=output
    )

    extension = output / "sample_management_20plus"
    assert (extension / "europe" / "truth_table.csv").exists()

    attrition = pd.read_csv(output / "analytical_samples.csv")
    restricted = attrition[attrition["sample"] == "management_20plus"]
    # The management module is only asked of larger establishments, so the
    # extension sample must describe a smaller population than the primary one.
    assert restricted["retained_share"].iloc[-1] < 1.0
    labels = {item["sample"] for item in summary["samples"]}
    assert labels == {"primary", "management_20plus"}


def test_subgroup_robustness_outputs_exist_because_design_columns_survive(
    tmp_path: Path,
) -> None:
    config_path, config = _demo_config()
    frame = generate_demo(n=600, seed=13)
    output = tmp_path / "results"
    run_analysis(frame, config=config, config_path=config_path, output_dir=output)

    assert (output / "leave_one_sector_out.csv").exists()
    assert (output / "leave_one_size_class_out.csv").exists()
    assert (output / "leave_one_survey_period_out.csv").exists()


def test_calibrate_frame_preserves_survey_design_columns() -> None:
    _, config = _demo_config()
    frame = generate_demo(n=200, seed=17)

    calibrated = calibrate_frame(frame, config, names=["DIG", "INN"])

    for column in ["sampling_weight", "stratum", "survey_year", "sector", "size_class"]:
        assert column in calibrated.columns
    assert "DIG_raw" in calibrated.columns
    assert "MGT" not in calibrated.columns


def test_specification_records_the_survey_design(tmp_path: Path) -> None:
    config_path, config = _demo_config()
    frame = generate_demo(n=400, seed=19)
    output = tmp_path / "results"
    run_analysis(frame, config=config, config_path=config_path, output_dir=output)

    with (output / "qca_specification.json").open(encoding="utf-8") as stream:
        specification = json.load(stream)

    assert specification["survey_design"]["weight_column"] == "sampling_weight"
    assert specification["timing"]["reference_period_years"] == 3
    assert set(specification["samples"]) == {"primary", "management"}
    assert specification["directional_expectations"]["DIG"] == "present"


def test_solution_metrics_are_reported_for_every_estimand(tmp_path: Path) -> None:
    config_path, config = _demo_config()
    frame = generate_demo(n=600, seed=23)
    output = tmp_path / "results"
    run_analysis(frame, config=config, config_path=config_path, output_dir=output)

    solutions = pd.read_csv(output / "europe" / "solutions.csv")
    assert set(solutions["estimand"]) == {"unweighted", "firm_population", "equal_country"}
    assert set(solutions["solution"]) == {"conservative", "parsimonious", "intermediate"}

    calibrated = pd.read_csv(output / "calibrated_memberships.csv")
    assert ANALYSIS_WEIGHT_COLUMN in calibrated.columns
