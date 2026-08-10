from __future__ import annotations

from pathlib import Path

from euro_fsqca.config import load_config
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import run_analysis


def test_end_to_end_demo(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs" / "analysis.demo.yml"
    config = load_config(config_path)
    config.robustness.consistency_cutoffs = [0.80]
    config.robustness.pri_cutoffs = [0.50]
    config.robustness.frequency_cutoffs = [3]

    frame = generate_demo(n=500, seed=7)
    output = tmp_path / "results"
    summary = run_analysis(
        frame,
        config=config,
        config_path=config_path,
        output_dir=output,
    )

    assert summary["n_complete_calibrated"] == 500
    assert (output / "qca_specification.json").exists()
    assert (output / "europe" / "truth_table.csv").exists()
    assert (output / "europe" / "truth_table_diagnostics.csv").exists()
    assert (output / "europe" / "contradictory_rows.csv").exists()
    assert (output / "europe" / "diversity_diagnostics.csv").exists()
    assert (output / "europe" / "difficult_rows.csv").exists()
    assert (output / "europe" / "solution_terms.csv").exists()
    assert (output / "regional_comparison.csv").exists()
    assert (output / "portability.csv").exists()
    assert (output / "portability_directed.csv").exists()
    assert (output / "portability_matrix.csv").exists()
    assert (output / "portability_network.csv").exists()
    assert (output / "country_portability.csv").exists()
    assert (output / "leave_one_country_out.csv").exists()
    assert (output / "fractional_logit.csv").exists()
