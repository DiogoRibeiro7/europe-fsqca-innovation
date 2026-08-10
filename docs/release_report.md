# Release Report

Release target: `v0.2.0`  
Report date: 2026-08-10

## Scope

This release packages the research scaffold for a European firm-level fsQCA study of innovation. It is ready for reproducible synthetic validation and empirical execution once licensed WBES data and final research decisions are supplied locally.

## Included Capabilities

- Source-file provenance manifest and validation.
- Multi-file schema audit.
- WBES variable mapping worksheet and validation.
- Harmonisation diagnostics and exclusion logging.
- Construct and calibration diagnostics.
- Truth-table diagnostics, contradictions, diversity, necessity, minimisation, negated-outcome analysis, and fractional-logit comparison.
- Regional comparison, directed portability, country portability, complementarity, threshold sensitivity, anchor sensitivity, omission, and bootstrap diagnostics.
- Python-R validation workflow.
- Generated table metadata and SVG figure helpers.
- Study-level specification validation.
- Data-gated manuscript scaffold.
- Novelty review, internal review, and response record.

## Validation

Local checks run for this release-prep branch:

- `make validate-spec`
- `make repro-demo`
- `poetry run ruff check .`
- `poetry run mypy src tests`
- `poetry run pytest`

The R environment check reports missing local R packages until `make r-setup` is run.

## Current Empirical Status

No substantive WBES results are included. The repository still requires:

- licensed EU-27 WBES files under `data/raw/`;
- validated checksums in `data/manifest.csv`;
- exact survey-release variable mapping in `configs/wbes_variable_map.yml`;
- documented construct transformations;
- justified calibration anchors in `configs/analysis.yml`;
- generated empirical tables, figures, R validation outputs, and manuscript results.

## Release Guardrails

- Do not commit raw or derived case-level WBES files.
- Do not alter regional membership after inspecting empirical solutions.
- Do not interpret synthetic outputs as evidence.
- Do not populate manuscript results without generated table metadata.
