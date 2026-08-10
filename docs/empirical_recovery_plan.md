# Empirical Recovery Plan

## Purpose

This repository contains a large, well-tested analytical apparatus and no
empirical result. This document identifies the shortest path from the current
tree to the first valid Europe-wide fsQCA result from real World Bank Enterprise
Survey data, and classifies every existing component by whether it contributes
to that path.

Nothing here changes analytical code. It is an audit and a route.

## The single blocker

`data/raw/` contains only `.gitkeep`. `data/manifest.csv` contains only headers.

Every stage from the schema audit onwards is downstream of that one fact. No
amount of further engineering moves the project forward until the licensed EU-27
files are on disk. The World Bank reports 18,939 establishments across the EU-27
collected between 2018 and 2022; until those files exist locally, the repository
cannot produce a finding, and no code change alters that.

## Component classification

`required now` means the component is on the critical path to the first
Europe-wide result. `required later` means it is needed for the paper but not
for that first result. `optional` means it is defensible but not necessary.
`disable` means it should stop executing in the main pipeline without being
deleted. `remove` means it should leave the repository.

| Component | File or module | Class | Reason |
| --- | --- | --- | --- |
| Data provenance and manifest | `data/provenance.py` | required now | Ingestion cannot start without checksummed source records. |
| Table readers | `data/io.py` | required now | Must read the real release formats. |
| Analytical table builder | `scripts/build_analysis_table.py` | required now | Currently raises `NotImplementedError`; this is the literal gap between the repository and the data. |
| Schema audit | `data/schema.py` | required now | Determines which variables are comparable EU-wide. |
| Variable coverage audit | `variable_coverage_matrix` | required now | The evidence base for the measurement model. |
| Variable mapping validation | `data/mapping.py` | required now | Turns the audit into an auditable mapping. |
| Harmonisation diagnostics | `data/harmonisation.py` | required now | Special codes and impossible values must be resolved before calibration. |
| Sample construction | `analysis/samples.py` | required now | Defines the analytical population and its attrition. |
| Construct diagnostics | `analysis/constructs.py` | required now | Validates uncalibrated constructs before anchors are chosen. |
| Direct calibration | `sets/calibration.py`, `sets/composites.py` | required now | Produces the calibrated memberships the canonical engine consumes. |
| Calibration diagnostics | `analysis/calibration.py` | required now | Evidence for anchor justification. |
| Readiness checks | `readiness.py` | required now | The gate that prevents a fictitious run. |
| Region assignment | `data/regions.py` | required now | Needed to export the Europe-wide and regional case files. |
| Canonical R engine | `r/qca_crosscheck.R` | required now | The publication truth table and minimisation. |
| Fuzzy operators and fit | `qca/fuzzy.py` | required now | Needed for Python-side validation of the canonical result. |
| Truth table | `qca/truth_table.py` | required now | Needed for Python-side validation. Weighted row inclusion is not needed now. |
| Necessity | `qca/necessity.py` | required now | Part of the first Europe-wide result. |
| Parity | `analysis/parity.py` | required now | Establishes that the two engines agree on the first real result. |
| Python conservative and parsimonious minimisation | `qca/minimize.py` | required now | Retained as the numerical cross-check, not as the publication engine. |
| Python intermediate minimisation | `qca/minimize.py` | required later, demote | R is canonical for intermediate solutions. Keep the Python implementation only to check Boolean structure. |
| Weighted set metrics | `qca/fuzzy.py`, `survey.py` | required later | Belongs to weighting sensitivity, not to the canonical solution generator. |
| Effective-sample-size row inclusion | `qca/truth_table.py` | disable in main analysis | The primary truth table must use standard case frequency. Keep as an exploratory appendix. |
| Regional analysis | `pipeline.py` | required later | Stage C, after the Europe-wide result exists. |
| Portability | `analysis/portability.py` | required later | The likely contribution, but downstream of a valid regional result. |
| Portability bootstrap | `bootstrap_directed_portability` | required later, disable now | Expensive and meaningless before deterministic portability exists. |
| Threshold and calibration sweeps | `analysis/robustness.py` | required later | Minimum robustness set, Stage D. |
| Estimand sweep | `estimand_sweep` | required later | Becomes weighting sensitivity in Stage C. |
| Leave-one-group-out | `leave_one_group_out` | required later | Part of the minimum robustness set. |
| Bootstrap QCA | `bootstrap_qca`, `bootstrap_stability` | disable now | Stability of a solution that does not yet exist is not informative. |
| Alternative regional taxonomy | `region_scheme_comparison` | disable now | Requires a theoretically justified primary taxonomy first. |
| Complementarity tests | `analysis/complementarity.py` | required later, rename | The concept name overstates what the test supports. |
| Condition co-occurrence | `condition_cooccurrence` | optional | Descriptive bookkeeping. |
| Net-effect regression | `analysis/regression.py` | remove from the main study | Not a validation of QCA, and it creates reviewer risk for no analytical gain. |
| Synthetic demo generator | `demo.py` | required now, restricted | Keep strictly for software tests. Never on the empirical path. |
| Known-structure scenarios | `synthetic.py` | optional | Useful for validating the minimiser; no empirical role. |
| Figure helpers | `figures.py` | required later | Figures come after results. |
| Table metadata helpers | `tables.py` | required later | Needed for the reproducible table register. |
| Release tooling | `.zenodo.json`, `CITATION.cff`, release report | required later | Publication packaging, not research. |
| Manuscript scaffold | `paper/` | required later | Written from generated outputs, not before them. |
| Historical review records | `docs/release_report.md`, `docs/novelty_review.md`, `reviews/` | optional | Keep as history. Do not extend before results exist. |

Nothing is classified `remove` except the net-effect regression. The apparatus
is not the problem; its ordering is.

## Stage status

| Required empirical stage | Current state | Blocker | File or module | Required action |
| --- | --- | --- | --- | --- |
| 1. WBES source files | Absent | Licensed data not acquired | `data/raw/` | Obtain the EU-27 releases under the applicable access terms and place them locally. |
| 2. Data manifest | Headers only | No source files | `data/manifest.csv`, `data/provenance.py` | Generate one checksummed row per source file during ingestion. |
| 3. Schema audit | Code ready, never run | No source files | `data/schema.py` | Run against the real files; export the schema inventory and comparison. |
| 4. Variable mapping | All seven constructs `unavailable` | No schema audit | `configs/wbes_variable_map.yml` | Replace placeholders with verified variables, coverage and coding. |
| 5. Harmonisation | Code ready, never run | No mapping | `data/harmonisation.py` | Resolve special codes, build the exclusion log. |
| 6. Sample construction | Framework ready, filters empty | Questionnaire screener unknown | `configs/analysis.yml`, `analysis/samples.py` | Encode the real eligibility rules as executable filters. |
| 7. Construct construction | Not started | No mapping | `analysis/constructs.py` | Build and validate uncalibrated constructs before anchors. |
| 8. Outcome construction | Not started | Innovation items unknown | `configs/analysis.yml` | Define `INN` from the real items, accounting for the three-year reference window. |
| 9. Calibration | Placeholder 0 / 0.5 / 1 | No construct distributions | `configs/analysis.yml` | Justify every anchor from distribution and theory. |
| 10. R/QCA Europe analysis | Script ready, never run | No calibrated data; CRAN `QCA` not installed | `r/qca_crosscheck.R` | Lock the R environment, export the Europe case file, run the canonical analysis. |
| 11. Python parity | Comparison logic ready and unit-tested | No canonical result to compare | `analysis/parity.py`, `scripts/run_parity.py` | Compare on group-specific case files once a real result exists. |
| 12. Regional analysis | Pipeline ready | Stage 10 incomplete | `pipeline.py` | Run only after the Europe-wide result is valid. |
| 13. Portability | Implemented, never applied | Stage 12 incomplete | `analysis/portability.py` | Apply deterministically first, bootstrap afterwards. |
| 14. Robustness | Implemented and wired | Stage 12 incomplete | `analysis/robustness.py` | Reduce to the minimum set and run once results exist. |
| 15. Manuscript | Protocol text, no results | Everything above | `paper/` | Write from generated outputs. |

## Shortest path to the first result

The critical path has eleven steps and only the first is not under this
repository's control.

1. Acquire the licensed EU-27 files into `data/raw/`.
2. Ingest them into one raw standardised table with provenance, and populate
   `data/manifest.csv`. Requires replacing the `NotImplementedError` in
   `scripts/build_analysis_table.py`.
3. Run the schema audit and the variable coverage audit against the real files.
4. Rewrite `configs/wbes_variable_map.yml` from the audit, using only verified
   variables.
5. Choose the primary condition set from coverage and comparability, not from
   the original project design. Fewer defensible conditions beat six weak ones.
6. Determine the real management eligibility rule and encode it as an executable
   filter, or drop `MGT` from the study.
7. Build the harmonised table with special codes resolved and design variables
   preserved.
8. Define and freeze the innovation outcome.
9. Validate the uncalibrated constructs, then justify every calibration anchor.
10. Lock the R environment and export the Europe-wide calibrated case file.
11. Run the canonical R/QCA analysis and check Python parity.

Steps 3 to 9 are sequential and cannot be parallelised, because each constrains
the next. Steps 2, 10 and the readiness gate are the only parts that can be
built before the data arrives.

## What is being done before the data arrives

Only work that shortens the path above, and only work that removes or
reorders existing capability rather than adding new capability:

- implement the ingestion layer so that step 2 is ready the day the files land;
- make the readiness gate mandatory so that a fictitious run is impossible;
- restore standard case frequency as the primary truth-table rule and record the
  engine authority decision;
- lock the R environment;
- declare directional expectations from theory, before any truth table exists;
- export group-specific case files so parity cannot silently compare different
  samples;
- remove the net-effect regression from the main study;
- rename the complementarity module to what it actually measures;
- state the theoretical basis the regional taxonomy still needs.

## What is explicitly not being done

No new visualisation framework, robustness method, configuration metric,
simulation system, methodological extension, release infrastructure or
manuscript scaffolding. The repository does not need more capability. It needs
data.

## Stop condition

If the canonical Europe-wide analysis cannot produce a scientifically valid
solution once the data is in place, development stops there and the blocker is
documented. Regional analysis, portability and robustness are not attempted on
an invalid base.
