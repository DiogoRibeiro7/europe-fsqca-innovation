from __future__ import annotations

from euro_fsqca.analysis.robustness import leave_one_group_out
from euro_fsqca.config import load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import calibrate_frame

CONDITIONS = ["DIG", "HC", "FIN", "INT", "EXTK"]


def test_leave_one_group_out_reports_solution_changes() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=200, seed=8)
    calibrated = calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])

    result = leave_one_group_out(
        calibrated,
        config=config,
        outcome=config.outcome_name,
        group_column=config.country_column,
        conditions=CONDITIONS,
        min_remaining_cases=50,
    )

    assert "removed_group" in result.columns
    assert "conservative_similarity" in result.columns
    assert not result.empty


def test_leave_one_group_out_covers_sector_and_size_because_they_are_preserved() -> None:
    config = load_config("configs/analysis.demo.yml")
    frame = generate_demo(n=300, seed=14)
    calibrated = calibrate_frame(frame, config, names=[*CONDITIONS, "INN"])

    for column in ["sector", "size_class"]:
        result = leave_one_group_out(
            calibrated,
            config=config,
            outcome=config.outcome_name,
            group_column=column,
            conditions=CONDITIONS,
            min_remaining_cases=50,
        )
        assert not result.empty, column
        assert set(result["group_column"]) == {column}
