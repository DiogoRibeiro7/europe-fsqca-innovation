from __future__ import annotations

from pathlib import Path


def test_r_environment_setup_script_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "r" / "setup_renv.R"
    content = script.read_text(encoding="utf-8")

    assert "required_packages <- c(\"renv\", \"QCA\", \"yaml\")" in content
    assert "--install" in content


def test_r_environment_docs_reference_crosscheck() -> None:
    root = Path(__file__).resolve().parents[1]
    content = (root / "r" / "README.md").read_text(encoding="utf-8")

    assert "qca_crosscheck.R" in content
    assert "calibrated_memberships.csv" in content


def test_r_script_reads_thresholds_from_the_analysis_configuration() -> None:
    root = Path(__file__).resolve().parents[1]
    content = (root / "r" / "qca_crosscheck.R").read_text(encoding="utf-8")

    # Thresholds must never be hard-coded: they come from the shared YAML.
    assert "yaml::yaml.load_file(config_path)" in content
    assert "incl_cut <- threshold(\"consistency_cutoff\"" in content
    assert "incl.cut = incl_cut" in content
    assert "dir.exp" in content


def test_r_script_exports_structured_solution_terms() -> None:
    root = Path(__file__).resolve().parents[1]
    content = (root / "r" / "qca_crosscheck.R").read_text(encoding="utf-8")

    # The machine-readable interface is a term table, not captured console text.
    assert 'write.csv(terms, file.path(output_dir, "solution_terms.csv")' in content
    assert "raw_coverage = as.numeric" in content
    assert "unique_coverage = as.numeric" in content
