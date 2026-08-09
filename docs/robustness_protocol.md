# Robustness Protocol

## Threshold sensitivity

Sweep combinations of:

- raw consistency cutoff
- PRI cutoff
- frequency cutoff

For every specification, store the conservative and parsimonious solution expressions.

A simple stability score for a solution expression is its frequency across admissible specifications.

String frequency is not enough for calibration sensitivity. Also record signed-literal Jaccard similarity against the main result.

## Calibration sensitivity

Perturb full-inclusion and full-exclusion anchors around the fixed crossover. Do not move anchors so far that the semantic meaning of the fuzzy set changes.

Classify structural changes as `same_configuration`, `one_added_condition`, `one_removed_condition`, `polarity_change`, or `unrelated_configuration`.

## Regional robustness

1. Primary three-bloc taxonomy
2. Four-bloc alternative taxonomy
3. Where sample sizes permit, country leave-one-out checks within each macroregion

## Outcome asymmetry

Always rerun the full sufficiency analysis for `~INN`; never infer low-innovation configurations by simply negating high-innovation solutions.

## Survey timing

If the final EU-27 release combines surveys collected across materially different periods, record survey year and pandemic timing. Conduct restricted-period or timing-stratified analyses where the metadata permit this.

## Cross-software validation

Before submission, compare publication solutions and fit parameters with the CRAN `QCA` package. Any discrepancy should be resolved before interpretation.
