# Necessity Analysis

Necessity diagnostics evaluate each condition and its negation for `INN`. The negated outcome is analysed in the same pipeline branch as the sufficiency analysis.

## Output

Each group folder contains `necessity.csv` with:

- condition;
- negation flag;
- display label;
- complete-case count;
- weighted flag, recording whether survey weights were applied;
- necessity consistency;
- necessity coverage;
- triviality flag.

## Interpretation

Do not classify a condition as necessary from one threshold alone. High consistency with low coverage can indicate trivial necessity and needs inspection of the empirical distribution.

Necessity is evaluated under the primary estimand, so it inherits the weighting
choice of the solution it accompanies:

```text
Cons_w(X <= Y) = sum_i w_i * min(X_i, Y_i) / sum_i w_i * Y_i
```

Compare necessity results across Europe and each macroregion using the same calibrated memberships.
