# Changelog

## 0.3.0 — 2026-08-10

Redesign around the survey design and the analytical population. This release
changes what the analysis claims, not only how it is computed.

### Added

- Survey-design-aware set theory: weighted consistency, coverage, PRI and
  necessity; weighted and Kish effective-sample-size truth-table frequency.
- Three explicit pooled estimands — unweighted, firm-population weights and
  equal-country weights — reported side by side in `estimand_sensitivity.csv`.
- Intermediate solutions from directional expectations, with core/peripheral
  classification in `core_peripheral.csv`.
- Declared analytical samples with filters and a recorded attrition table, so a
  condition asked of only part of the frame cannot silently change the
  population. `MGT` moved to a restricted extension sample.
- Survey timing carried through calibration: reference-window reporting in
  `survey_timing.csv` and survey-period omission robustness.
- Directed term-level portability with bootstrap intervals and a two-stage
  discovery/transfer bootstrap in `portability_bootstrap.csv`.
- A real complementarity test in `complementarity.csv` and solution-level
  substitution in `substitutability.csv`.
- `euro-fsqca readiness` and `euro-fsqca variable-audit`.
- `scripts/run_parity.py` for automated, term-level Python-R parity.
- Stratified bootstrap, term-level bootstrap stability and term-level solution
  similarity.

### Changed

- **`calibrate_frame` now preserves the design columns.** Weights, strata,
  survey year, sector and size survive calibration; the leave-one-sector-out
  and leave-one-size-class-out checks consequently run instead of silently
  producing nothing.
- R/QCA is now the canonical publication engine. `r/qca_crosscheck.R` reads
  thresholds, conditions and directional expectations from the shared YAML
  configuration and exports structured term-level CSV instead of captured
  console text.
- The pipeline runs the bootstrap and the alternative regional taxonomy that
  the specification promised.
- Regional comparison is term-level, not solution-string equality.
- `portability_matrix.csv` reports the share of source terms that transfer,
  with the consistency distribution, rather than a mean across unrelated terms.
- The net-effect comparison uses the observed outcome with survey weights,
  country, period, sector and size controls and clustered errors.
- `configs/analysis.yml` is marked `status: template`; `euro-fsqca run` refuses
  it without `--allow-template`.
- The synthetic generator produces sampling weights, strata, size classes and
  staggered fieldwork years so the design-aware paths are exercised.

### Renamed

- `anchor_sensitivity.csv` → `calibration_sensitivity.csv` (matching the spec).
- `complementarity_pairs.csv` → `condition_cooccurrence.csv`.
- `fractional_logit.csv` → `net_effect_model.csv`.
- `condition_pair_matrix()` → `condition_cooccurrence()`.
- `fit_fractional_logit()` → `fit_net_effect_model()`.

### Not included

No empirical results. The manifest is empty and every WBES construct mapping is
still unresolved, so this release remains research infrastructure.

## 0.2.0 — 2026-08-10

- Added data provenance, schema audit, mapping validation, and harmonisation checks.
- Added construct, calibration, truth-table, diversity, necessity, complementarity, robustness, and portability diagnostics.
- Added country-level portability, sample omission, bootstrap stability, synthetic scenario checks, and research figures.
- Added generated-table metadata, study-level specification validation, and reproducibility commands.
- Added Python package typing metadata and R validation environment setup.
- Added data-gated manuscript sections, novelty review, internal review, response record, and release report.
- Preserved WBES raw-data separation and did not report synthetic output as evidence.

## 0.1.0 — 2026-08-09

- Added typed Python fsQCA research pipeline.
- Added direct fuzzy-set calibration with explicit anchors.
- Added necessity, sufficiency, PRI, truth-table and Boolean minimisation logic.
- Added pan-European and macroregional analyses.
- Added negated-outcome analysis for causal asymmetry.
- Added configuration portability and heterogeneity diagnostics.
- Added threshold and calibration-anchor sensitivity sweeps.
- Added fractional-logit net-effect comparison.
- Added synthetic end-to-end validation data generator.
- Added WBES schema inspection and variable-mapping workflow.
- Added optional CRAN QCA cross-check script.
- Added LaTeX manuscript scaffold and methodological documentation.
- Added tests and GitHub Actions CI configuration.
