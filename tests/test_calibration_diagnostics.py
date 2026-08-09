from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.analysis.calibration import (
    calibration_group_summary,
    calibration_summary,
    write_calibration_diagnostics,
)
from euro_fsqca.config import load_config


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "firm_id": ["a", "b", "c"],
            "country": ["PT", "ES", "PT"],
            "macroregion": ["South", "South", "South"],
            "digital_raw": [0, 50, 100],
            "human_raw": [0, 50, 100],
            "finance_raw": [0, 50, 100],
            "international_raw": [0, 50, 100],
            "management_raw": [0, 50, 100],
            "external_knowledge_raw": [0, 50, 100],
            "innovation_raw": [0, 50, 100],
        }
    )


def test_calibration_summary_checks_bounds_and_monotonicity() -> None:
    config = load_config("configs/analysis.demo.yml")

    summary = calibration_summary(_frame(), config=config)

    assert set(summary["bounds_ok"]) == {True}
    assert set(summary["monotone_ok"]) == {True}
    exact = summary.loc[summary["set_name"] == "DIG", "n_exact_0_5"].astype(int).iloc[0]
    assert exact == 1


def test_calibration_group_summary_uses_common_scale() -> None:
    config = load_config("configs/analysis.demo.yml")

    summary = calibration_group_summary(_frame(), config=config, group_column="country")

    assert {"PT", "ES"} == set(summary["country"])
    assert "DIG" in set(summary["set_name"])


def test_write_calibration_diagnostics(tmp_path: Path) -> None:
    config = load_config("configs/analysis.demo.yml")

    write_calibration_diagnostics(_frame(), config=config, output_dir=tmp_path)

    assert (tmp_path / "calibration_summary.csv").exists()
    assert (tmp_path / "calibration_country_summary.csv").exists()
