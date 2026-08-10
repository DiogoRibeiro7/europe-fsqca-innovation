# R QCA Environment

R/QCA is the **canonical publication engine** for truth tables and minimisation in this project. The Python implementation is the independent numerical cross-check. See `docs/python_r_validation.md` for the division of authority.

## Check Local Packages

```bash
Rscript r/setup_renv.R
```

This reports whether `renv`, `QCA` and `yaml` are available. It does not install anything.

## Install Packages

```bash
Rscript r/setup_renv.R --install
```

This initializes `renv` when needed and installs the CRAN packages. Commit an `renv.lock` file only after package versions are installed and verified locally.

## Run the Canonical Analysis

```bash
Rscript r/qca_crosscheck.R \
  results/main/calibrated_memberships.csv \
  configs/analysis.yml \
  results/main/r_validation/europe \
  INN
```

Arguments are the calibrated membership table, the **analysis configuration**, the output directory and, optionally, the outcome. Thresholds, conditions and directional expectations are read from the configuration file, so nothing has to be kept in sync by hand.

The calibrated CSV must come from the Python pipeline. Do not run this script directly on raw WBES files.

## Structured Output

- `solution_terms.csv` — term-level consistency, PRI, raw and unique coverage;
- `solutions.csv` — solution-level expression and metrics for conservative, parsimonious and intermediate solutions;
- `truth_table.csv`, `necessity.csv`, `specification.csv`;
- `*.txt` transcripts for manual reading only.

## Automated Parity

```bash
python scripts/run_parity.py --results results/main --config configs/analysis.yml
```

Runs this script and compares its terms with the Python pipeline's, writing `parity_report.csv` and exiting non-zero on any difference.

## Known Limitation

The CRAN `QCA` package has no notion of survey weights, so parity is checked against the unweighted estimand only. Weighted set metrics are a Python extension and must be reported as such.
