# QCA Formulas

This repository uses fuzzy-set operations with explicit numerical tolerances in tests.

## Basic Operations

For membership scores in `[0, 1]`:

- Negation: `~X = 1 - X`
- Intersection: `X*Y = min(X, Y)`
- Union: `X + Y = max(X, Y)`

## Sufficiency

For configuration membership `X` and outcome membership `Y`:

```text
consistency = sum(min(X, Y)) / sum(X)
coverage = sum(min(X, Y)) / sum(Y)
```

PRI is calculated as:

```text
PRI = (sum(min(X, Y)) - sum(min(X, 1 - Y))) /
      (sum(X) - sum(min(X, 1 - Y)))
```

Undefined divisions are reported as missing numeric values.

## Necessity

For condition membership `X` and outcome membership `Y`:

```text
consistency = sum(min(X, Y)) / sum(Y)
coverage = sum(min(X, Y)) / sum(X)
```

## Truth Tables

Rows are assigned by crisp presence above `0.5`. Row fit is still calculated from the fuzzy membership in the full row configuration.

A row is positive when it meets:

- minimum frequency;
- sufficiency consistency cutoff;
- PRI cutoff when PRI is available.

An observed row is flagged as contradictory when it has enough cases but fails the consistency rule and is not positive.
