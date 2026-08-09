# Development Audit

Date: 2026-08-09

Scope: current `main` branch after the `v0.1.0` release.

| Component | Current state | Missing work | Scientific risk | Engineering risk | Priority | Action |
| --------- | ------------- | ------------ | --------------- | ---------------- | -------- | ------ |
| Repository structure | Package, configs, docs, tests, paper scaffold, R check script, examples, and staged data folders exist. | No generated `outputs/` tree for formal audit artifacts. | Low for structure; high if users mistake placeholders for completed empirical work. | Low. | High | Keep current structure and add generated-output conventions. |
| Python package | `src/euro_fsqca` contains configuration, data IO, schema reporting, calibration, composites, QCA, analysis, CLI, and synthetic data modules. | More input validation and reporting are needed for real WBES processing. | Medium because empirical assumptions still sit outside verified mappings. | Medium. | High | Extend modules without replacing the current package design. |
| Data directories | `data/raw`, `data/interim`, and `data/processed` exist with `.gitkeep` placeholders. Case-level files are ignored. | Formal source manifest, checksum validation, and missing-source reporting are not yet implemented. | High until source provenance is auditable. | Medium. | High | Add manifest and acquisition checks before real processing. |
| Configuration files | `configs/analysis.yml`, `configs/analysis.demo.yml`, `configs/regions.yml`, and `configs/wbes_variable_map.yml` exist. | Real WBES mappings and empirical calibration anchors remain unresolved. | High because current WBES config is a template. | Medium. | High | Validate mapping states and block empirical runs with unknown mappings. |
| WBES ingestion code | `src/euro_fsqca/data/io.py` reads common table formats; `schema.py` creates privacy-safe schema reports. | No multi-file acquisition manifest or cross-country schema comparison. | High for comparability. | Medium. | High | Add source inventory, checksum checks, and schema comparison. |
| Variable mapping | `configs/wbes_variable_map.yml` lists intended constructs and candidate content. | All source variables are empty and marked as TODO. | High. | Low. | High | Replace placeholders only after release-specific schema audit. |
| Synthetic data generator | `src/euro_fsqca/demo.py` generates 6,000 synthetic firms with known regional recipes for demo runs. | More known-structure scenarios are needed for stronger recovery tests. | Low if clearly labelled; high if reported as evidence. | Low. | Medium | Keep demo and expand synthetic validation. |
| Construct code | `sets/composites.py` supports mean, min, max, and weighted mean with missing-data rules. | Construct validity, country coverage, diagnostics, and alternative operationalisations are incomplete. | High. | Medium. | High | Add construct reports after mapping verification. |
| Calibration code | `sets/calibration.py` implements direct fuzzy calibration and anchor shifting. | Anchor diagnostics and empirical justification reports are incomplete. | High. | Low. | High | Generate calibration diagnostics from configured anchors. |
| fsQCA code | Fuzzy operations, necessity, truth tables, and minimisation exist in `qca/`. | Contradiction diagnostics, richer diversity reports, and stronger minimisation tests are incomplete. | Medium. | Medium. | High | Add diagnostics and analytically checked tests. |
| Regional analysis | `configs/regions.yml` defines macroregional schemes; pipeline runs regional groups with common calibration. | Regional comparison tables and country-level diagnostics are partial. | Medium. | Low. | High | Extend regional outputs and interpretation guards. |
| Portability analysis | `analysis/portability.py` evaluates configured terms across regions. | Directed region-pair, heatmap, network, and country-level outputs are incomplete. | Medium. | Medium. | High | Expand portability outputs without refitting target regions. |
| Sensitivity analysis | Threshold and anchor sweeps exist in `analysis/robustness.py`. | Solution similarity, sample robustness, bootstrap diagnostics, and richer stability summaries are missing. | Medium. | Medium. | High | Add structured robustness modules and tests. |
| R validation code | `r/qca_crosscheck.R` runs independent QCA truth table and minimisation from exported calibrated data. | Machine-readable parity outputs, tolerances, and regional validation reports are missing. | Medium. | Medium. | High | Keep R narrow and add comparison artifacts. |
| Tests | Unit and integration tests cover calibration, fuzzy metrics, truth tables, regional assignment, and the synthetic pipeline. | Real-data paths, acquisition checks, mapping validation, and R parity are not tested. | Medium. | Medium. | High | Add tests as data-foundation features are introduced. |
| Notebooks | No notebook workflow is present. | Optional result notebooks may be useful later. | Low. | Low. | Low | Keep production analysis in modules and scripts. |
| Reports | Example demo outputs exist under `examples/`; generated `results/` are ignored. | Formal generated reports for schema, harmonisation, constructs, calibration, robustness, and parity are missing. | High until empirical work is complete. | Medium. | High | Generate reports from code with metadata. |
| Manuscript files | LaTeX scaffold exists under `paper/` with section files and references. | Generated tables and real empirical results are not integrated. | High if manuscript is treated as complete. | Low. | Medium | Populate only from generated outputs after data foundation is stable. |
| CI | GitHub Actions run Ruff, mypy, and pytest on Python 3.11, 3.12, and 3.13. | R validation is not in CI. | Low for Python; medium for parity. | Low. | Medium | Add optional R job once R dependency control is in place. |
| Documentation | Research design, data contract, calibration, robustness, reproducibility, sources, regional taxonomy, and mapping docs exist. | Data source manifest, schema audit, outcome definition, parity, novelty, review, and release reports are missing. | Medium. | Low. | High | Fill documentation in the same order as implementation. |

## Test Evidence

Local checks after the public release:

```bash
poetry run ruff check .
poetry run mypy src tests
poetry run pytest
```

Current result: all passed locally. GitHub CI passed on Python 3.11, 3.12, and 3.13 for the Zenodo metadata commit before the `v0.1.0` release.

## Placeholder And Synthetic Paths

The following paths must not be treated as empirical evidence:

- `configs/wbes_variable_map.yml`: mapping worksheet with empty source-variable lists.
- `configs/analysis.yml`: WBES analysis template with placeholder anchors.
- `configs/analysis.demo.yml`: synthetic demonstration configuration.
- `src/euro_fsqca/demo.py`: synthetic data generator.
- `examples/demo_summary.json`: generated from synthetic data.
- `examples/demo_europe_solutions.csv`: generated from synthetic data.
- `examples/demo_portability.csv`: generated from synthetic data.

## Python And R Boundary

Python is the main implementation layer for ingestion, validation, harmonisation, construct construction, calibration, QCA metrics, regional comparison, portability, robustness, tables, figures, and reproducibility.

R is reserved for independent QCA validation using exported calibrated data and explicit exchange files. The current R script does not duplicate the full Python pipeline.
