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


def test_renv_lockfile_pins_the_canonical_engine() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "renv.lock").read_text(encoding="utf-8"))

    # The published solution must be attributable to a known engine version.
    assert lock["R"]["Version"].startswith("4.")
    packages = lock["Packages"]
    assert "QCA" in packages
    assert packages["QCA"]["Version"]
    assert "yaml" in packages
    # QCA depends on admisc; a lockfile without it would not restore.
    assert "admisc" in packages


def test_renv_activation_is_committed_and_library_is_not() -> None:
    root = Path(__file__).resolve().parents[1]

    assert (root / ".Rprofile").exists()
    assert (root / "renv" / "activate.R").exists()
    ignored = (root / ".gitignore").read_text(encoding="utf-8")
    assert "renv/library/" in ignored
