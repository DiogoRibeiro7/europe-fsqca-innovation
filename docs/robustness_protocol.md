# Robustness Protocol

Every check below is executed by `run_analysis` when `robustness.enabled` is true and writes a named file. A check that the pipeline does not run is not a robustness check.

## Threshold sensitivity

`threshold_sensitivity.csv`. Sweep combinations of the raw consistency cutoff, the PRI cutoff and the frequency cutoff. For every specification, store the conservative and parsimonious expressions, retained rows, contradictory rows and term counts.

Solution-string frequency alone is not enough. Two similarity measures are recorded against the main solution:

- `conservative_similarity` — Jaccard over signed literals;
- `conservative_term_similarity` — Jaccard over whole configuration terms.

The two can diverge sharply. Identical literal pools with different recipes score 1.0 on the first and much lower on the second; report both.

## Calibration sensitivity

`calibration_sensitivity.csv`. Perturb full-inclusion and full-exclusion anchors around the fixed crossover. Do not move anchors so far that the semantic meaning of the fuzzy set changes.

Structural changes are classified as `same_configuration`, `one_added_condition`, `one_removed_condition`, `polarity_change` or `unrelated_configuration`.

## Estimand sensitivity

`estimand_sensitivity.csv`. Re-derive the solution under each configured estimand: unweighted, firm-population weights, and equal-country weights.

This is a substantive comparison, not a nuisance check. The three estimands answer different questions, and disagreement between them is a finding about whose innovation the pooled solution describes.

## Sample omission

Written whenever the grouping column survives into the calibrated table, which is why calibration preserves the design columns:

- `leave_one_country_out.csv`
- `leave_one_sector_out.csv`
- `leave_one_size_class_out.csv`
- `leave_one_survey_period_out.csv`

## Regional robustness

`regional_taxonomy_robustness.csv` re-derives regional solutions under `robustness.alternative_region_scheme` (the four-bloc taxonomy). Regions below the minimum sample size are reported as skipped rather than silently dropped.

The primary three-bloc taxonomy remains the pre-specified design; the alternative exists so that a regional finding can be shown not to depend on where the boundary was drawn.

## Bootstrap robustness

`bootstrap_draws.csv`, `bootstrap_stability.csv` and `bootstrap_term_stability.csv`. Resample calibrated establishments with replacement, rerun truth-table minimisation and record appearance frequencies for whole solutions and for individual terms.

When `survey.strata_column` is configured the resampling is stratified, which reproduces the sampling design instead of treating a stratified sample as a simple random draw. This is a stability diagnostic, not conventional parameter uncertainty.

Use fixed seeds, retain failed replicates with a failure reason, and keep replicate counts small in CI.

## Portability uncertainty

`portability_bootstrap.csv`. Bootstraps both source-solution discovery and target-region evaluation. See `docs/portability_analysis.md`.

## Outcome asymmetry

Always rerun the full sufficiency analysis for `~INN` (`europe_negative_outcome/`); never infer low-innovation configurations by negating high-innovation solutions.

## Survey timing

EU-27 fieldwork ran from 2018 to 2022 and standard innovation questions use a three-year reference window, so respondents in different countries describe different periods and some straddle the pandemic.

`survey_timing.csv` records, per country, the survey years, the implied reference window and the assigned period. Declaring `timing.periods` in the configuration adds the survey period as an omission dimension. Timing is not a caveat to mention in the discussion; it is a design dimension the pipeline carries.

## Analytical sample

`analytical_samples.csv` records, for every declared sample, the establishments and weight mass surviving each inclusion rule and each completeness requirement. A condition asked of only part of the frame changes the population, and the attrition table is what makes that visible.

## Cross-software validation

Before submission, compare publication solutions and fit parameters with the CRAN `QCA` package via `scripts/run_parity.py`. Resolve any discrepancy before interpretation.
