"""Command-line interface for the European fsQCA research pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from euro_fsqca.config import load_config
from euro_fsqca.data.io import read_table, write_table
from euro_fsqca.data.schema import schema_report
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
