# Python-R Validation

## Division of authority

R/QCA is the **canonical publication engine** for truth tables and minimisation. Python is the independent numerical cross-check.

| Layer | Responsibility |
| --- | --- |
| Python | acquisition, harmonisation, measurement, calibration, weighting, diagnostics, sensitivity orchestration, visualisation |
| R (CRAN `QCA`) | canonical truth tables, conservative/parsimonious/intermediate minimisation, published solution metrics |
| Python | independent recomputation of the same quantities as a cross-check |

There is no scientific benefit in making a bespoke SymPy minimiser the authority for a substantive paper. Boolean minimisation belongs to a mature, widely reviewed implementation; the value this repository adds is upstream and downstream of it.

## Shared configuration

`r/qca_crosscheck.R` reads the **same YAML analysis configuration** the Python pipeline uses. Conditions, the outcome, `incl.cut`, `pri.cut`, `n.cut` and the directional expectations all come from that file. No threshold is hard-coded in the R script, so the two engines cannot drift apart silently.

```bash
Rscript r/qca_crosscheck.R \
  results/main/calibrated_memberships.csv \
  configs/analysis.yml \
  results/main/r_validation/europe \
  INN
```

## Structured exchange

R writes machine-readable output, not captured console text:

- `solution_terms.csv` — one row per configuration with `consistency`, `pri`, `raw_coverage`, `unique_coverage`;
- `solutions.csv` — solution-level expression and metrics per solution type;
- `truth_table.csv` — the canonical truth table;
- `necessity.csv` — superset/subset necessity relations;
- `specification.csv` — the thresholds and directional expectations actually used;
- `*.txt` — human-readable transcripts for manual review only.

## Group-specific case files

Every analysis group exports the exact cases it analysed to
`<group>/analysis_cases.csv`:

```text
results/main/europe/analysis_cases.csv
results/main/region_north_west/analysis_cases.csv
results/main/region_south/analysis_cases.csv
results/main/region_central_east/analysis_cases.csv
results/main/sample_management_20plus/europe/analysis_cases.csv
```

R consumes the group file, never the pooled table. Without this, a regional
validation can be run against the whole European sample and appear to pass: the
numbers would be internally consistent and would describe the wrong population.

## Automated parity

```bash
python scripts/run_parity.py --results results/main --config configs/analysis.yml
```

The script discovers every group that exported its cases, runs the canonical
engine over each, and compares:

- truth-table row membership, matched on the condition bit pattern;
- truth-table row frequency;
- row consistency and PRI;
- row inclusion, `positive` against `OUT`;
- solution terms, matched on canonical configuration strings;
- term consistency, coverage and PRI.

Configuration strings are normalised before matching: tilde and lowercase
negation are both accepted and literals are ordered by the configured condition
order, so the comparison is over Boolean structure rather than over printed
text. The report is written to `outputs/validation/python_r_parity.csv` and the
script exits non-zero on anything worse than `NUMERICAL_TOLERANCE`.

## Comparison statuses

| Status | Meaning |
| --- | --- |
| `PASS` | Agreement within `1e-6`. |
| `NUMERICAL_TOLERANCE` | Difference up to `1e-3`: floating-point or rounding, worth recording. |
| `EQUIVALENT_ALTERNATIVE` | Different terms that cover exactly the same configurations, or a difference in a solution type for which R is canonical. Recorded, not a failure. |
| `ALGORITHM_DIFFERENCE` | The engines disagree about the analysis, not about rounding. Must be explained before the result is used. |
| `FAIL` | Validation could not run. |

Boolean minimisation can admit several equally minimal covers, and the two
engines need not return the same one. Covers are therefore compared
semantically with `solutions_equivalent`, so an alternative cover of the same
configurations is not reported as a disagreement.

## What is compared, and what is not

Conservative and parsimonious solutions are compared and must agree: both
engines implement the same unambiguous procedure.

The **intermediate solution is not compared for agreement**. R is canonical for
it, and the Python implementation is a documented approximation of Enhanced
Standard Analysis kept only to check Boolean structure. Comparing an
approximation against the authority and calling the deviation a failure would
misrepresent both. The parity report records R's intermediate solution for each
group as a `reference_solution` row, with `EQUIVALENT_ALTERNATIVE` where Python
did not reproduce it and the Python result quoted in the detail column.

## Differences found and resolved

Parity is not decoration. The first real run of the canonical engine, on
identical calibrated data, returned 12 structural and 3 tolerance differences.

### 1. PRI was computed incorrectly in Python

The implementation subtracted
`min(x, 1 - y)` where the standard formula subtracts `min(x, y, 1 - y)`:

```text
PRI = (sum min(x, y) - sum min(x, y, 1 - y)) / (sum x - sum min(x, y, 1 - y))
```

The subtracted term is membership held *simultaneously* in the configuration,
the outcome and its negation. Subtracting ordinary non-membership in the
outcome instead counted every case outside the outcome as inconsistency, and
drove PRI far below zero: on one truth-table row R reported `0.019` and Python
reported `-41.4`. Because row inclusion is gated on `pri_cutoff`, this silently
excluded rows that should have been positive, and the Python and R solutions
differed as a result.

That bug had been present since the fuzzy operators were written, was covered
by unit tests that asserted the wrong formula's own output, and was invisible
until the canonical engine actually ran.

### 2. Low-frequency rows were treated as negatives instead of remainders

`QCA::truthTable` codes a row observed in fewer than `n.cut` cases as a logical
remainder. The Python truth table treated any row with at least one case as an
observed negative, so those rows were unavailable as don't-cares and the
parsimonious solution could not simplify as far. In one region R returned
`DIG*HC + HC*INT*EXTK` where Python returned four terms.

A row nobody observed enough of is not evidence that the outcome is absent. The
truth table now carries a `remainder` column and minimisation uses it.

### 3. Python's intermediate solution is an approximation

Python restores literals onto parsimonious implicants; R removes inadmissible
simplifying assumptions and re-minimises. The two agree in most groups and
diverge where the covered rows already justify a simplification without any
counterfactual. This is why R is canonical for intermediate solutions and why
they are recorded rather than compared for agreement.

### Current state

On the synthetic demonstration, across the pooled analysis, all three regions
and the negated outcome:

| Status | Comparisons |
| --- | --- |
| `PASS` | 748 |
| `EQUIVALENT_ALTERNATIVE` | 2 |
| `ALGORITHM_DIFFERENCE` | 0 |

Largest numerical difference: `1.0e-14`. The two remaining rows are the
intermediate solutions in the regions where Python's approximation diverges
from the canonical R result.

The first two defects are the strongest available argument for keeping R
authoritative.

## Scope of parity

R/QCA has no notion of survey weights, so parity is checked against the **unweighted** estimand. Weighted set metrics are a Python extension and are validated by their own unit tests, not by R. This limitation is stated explicitly rather than hidden: a weighted solution that has no R counterpart must be reported as a Python-only result.

## Required reports

The Europe-wide solution and each main regional solution need a passing parity report before being used as substantive evidence.

## Environment setup

```bash
make r-check-env   # report missing packages
make r-setup       # install them
make r-crosscheck  # run the canonical engine
make parity        # run R and compare with Python
```
