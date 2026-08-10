# QCA Engine Policy

## Authority

The CRAN `QCA` package is the **canonical publication engine** for this study.
Truth tables, Boolean minimisation and the reported solution metrics come from
it. Python does everything around it.

| Layer | Responsibility |
| --- | --- |
| Python | acquisition, ingestion, harmonisation, measurement, calibration, diagnostics, orchestration, sensitivity analysis, portability, visualisation |
| R (CRAN `QCA`) | canonical truth tables, conservative, parsimonious and intermediate minimisation, published solution metrics |
| Python | independent numerical validation of those results |

### Why not the Python minimiser

The repository contains a transparent SymPy sum-of-products minimiser. It is
correct, it is tested, and it is **not** the authority for a substantive paper.

A bespoke minimiser used as the publication engine puts the burden of proving
the implementation on the paper. That burden is avoidable: `QCA` is mature,
widely reviewed, and the implementation reviewers already know. The value this
repository adds is upstream of minimisation, in getting the measurement and the
sample right, and downstream of it, in portability and sensitivity.

The Python minimiser stays, in one role: recomputing the canonical result
independently so that a disagreement between the two engines is detected rather
than assumed away. See `docs/python_r_validation.md`.

## Row inclusion counts cases

Truth-table row existence in the canonical analysis uses the **standard case
frequency**: the number of sampled establishments assigned to the row.

This is a deliberate reversal of an earlier decision in this repository.

The argument for weighting row inclusion is real. WBES over-samples some
strata, weight mass is not evidence, and Kish's effective sample size discounts
exactly that inflation. But making it the primary rule would mean:

- the frequency threshold no longer means what `n.cut` means in every published
  fsQCA study, so the number is not comparable with the literature;
- the canonical R engine cannot reproduce it, which breaks parity on the one
  quantity parity exists to check;
- reviewers would be asked to accept a non-standard inclusion rule *and* a
  non-standard set of results at the same time.

A study that departs from the standard procedure should do so on one axis, with
a clear argument, not on several at once by default. The design question is
better answered where it belongs: in the sensitivity analysis.

## Where weighting does belong

Survey weights are used to test whether the discovered configurations survive
the design, not to discover them:

- **`estimand_sensitivity.csv`** — the solution re-derived under unweighted,
  firm-population and equal-country weights.
- **Weighted set metrics** — every reported configuration carries unweighted
  and weighted consistency and coverage side by side, so the reader can see
  whether its fit depends on the design.
- **Stratified bootstrap** — resampling respects the strata when they are
  available.

The scientific question is: *does the empirical fit of the canonical
configurations change when the survey design or the country weighting changes?*
That is answerable, and it is more informative than a weighted truth table.

## The exploratory appendix

`robustness.weighted_truth_table_exploration` rebuilds the truth table on all
three bases — case count, weight mass, and effective sample size — and writes
`exploratory/weighted_truth_table_comparison.csv` with a `canonical` flag
marking the case-count rows.

It is off by default in the main configuration. It reports row inclusion under
each rule and nothing else: it never feeds a solution, and no configuration is
reported from it. It exists so the consequences of the design can be inspected
and, if they are large, discussed as a limitation.

## Consequences for the configuration

`truth_table.frequency_basis` no longer exists as a configuration option. The
canonical thresholds are always constructed with case counting. The capability
remains in `TruthTableThresholds` because the exploratory appendix uses it, but
it cannot be reached from the main analysis path.

## Summary

| Question | Answer |
| --- | --- |
| Which engine produces the published solution? | CRAN `QCA` |
| What does the Python minimiser do? | Independent cross-check |
| What determines truth-table row inclusion? | Number of sampled establishments |
| Where are survey weights used? | Fit of discovered configurations, and sensitivity |
| Can a weighted truth table produce a reported solution? | No |
