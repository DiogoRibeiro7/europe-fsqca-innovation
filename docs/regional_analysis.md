# Regional Analysis

The main regional comparison uses common Europe-wide calibration anchors. Regions are not recalibrated separately for the primary analysis.

## Main Groups

- North/West;
- South;
- Central/East.

## Output

`regional_comparison.csv` is generated at the run output root. It records:

- region;
- number of cases;
- relative prevalence;
- threshold settings;
- conservative and parsimonious solutions;
- number of positive truth-table rows;
- whether regional solutions match Europe-wide solutions.

Each regional folder also contains the same truth table, diagnostics, solution, and term files as the Europe-wide folder.

## Interpretation

A missing regional configuration is not evidence that a mechanism cannot operate in that region. First check whether the configuration is empirically available and whether sample size is adequate.
