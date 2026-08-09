from __future__ import annotations

from euro_fsqca.analysis.robustness import threshold_sweep
from euro_fsqca.config import load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame


def test_threshold_sweep_reports_diagnostics() -> None:
    config = load_config("configs/analysis.demo.yml")
    config.robustness.consistency_cutoffs = [0.8]
    config.robustness.pri_cutoffs = [0.5]
    config.robustness.frequency_cutoffs = [2]
    frame = generate_demo(n=200, seed=4)
    calibrated = calibrate_frame(frame, config)

    result = threshold_sweep(calibrated, config=config, outcome=config.outcome_name)

    assert "n_contradictory_rows" in result.columns
    assert "n_conservative_terms" in result.columns
    assert "conservative_similarity" in result.columns
