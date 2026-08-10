from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from euro_fsqca.cli import app
from euro_fsqca.readiness import FATAL, assess_readiness, readiness_blockers


def test_current_repository_state_is_reported_as_not_research_ready() -> None:
    root = Path(__file__).resolve().parents[1]

    report = assess_readiness(
        config_path=root / "configs" / "analysis.yml",
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=root / "data" / "manifest.csv",
        raw_root=root / "data" / "raw",
    )
    blockers = readiness_blockers(report)

    checks = dict(zip(report["check"], report["status"], strict=True))
    # These are exactly the conditions that make published findings impossible.
    assert checks["data_manifest"] == FATAL
    assert checks["variable_mapping"] == FATAL
    assert checks["calibration_anchors"] == FATAL
    assert checks["survey_weights"] == FATAL
    assert checks["survey_timing"] == FATAL
    assert len(blockers) >= 5


def test_readiness_command_exits_non_zero_while_blockers_remain() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["readiness"])

    assert result.exit_code == 1
    assert "fatal blockers remain" in result.output


def test_run_refuses_to_execute_the_template_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    frame = tmp_path / "input.csv"
    frame.write_text("firm_id,country\nA,Portugal\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(frame),
            "--config",
            "configs/analysis.yml",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 1
    assert "template" in result.output
