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

## Automated parity

```bash
python scripts/run_parity.py --results results/main --config configs/analysis.yml
```

The script runs R, normalises both engines' configuration strings to a canonical form (tilde and lowercase negation are both accepted, literals are ordered by the configured condition order), joins on `solution` and `configuration`, and writes `parity_report.csv` and `parity_summary.csv`. It exits non-zero on any difference, so parity can gate a release instead of being asserted in prose.

## Comparison statuses

- `PASS`: same term, metrics agree within tolerance;
- `TOLERANCE_DIFFERENCE`: same term, metric differences exceed tolerance;
- `STRUCTURAL_DIFFERENCE`: a term exists in one engine only;
- `MISSING_METRIC`: a metric is not reported by both engines;
- `FAIL`: validation could not run.

Default tolerance is `1e-6` for consistency, coverage and PRI.

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
