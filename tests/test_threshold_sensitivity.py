from __future__ import annotations

from euro_fsqca.analysis.robustness import estimand_sweep, region_scheme_comparison, threshold_sweep
from euro_fsqca.config import load_config
from euro_fsqca.data.regions import load_region_map
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame

CONDITIONS = ["DIG", "HC", "FIN", "INT", "EXTK"]


def test_threshold_sweep_reports_diagnostics() -> None:
    config = load_config("configs/analysis.demo.yml")
    config.robustness.consistency_cutoffs = [0.8]
    config.robustness.pri_cutoffs = [0.5]
    config.robustness.frequency_cutoffs = [2]
    frame = generate_demo(n=200, seed=4)
    calibrated = calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])

    result = threshold_sweep(
        calibrated, config=config, outcome=config.outcome_name, conditions=CONDITIONS
    )

    assert "n_contradictory_rows" in result.columns
    assert "n_conservative_terms" in result.columns
    assert "conservative_similarity" in result.columns
    assert "conservative_term_similarity" in result.columns


def test_estimand_sweep_compares_weighting_schemes() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=400, seed=6)
    calibrated = calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])

    result = estimand_sweep(
        calibrated, config=config, outcome=config.outcome_name, conditions=CONDITIONS
    )

    assert list(result["estimand"]) == ["unweighted", "firm_population", "equal_country"]
    assert "conservative_solution" in result.columns
    # Every estimand is reported on the same set of establishments.
    assert set(result["n"]) == {len(calibrated)}


def test_region_scheme_comparison_uses_the_alternative_taxonomy() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=400, seed=15)
    calibrated = calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])
    mapping = load_region_map("configs/regions.yml", "eu4_robustness")

    result = region_scheme_comparison(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        schemes={"eu4_robustness": mapping},
        conditions=CONDITIONS,
        min_cases=10,
    )

    assert set(result["scheme"]) == {"eu4_robustness"}
    assert set(result["region"]) == {"north", "west", "south", "east"}
