from __future__ import annotations

from pathlib import Path


def test_r_environment_setup_script_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "r" / "setup_renv.R"
    content = script.read_text(encoding="utf-8")

    assert "required_packages <- c(\"renv\", \"QCA\")" in content
    assert "--install" in content


def test_r_environment_docs_reference_crosscheck() -> None:
    root = Path(__file__).resolve().parents[1]
    content = (root / "r" / "README.md").read_text(encoding="utf-8")

    assert "qca_crosscheck.R" in content
    assert "calibrated_memberships.csv" in content
