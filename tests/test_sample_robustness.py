from __future__ import annotations

from euro_fsqca.analysis.robustness import leave_one_group_out
from euro_fsqca.config import load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame


def test_leave_one_group_out_reports_solution_changes() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=200, seed=8)
    calibrated = calibrate_frame(frame, config)

    result = leave_one_group_out(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        group_column=config.country_column,
        min_remaining_cases=50,
    )

    assert "removed_group" in result.columns
    assert "conservative_similarity" in result.columns
    assert not result.empty
