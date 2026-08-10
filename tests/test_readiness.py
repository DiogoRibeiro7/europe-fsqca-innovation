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


def test_run_is_gated_on_every_blocker_not_only_the_template_flag(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    runner = CliRunner()
    # A configuration that is NOT marked as a template still fails, because the
    # manifest, schema audit and mappings are independent blockers.
    config = tmp_path / "research.yml"
    payload = (root / "configs" / "analysis.demo.yml").read_text(encoding="utf-8")
    config.write_text(payload.replace("status: research", "status: research"), encoding="utf-8")
    frame = tmp_path / "input.csv"
    frame.write_text("firm_id,country\nA,Portugal\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(frame),
            "--config",
            str(config),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to run" in result.output
    assert "data_manifest" in result.output
    assert "schema_audit" in result.output


def test_unsafe_development_run_warns_loudly(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
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
            str(root / "configs" / "analysis.demo.yml"),
            "--output-dir",
            str(tmp_path / "out"),
            "--unsafe-development-run",
        ],
    )

    assert "UNSAFE DEVELOPMENT RUN" in result.output
    assert "NOT an empirical result" in result.output


def test_readiness_flags_a_restricted_sample_without_executable_filters(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "configs" / "analysis.demo.yml").read_text(encoding="utf-8")
    # Strip the management sample's filters, leaving the restriction as prose.
    stripped = source.replace(
        """    filters:
      - column: n_employees
        min: 20
        description: establishments with at least twenty workers
      - column: management_raw
        require_non_missing: true
        description: complete management-practice answers""",
        "    filters: []",
    )
    config = tmp_path / "unfiltered.yml"
    config.write_text(stripped, encoding="utf-8")

    report = assess_readiness(
        config_path=config,
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=root / "data" / "manifest.csv",
        raw_root=root / "data" / "raw",
    )

    row = report[report["check"] == "sample_filters"].iloc[0]
    assert row["status"] == FATAL
    assert "management_20plus" in row["detail"]


def test_readiness_accepts_a_completed_schema_audit(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    audit = tmp_path / "schema_audit.csv"
    audit.write_text("source_name,column\nPT,idstd\nES,idstd\n", encoding="utf-8")

    report = assess_readiness(
        config_path=root / "configs" / "analysis.demo.yml",
        mapping_path=root / "configs" / "wbes_variable_map.yml",
        manifest_path=root / "data" / "manifest.csv",
        raw_root=root / "data" / "raw",
        schema_audit_path=audit,
    )

    row = report[report["check"] == "schema_audit"].iloc[0]
    assert row["status"] == "ok"
    assert "2 source files" in row["detail"]
