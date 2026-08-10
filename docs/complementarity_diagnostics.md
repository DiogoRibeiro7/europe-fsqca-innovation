# Configurational Complementarity and Substitution

Counting how often two conditions appear together in solution terms measures **co-occurrence**. It is not evidence of complementarity, and earlier versions of this repository reported it as if it were. Three separate outputs are now written, with three different claims attached.

## 1. `condition_cooccurrence.csv` — descriptive only

Source, condition pair, polarity of each condition, pair type, number of sufficient terms in which the pair appears.

This is bookkeeping over solution terms. It establishes neither economic complementarity nor a causal interaction effect, and it must not be described as either.

## 2. `complementarity.csv` — the actual test

For every condition pair the pipeline compares the sufficiency of the conjunction with the sufficiency of each condition alone, and with the sufficiency of the disjunction:

- `consistency_left`, `consistency_right` — each condition alone;
- `consistency_conjunction` — `A*B` under the minimum t-norm;
- `consistency_disjunction` — `A+B` under the maximum s-norm;
- `conjunctural_gain` — `Cons(A*B) - max(Cons(A), Cons(B))`;
- `coverage_cost` — the coverage given up by requiring both;
- `relation` — the classification.

`relation` takes one of:

| Value | Meaning |
| --- | --- |
| `complements` | Neither condition alone reaches the sufficiency threshold, the conjunction does, and the gain exceeds the margin. |
| `substitutes` | Each condition alone reaches the threshold and so does their union, so either one suffices. |
| `conjunctural_gain_without_sufficiency` | The conjunction improves on both parts but still falls short of sufficiency. |
| `independent` | No material conjunctural gain. |
| `insufficient_evidence` | Fewer relevant cases than `min_relevant_cases`. |

The test is computed with the analysis weights of the primary estimand, so the statement refers to the same population as the solution it accompanies.

## 3. `substitutability.csv` — substitution inside the solution

Two intermediate-solution terms that agree on every literal except one, where each holds a *different* condition, identify substitution within a shared context: given that context, either condition produces the outcome. The file reports the shared context, the two interchangeable literals, and the size of the context they share.

This is the configurational counterpart of the pairwise test: the pairwise test asks whether two conditions are complements or substitutes in general, and this one asks where the solution itself shows one standing in for the other.

## Interpretation

All three are conditional on the calibration and the truth-table thresholds. Read them against `threshold_sensitivity.csv`, `calibration_sensitivity.csv` and `estimand_sensitivity.csv` before making any claim in the manuscript.
