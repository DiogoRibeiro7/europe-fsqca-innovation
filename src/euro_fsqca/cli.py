"""Command-line interface for the European fsQCA research pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from euro_fsqca.config import load_config
from euro_fsqca.data.io import read_table, write_table
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
