# Portability Analysis

Portability evaluates whether a configuration identified in one region appears and remains associated with `INN` in another region. Target regions are not refit for this test.

## Distinct Questions

1. Is the source configuration empirically present in the target region?
2. When present, does it retain high consistency and coverage with `INN`?

These are separate failure modes. A configuration can be rare in the target region, or it can be present but weakly associated with the outcome.

## Outputs

The pipeline writes:

- `portability.csv`: Europe-wide conservative terms evaluated by region.
- `portability_directed.csv`: directed source-region to target-region checks.
- `portability_matrix.csv`: region-pair consistency matrix.
- `portability_network.csv`: network-ready source, target, weight, availability, and case-count data.

## Metrics

- `available_cases`: target-region establishments with configuration membership above `0.5`.
- `availability`: share of target-region establishments above that threshold.
- `consistency`: sufficiency consistency in the target region.
- `coverage`: sufficiency coverage in the target region.
- `contradiction_rate`: relevant target cases with outcome membership at or below `0.5`.

Portability is directed: `A -> B` is not assumed to equal `B -> A`.
