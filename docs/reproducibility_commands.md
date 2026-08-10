# Reproducibility Commands

Run commands from the repository root after `poetry install`.

## Local Quality Checks

```bash
make lint
make typecheck
make test
make check
```

## Study Specification

```bash
make validate-spec
```

This validates `configs/research_spec.yml` against the analysis configuration and regional taxonomy.

## Synthetic Pipeline Check

```bash
make run-demo
```

The synthetic run verifies the computational pipeline only. Do not cite its outputs as empirical findings.

## Empirical Data Checks

These commands require licensed WBES source files under `data/raw/` and a completed analytical table at `data/processed/wbes_eu27_analysis.csv`.

```bash
make validate-data
make schema-audit
make validate-mapping
make check-harmonisation
make construct-diagnostics
make calibration-diagnostics
make run-main
```

The default input and output paths can be overridden, for example:

```bash
make run-main ANALYSIS_INPUT=data/processed/custom.csv MAIN_RESULTS=results/custom
```

## Full Synthetic Recheck

```bash
make repro-demo
```

This validates the study specification, runs the synthetic pipeline, and executes the local quality gates.
