from __future__ import annotations

from typer.testing import CliRunner

from euro_fsqca.cli import app


def test_validate_spec_accepts_named_path() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["validate-spec", "--spec", "configs/research_spec.yml"])

    assert result.exit_code == 0
    assert "Specification validation passed" in result.output
