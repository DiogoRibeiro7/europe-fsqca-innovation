# Diversity Diagnostics

For six binary truth-table conditions, the logical space contains `2^6 = 64` possible configurations.

The pipeline writes:

- `diversity_diagnostics.csv`;
- `difficult_rows.csv`;
- `contradictory_rows.csv`.

These files show observed configurations, unobserved configurations, logical remainders, contradictory rows, and rows near decision thresholds.

Logical remainders are not automatically treated as equally plausible counterfactuals. They require theoretical review before interpretation.
