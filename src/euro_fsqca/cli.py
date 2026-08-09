"""Command-line interface for the European fsQCA research pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from euro_fsqca.analysis.constructs import write_construct_diagnostics
from euro_fsqca.config import load_config
from euro_fsqca.data.harmonisation import build_exclusion_log, harmonisation_report
from euro_fsqca.data.io import read_table, write_table
from euro_fsqca.data.mapping import (
    MappingValidationError,
    load_variable_mapping,
    validate_variable_mapping,
    write_mapping_coverage,
)
from euro_fsqca.data.provenance import ManifestValidationError, raise_for_manifest_errors
from euro_fsqca.data.provenance import validate_manifest as validate_source_manifest
from euro_fsqca.data.schema import schema_audit_from_manifest, schema_report
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import run_analysis

app = typer.Typer(no_args_is_help=True, help="European firm-innovation fsQCA research pipeline.")


@app.command()
def inspect(
    input: Annotated[Path, typer.Option("--input", help="Input microdata file.")],
    output: Annotated[Path, typer.Option("--output")] = Path("results/schema.csv"),
) -> None:
    """Inspect a microdata file and write a privacy-safe schema report."""
    frame = read_table(input)
    write_table(schema_report(frame), output)
    typer.echo(f"Schema written to {output}")


@app.command()
def demo(
    output: Path = Path("data/processed/demo_raw.csv"),
    n: int = 6000,
    seed: int = 42,
) -> None:
    """Generate synthetic data to exercise the complete pipeline."""
    frame = generate_demo(n=n, seed=seed)
    write_table(frame, output)
    typer.echo(f"Synthetic demo data written to {output}")


@app.command("validate-data")
def validate_data(
    manifest: Annotated[Path, typer.Option("--manifest")] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option("--root")] = Path("data/raw"),
) -> None:
    """Validate source files recorded in the data manifest."""
    try:
        report = validate_source_manifest(manifest, root=root)
        raise_for_manifest_errors(report)
    except ManifestValidationError as exc:
        typer.echo(f"Data validation failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Data validation passed: {len(report.entries)} source files checked")


@app.command("schema-audit")
def audit_schema(
    manifest: Annotated[Path, typer.Option("--manifest")] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option("--root")] = Path("data/raw"),
    output: Annotated[Path, typer.Option("--output")] = Path("outputs/data/schema_audit.csv"),
    max_values: Annotated[int, typer.Option("--max-values", min=1)] = 20,
) -> None:
    """Compare schemas across all source files recorded in the manifest."""
    frame = schema_audit_from_manifest(manifest, raw_root=root, max_values=max_values)
    write_table(frame, output)
    typer.echo(f"Schema audit written to {output}")


@app.command("validate-mapping")
def validate_mapping(
    mapping: Annotated[Path, typer.Option("--mapping")] = Path("configs/wbes_variable_map.yml"),
    output: Annotated[Path, typer.Option("--output")] = Path("outputs/data/mapping_coverage.csv"),
    require_main_ready: Annotated[bool, typer.Option("--require-main-ready")] = False,
) -> None:
    """Validate WBES variable mappings and write construct coverage."""
    try:
        mappings = load_variable_mapping(mapping)
        report = validate_variable_mapping(mappings, require_main_ready=require_main_ready)
    except MappingValidationError as exc:
        typer.echo(f"Mapping validation failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    write_mapping_coverage(mappings, output)
    if report.errors:
        for error in report.errors:
            typer.echo(f"Mapping validation warning: {error}", err=True)
        if require_main_ready:
            raise typer.Exit(1)
    typer.echo(f"Mapping coverage written to {output}")


@app.command("check-harmonisation")
def check_harmonisation(
    input: Annotated[Path, typer.Option("--input", help="Harmonised analytical table.")],
    report_output: Annotated[Path, typer.Option("--report-output")] = Path(
        "outputs/data/harmonisation_report.csv"
    ),
    exclusion_output: Annotated[Path, typer.Option("--exclusion-output")] = Path(
        "outputs/data/exclusion_log.csv"
    ),
) -> None:
    """Write harmonisation diagnostics and an exclusion-log template."""
    frame = read_table(input)
    write_table(harmonisation_report(frame), report_output)
    write_table(build_exclusion_log(frame, []), exclusion_output)
    typer.echo(f"Harmonisation report written to {report_output}")
    typer.echo(f"Exclusion log written to {exclusion_output}")


@app.command("construct-diagnostics")
def diagnose_constructs(
    input: Annotated[Path, typer.Option("--input", help="Pre-calibration table.")],
    config: Annotated[Path, typer.Option("--config")] = Path("configs/analysis.yml"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("outputs/constructs"),
) -> None:
    """Write pre-calibration construct diagnostics."""
    frame = read_table(input)
    analysis_config = load_config(config)
    write_construct_diagnostics(frame, config=analysis_config, output_dir=output_dir)
    typer.echo(f"Construct diagnostics written to {output_dir}")


@app.command()
def run(
    input: Annotated[Path, typer.Option("--input", help="Canonical analysis table.")],
    config: Annotated[Path, typer.Option("--config")] = Path("configs/analysis.yml"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("results/main"),
) -> None:
    """Run the configured fsQCA analysis."""
    frame = read_table(input)
    analysis_config = load_config(config)
    summary = run_analysis(
        frame,
        config=analysis_config,
        config_path=config,
        output_dir=output_dir,
    )
    typer.echo(f"Analysis complete: {output_dir}")
    typer.echo(f"Complete calibrated cases: {summary['n_complete_calibrated']}")


if __name__ == "__main__":
    app()
