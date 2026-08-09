# Reproducibility

## Environment

- Python 3.11–3.13
- Poetry dependency management
- ruff linting
- mypy static checking
- pytest tests
- optional R cross-check

## Randomness

Only the synthetic demonstration uses random generation and requires an explicit seed. Empirical analysis must be deterministic given the same input microdata and configuration.

## Provenance

A submission run should archive:

- git commit SHA
- analysis YAML
- regional taxonomy YAML
- variable map
- schema report
- aggregate sample-flow table
- calibration anchors
- truth tables
- all solution tables
- robustness grid

Do not archive restricted raw microdata in the public repository.
