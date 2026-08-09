# Calibration Protocol

## Principle

Calibration is part of measurement, not a mechanical rescaling step. Every fuzzy set must have an interpretable meaning and three documented anchors:

- full exclusion
- crossover / maximum ambiguity
- full inclusion

The primary analysis uses the same anchors for every European firm.

## Direct method

For a monotone set, raw observations are transformed by a piecewise logistic function. The crossover maps to 0.5 and the two outer anchors map to `1-idm` and `idm`, respectively. The default `idm` is 0.95.

This allows asymmetric distances between exclusion, crossover, and inclusion while preserving the substantive anchors.

## Rules

1. Do not use 5th/50th/95th percentiles by default.
2. Prefer external benchmarks or theory when available.
3. If empirical percentiles are necessary, justify why those percentiles correspond to set membership.
4. Do not create artificial fuzziness for genuinely dichotomous concepts.
5. Avoid exact 0.5 memberships in final case-level data where possible; inspect ambiguous cases explicitly.
6. Do not calibrate independently by macroregion in the main comparison.

## Sensitivity

The robustness design should perturb outer anchors while holding the substantive crossover fixed. Report whether core solution terms survive reasonable perturbations.

The current Python threshold sweep varies truth-table thresholds. Anchor perturbation is exposed in the package and should be activated after the empirical WBES anchors are frozen.
