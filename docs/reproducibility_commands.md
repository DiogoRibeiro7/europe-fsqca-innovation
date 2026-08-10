# Reproducibility Commands

Run commands from the repository root after `poetry install`.

## Local Quality Checks

```bash
make lint
make typecheck
make test
make check
```

## Empirical Readiness

```bash
make readiness
```

This reports every blocker standing between the repository and a defensible empirical run, and exits non-zero while any fatal blocker remains. Run it before believing any result.

## Study Specification

```bash
make validate-spec
```

This validates `configs/research_spec.yml` against the analysis configuration, the declared samples and estimands, and the regional taxonomy.

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
make variable-audit
make validate-mapping
make check-harmonisation
make construct-diagnostics
make calibration-diagnostics
make readiness
make run-main
make r-crosscheck
make parity
```

`make variable-audit` ranks source variables by comparable coverage across country releases and should be run *before* the constructs are defined. `make parity` runs the canonical R/QCA engine and compares its solution terms with the Python pipeline's, exiting non-zero on any difference.

`euro-fsqca run` refuses a configuration marked `status: template`. Pass `--allow-template` only for a software smoke test, never for a result.

The default input and output paths can be overridden, for example:

```bash
make run-main ANALYSIS_INPUT=data/processed/custom.csv MAIN_RESULTS=results/custom
```

## Full Synthetic Recheck

```bash
make repro-demo
```

This validates the study specification, runs the synthetic pipeline, and executes the local quality gates.
