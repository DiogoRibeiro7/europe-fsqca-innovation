from __future__ import annotations

import pandas as pd

from euro_fsqca.analysis.robustness import (
    bootstrap_qca,
    bootstrap_stability,
    bootstrap_term_stability,
)
from euro_fsqca.config import AnalysisConfig, load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame

CONDITIONS = ["DIG", "HC", "FIN", "INT", "EXTK"]


def _calibrated(n: int, seed: int) -> tuple[AnalysisConfig, pd.DataFrame]:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=n, seed=seed)
    return config, calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])


def test_bootstrap_qca_records_samples() -> None:
    config, calibrated = _calibrated(200, 9)

    result = bootstrap_qca(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        n_bootstrap=3,
        seed=1,
        conditions=CONDITIONS,
    )

    assert result.shape[0] == 3
    assert set(result["status"]) == {"PASS"}


def test_bootstrap_stability_counts_appearances() -> None:
    config, calibrated = _calibrated(200, 10)
    result = bootstrap_qca(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        n_bootstrap=2,
        seed=1,
        conditions=CONDITIONS,
    )

    stability = bootstrap_stability(result)
    terms = bootstrap_term_stability(result)

    assert "appearance_frequency" in stability.columns
    assert "configuration" in terms.columns


def test_bootstrap_can_resample_within_strata() -> None:
    config, calibrated = _calibrated(300, 12)

    result = bootstrap_qca(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        n_bootstrap=2,
        seed=3,
        conditions=CONDITIONS,
        strata_column=config.survey.strata_column,
    )

    # A stratified bootstrap preserves the stratum sizes of the original sample.
    assert set(result["n"]) == {len(calibrated)}
