# Portability Analysis

Portability asks whether a configuration identified in one region appears, and remains sufficient for `INN`, in another region. Target regions are not refit for this test, and the calibration is the same Europe-wide scale everywhere.

The **unit of portability is the configuration term**, not the solution string. Two regional solutions can share every literal and still propose different recipes, so solution-string comparison answers the wrong question.

## Distinct failure modes

1. **Availability** — is the source configuration empirically present in the target region at all?
2. **Fit** — when present, does it retain high consistency and coverage with `INN`?
3. **Stability** — is it a stable feature of the source region, or an artefact of one sample?

These fail independently. A configuration can be rare in the target region, present but weakly associated with the outcome, or simply not a robust feature of the source region.

## Direction

Portability is directed. `C_south -> north_west` is a different claim from `C_north_west -> south`, and the two are reported separately throughout.

## Outputs

| File | Content |
| --- | --- |
| `portability.csv` | Europe-wide conservative terms evaluated in every region. |
| `portability_directed.csv` | Directed source-region to target-region evaluation, one row per term and target, with bootstrap confidence intervals. |
| `portability_matrix.csv` | Region-pair aggregate. |
| `portability_network.csv` | Network-ready source, target, term, weight, interval, availability and case counts. |
| `portability_bootstrap.csv` | Source-solution discovery frequency and target consistency distribution. |
| `country_portability.csv` | Country-level evaluation of European and regional configurations. |

## Term-level metrics

- `available_cases` — target establishments with configuration membership above `0.5`;
- `availability` — their share of the target region;
- `consistency`, `coverage`, `pri` — sufficiency fit under the primary estimand;
- `consistency_ci_lower`, `consistency_ci_upper` — percentile bootstrap interval over resampled target cases;
- `contradiction_rate` — relevant target cases with outcome membership at or below `0.5`;
- `portable` — clears the consistency threshold with at least `min_available_cases` relevant cases;
- `portable_lower_bound` — the *lower* interval bound still clears the threshold, which is the conservative reading.

## The region-pair aggregate

Averaging consistency across structurally different terms has no clean substantive meaning: the mean of a strong recipe and a weak, unrelated recipe describes neither. `portability_matrix.csv` therefore reports:

- `share_portable` — the headline: the share of the source region's terms that clear the rule in the target region;
- `n_terms`, `n_portable` — the counts that share rests on;
- `consistency_median`, `consistency_min`, `consistency_max` — the distribution, not a single collapsed number;
- `consistency_availability_weighted_mean` — a mean weighted by how many target establishments each term actually reaches;
- `mean_available_cases`.

Report `share_portable` with its term count. Never report a bare mean consistency for a region pair.

## Two-stage bootstrap

`portability_bootstrap.csv` separates the two uncertainties that matter:

- `discovery_frequency` — how often the source region's own solution contains this configuration when the source region is resampled. A term found in 30% of replicates is not a finding about that region.
- `consistency_mean`, `consistency_ci_lower`, `consistency_ci_upper`, `portable_frequency` — how the term performs in a resampled target region.

A configuration is only worth calling portable when it is both stably discovered and stably transferred.

## Country-level diagnostics

Country diagnostics do not run standalone country QCA. They evaluate configurations learned from Europe or from the relevant region, and they flag weak samples rather than hiding them.
