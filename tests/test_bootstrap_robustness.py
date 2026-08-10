from __future__ import annotations

from euro_fsqca.analysis.robustness import bootstrap_qca, bootstrap_stability
from euro_fsqca.config import load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame


def test_bootstrap_qca_records_samples() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=200, seed=9)
    calibrated = calibrate_frame(frame, config)

    result = bootstrap_qca(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        n_bootstrap=3,
        seed=1,
    )

    assert result.shape[0] == 3
    assert set(result["status"]) == {"PASS"}


def test_bootstrap_stability_counts_appearances() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=200, seed=10)
    calibrated = calibrate_frame(frame, config)
    result = bootstrap_qca(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        n_bootstrap=2,
        seed=1,
    )

    stability = bootstrap_stability(result)

    assert "appearance_frequency" in stability.columns
