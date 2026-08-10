# QCA Formulas

This repository uses fuzzy-set operations with explicit numerical tolerances in tests.

## Basic Operations

For membership scores in `[0, 1]`:

- Negation: `~X = 1 - X`
- Intersection: `X*Y = min(X, Y)`
- Union: `X + Y = max(X, Y)`

## Sufficiency

For configuration membership `X`, outcome membership `Y` and case weight `w`:

```text
consistency = sum(w * min(X, Y)) / sum(w * X)
coverage    = sum(w * min(X, Y)) / sum(w * Y)
```

PRI is calculated as:

```text
PRI = (sum(w * min(X, Y)) - sum(w * min(X, 1 - Y))) /
      (sum(w * X)         - sum(w * min(X, 1 - Y)))
```

With `w = 1` these reduce to the conventional case-oriented estimators. Undefined divisions are reported as missing numeric values.

## Necessity

```text
consistency = sum(w * min(X, Y)) / sum(w * Y)
coverage    = sum(w * min(X, Y)) / sum(w * X)
```

## Weights and estimands

WBES is a stratified probability sample, so `w` is a design choice that has to be stated, not a detail. Three estimands are supported:

| Estimand | `w` | Claim |
| --- | --- | --- |
| `unweighted` | `1` | About the sampled establishments. |
| `firm_population` | published sampling weight | About the establishment population in the frame. |
| `equal_country` | weight rescaled so each country contributes equal aggregate weight | About countries rather than about the largest member states. |

Weights are rescaled to sum to the number of cases so that weighted frequencies stay on the same scale as case counts. Consistency and coverage are ratios and so are invariant to that rescaling; row frequency is not, which is why the basis below matters.

## Truth Tables

Rows are assigned by crisp presence above `0.5`. Row fit is still calculated from the fuzzy membership in the full row configuration, using the same weights as the solution.

Each row reports three measures of evidence:

- `frequency` — sampled establishments in the row;
- `weighted_frequency` — the row's weight mass, `sum(w)`;
- `effective_frequency` — Kish's effective sample size within the row, `sum(w)^2 / sum(w^2)`.

Row inclusion in the canonical analysis is decided by `frequency` alone: the number of sampled establishments. Weight mass and effective sample size are reported for inspection but do not gate a reported solution, because a non-standard `n.cut` would not be comparable with the literature and could not be reproduced by the canonical R engine. The exploratory comparison across all three rules is written only when `robustness.weighted_truth_table_exploration` is enabled. See `docs/qca_engine_policy.md`.

A row is positive when it meets:

- the frequency cutoff on the configured basis;
- the sufficiency consistency cutoff;
- the PRI cutoff when PRI is available.

An observed row is flagged as contradictory when it has enough evidence but fails the consistency rule and is not positive.

## Solution types

- **Conservative (complex)** — positive rows only, no logical remainders.
- **Parsimonious** — unobserved rows treated as don't-cares, observed negative rows preserved.
- **Intermediate** — only *easy* counterfactuals are used. Starting from each parsimonious implicant, a dropped literal is restored whenever the row that licensed dropping it is an unobserved row in which the condition takes the value opposite to its declared directional expectation. Conditions declared `either` impose no restriction. The result is a superset of the parsimonious and a subset of the conservative solution.

A literal in the intermediate solution is **core** when it also survives into the parsimonious solution, and **peripheral** otherwise. Core/peripheral claims are only available because the intermediate solution exists; they cannot be made from a conservative/parsimonious pair alone.

The CRAN `QCA` package is the canonical engine for publication truth tables and minimisation. See `docs/python_r_validation.md`.
