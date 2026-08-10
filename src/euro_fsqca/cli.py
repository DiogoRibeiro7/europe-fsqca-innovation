"""Command-line interface for the European fsQCA research pipeline."""

from pathlib import Path
from typing import Annotated

import typer

from euro_fsqca.analysis.calibration import write_calibration_diagnostics
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
from euro_fsqca.data.schema import (
    schema_artifacts_from_manifest,
    schema_report,
    variable_coverage_from_manifest,
)
from euro_fsqca.demo import generate_demo
from euro_fsqca.pipeline import run_analysis
from euro_fsqca.readiness import assess_readiness, readiness_blockers
from euro_fsqca.spec import load_research_spec, validate_research_spec

app = typer.Typer(no_args_is_help=True, help="European firm-innovation fsQCA research pipeline.")


@app.command()
def inspect(
    input: Annotated[Path, typer.Option(help="Input microdata file.", is_flag=False)],
    output: Annotated[Path, typer.Option(is_flag=False)] = Path("results/schema.csv"),
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
    manifest: Annotated[Path, typer.Option(is_flag=False)] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option(is_flag=False)] = Path("data/raw"),
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
    manifest: Annotated[Path, typer.Option(is_flag=False)] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option(is_flag=False)] = Path("data/raw"),
    output: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "outputs/data/schema_audit.csv"
    ),
    max_values: Annotated[int, typer.Option(min=1, is_flag=False)] = 20,
) -> None:
    """Compare schemas across all source files recorded in the manifest.

    Variable and value labels are read from Stata and SPSS sources, because a
    WBES variable name alone does not identify what was asked.
    """
    paths = schema_artifacts_from_manifest(
        manifest, raw_root=root, output_dir=output.parent, max_values=max_values
    )
    for name, path in paths.items():
        typer.echo(f"Schema {name} written to {path}")


@app.command("variable-audit")
def variable_audit(
    manifest: Annotated[Path, typer.Option(is_flag=False)] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option(is_flag=False)] = Path("data/raw"),
    output: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "outputs/data/variable_coverage.csv"
    ),
    min_non_missing_share: Annotated[float, typer.Option(min=0.0, max=1.0, is_flag=False)] = 0.5,
) -> None:
    """Rank source variables by comparable coverage across country releases.

    Run this before defining conditions. Constructs should follow from the
    variables that are actually comparable EU-wide, not the other way round.
    """
    frame = variable_coverage_from_manifest(
        manifest, raw_root=root, min_non_missing_share=min_non_missing_share
    )
    write_table(frame, output)
    usable = int((frame["comparability"] == "comparable_all_countries").sum()) if len(frame) else 0
    typer.echo(f"Variable coverage written to {output}")
    typer.echo(f"Variables comparable across every country release: {usable}")


@app.command()
def readiness(
    config: Annotated[Path, typer.Option(is_flag=False)] = Path("configs/analysis.yml"),
    mapping: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "configs/wbes_variable_map.yml"
    ),
    manifest: Annotated[Path, typer.Option(is_flag=False)] = Path("data/manifest.csv"),
    root: Annotated[Path, typer.Option(is_flag=False)] = Path("data/raw"),
    output: Annotated[Path, typer.Option(is_flag=False)] = Path("outputs/readiness.csv"),
) -> None:
    """Report what stands between this repository and an empirical run."""
    report = assess_readiness(
        config_path=config,
        mapping_path=mapping,
        manifest_path=manifest,
        raw_root=root,
    )
    write_table(report, output)
    for _, row in report.iterrows():
        typer.echo(f"[{row['status'].upper():7}] {row['check']}: {row['detail']}")
    blockers = readiness_blockers(report)
    typer.echo(f"Readiness report written to {output}")
    if blockers:
        typer.echo(f"{len(blockers)} fatal blockers remain before an empirical run", err=True)
        raise typer.Exit(1)
    typer.echo("No fatal blockers: an empirical run is possible")


@app.command("validate-mapping")
def validate_mapping(
    mapping: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "configs/wbes_variable_map.yml"
    ),
    output: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "outputs/data/mapping_coverage.csv"
    ),
    require_main_ready: bool = typer.Option(False, "--require-main-ready"),
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


@app.command("validate-spec")
def validate_spec(
    spec: Annotated[Path, typer.Option(is_flag=False)] = Path("configs/research_spec.yml"),
) -> None:
    """Validate the study-level specification."""
    loaded_spec = load_research_spec(spec)
    report = validate_research_spec(loaded_spec)
    for warning in report.warnings:
        typer.echo(f"Specification warning: {warning}", err=True)
    if report.errors:
        for error in report.errors:
            typer.echo(f"Specification error: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Specification validation passed: {spec}")


@app.command("check-harmonisation")
def check_harmonisation(
    input: Annotated[Path, typer.Option(help="Harmonised analytical table.", is_flag=False)],
    report_output: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "outputs/data/harmonisation_report.csv"
    ),
    exclusion_output: Annotated[Path, typer.Option(is_flag=False)] = Path(
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
    input: Annotated[Path, typer.Option(help="Pre-calibration table.", is_flag=False)],
    config: Annotated[Path, typer.Option(is_flag=False)] = Path("configs/analysis.yml"),
    output_dir: Annotated[Path, typer.Option(is_flag=False)] = Path("outputs/constructs"),
) -> None:
    """Write pre-calibration construct diagnostics."""
    frame = read_table(input)
    analysis_config = load_config(config)
    write_construct_diagnostics(frame, config=analysis_config, output_dir=output_dir)
    typer.echo(f"Construct diagnostics written to {output_dir}")


@app.command("calibration-diagnostics")
def diagnose_calibration(
    input: Annotated[Path, typer.Option(help="Pre-calibration table.", is_flag=False)],
    config: Annotated[Path, typer.Option(is_flag=False)] = Path("configs/analysis.yml"),
    output_dir: Annotated[Path, typer.Option(is_flag=False)] = Path("outputs/calibration"),
) -> None:
    """Write calibration diagnostics for configured fuzzy sets."""
    frame = read_table(input)
    analysis_config = load_config(config)
    write_calibration_diagnostics(frame, config=analysis_config, output_dir=output_dir)
    typer.echo(f"Calibration diagnostics written to {output_dir}")


@app.command()
def run(
    input: Annotated[Path, typer.Option(help="Canonical analysis table.", is_flag=False)],
    config: Annotated[Path, typer.Option(is_flag=False)] = Path("configs/analysis.yml"),
    output_dir: Annotated[Path, typer.Option(is_flag=False)] = Path("results/main"),
    mapping: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "configs/wbes_variable_map.yml"
    ),
    manifest: Annotated[Path, typer.Option(is_flag=False)] = Path("data/manifest.csv"),
    raw_root: Annotated[Path, typer.Option(is_flag=False)] = Path("data/raw"),
    schema_audit: Annotated[Path, typer.Option(is_flag=False)] = Path(
        "outputs/data/schema_audit.csv"
    ),
    unsafe_development_run: bool = typer.Option(
        False,
        "--unsafe-development-run",
        help=(
            "Bypass every readiness blocker. For software development only. "
            "Output produced this way is not evidence and must never be published."
        ),
    ),
) -> None:
    """Run the configured fsQCA analysis.

    The run is gated on empirical readiness. Every blocker must be resolved,
    not merely relabelled: flipping the configuration status to `research`
    clears one check and leaves the rest standing.
    """
    analysis_config = load_config(config)
    report = assess_readiness(
        config_path=config,
        mapping_path=mapping,
        manifest_path=manifest,
        raw_root=raw_root,
        schema_audit_path=schema_audit,
    )
    blockers = readiness_blockers(report)
    if blockers:
        if not unsafe_development_run:
            typer.echo(
                f"Refusing to run: {len(blockers)} readiness blockers remain.", err=True
            )
            for blocker in blockers:
                typer.echo(f"  - {blocker}", err=True)
            typer.echo(
                "Resolve them and re-run, or use --unsafe-development-run for a software "
                "smoke test whose output is not evidence.",
                err=True,
            )
            raise typer.Exit(1)
        typer.echo("=" * 78, err=True)
        typer.echo(
            "UNSAFE DEVELOPMENT RUN: "
            f"{len(blockers)} readiness blockers were bypassed.",
            err=True,
        )
        for blocker in blockers:
            typer.echo(f"  - {blocker}", err=True)
        typer.echo(
            "The output of this run is NOT an empirical result. Do not publish it, "
            "cite it, or copy it into the manuscript.",
            err=True,
        )
        typer.echo("=" * 78, err=True)
    frame = read_table(input)
    summary = run_analysis(
        frame,
        config=analysis_config,
        config_path=config,
        output_dir=output_dir,
    )
    typer.echo(f"Analysis complete: {output_dir}")
    typer.echo(f"Complete calibrated cases: {summary['n_complete_calibrated']}")
    for sample in summary["samples"]:
        typer.echo(
            f"  sample {sample['sample']}: {sample['n_complete_calibrated']} establishments, "
            f"conditions {', '.join(sample['conditions'])}"
        )


if __name__ == "__main__":
    app()
