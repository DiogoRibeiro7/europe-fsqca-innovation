# Research Workflow and Status

This document records the expected empirical workflow and the honest implementation status. Run `euro-fsqca readiness` for the machine-checked version of the top of this table.

## Status

| Stage | Status | Current implementation | Blocker or next step |
| ----- | ------ | ---------------------- | -------------------- |
| WBES data | **Blocked** | `data/manifest.csv` contains headers only. | Acquire the licensed EU-27 files (~18,939 establishments, 2018-2022) and record provenance. **Everything below is gated on this.** |
| Variable coverage audit | Ready, unused | `euro-fsqca variable-audit` ranks variables by comparable coverage across country releases. | Run against the real files; it needs data to say anything. |
| Construct design | **Blocked** | Six provisional constructs are declared. | Re-derive the conceptual domains from the coverage audit and the standardised questionnaire, then freeze the condition set. The current list is a hypothesis, not a design. |
| Variable mapping | **Blocked** | Worksheet exists; all seven constructs are `unavailable` with empty `source_variables`. | Verify release-specific variables, labels, transformations and missing-value rules. |
| Outcome definition | **Blocked** | `INN` is declared but not operationalised. | Define from the verified questionnaire, accounting for the three-year reference window. |
| Calibration anchors | **Blocked** | Placeholder 0 / 0.5 / 1 for every set. | Justify each anchor from the observed distribution and from theory, and record the justification in the config. |
| Survey design | Ready, unconfigured | Weighted set metrics, three estimands, effective-sample-size row inclusion, weight diagnostics, stratified bootstrap. | Fill `survey.weight_column` and `survey.strata_column` from the release, then set the primary estimand. |
| Survey timing | Ready, unconfigured | Timing is preserved through calibration; period omission and reference-window reporting are implemented. | Fill `timing.year_column` and declare the periods. |
| Analytical samples | Ready | Declared samples with filters and a recorded attrition table; MGT isolated in an extension sample. | Replace the placeholder filters with the real screener rules. |
| Harmonisation checks | Ready | Missingness, impossible values, duplicates, categories, anomalies, exclusion log. | Run against the real table. |
| Europe-wide QCA | Ready | Necessity, truth table, conservative/parsimonious/intermediate minimisation, core-peripheral roles, negated outcome, per-estimand metrics. | Run only after mapping and calibration are verified. |
| Regional QCA | Ready | Independent macroregional solutions plus term-level comparison against the pooled solution. | **Blocked on theory**: the taxonomy is geographic. See docs/regional_taxonomy_theory.md. |
| Portability | Ready | Directed term-level evaluation, bootstrap intervals, two-stage discovery/transfer bootstrap, region-pair aggregates with explicit semantics. | Interpret against the real data. |
| Complementarity | Ready | Pairwise sufficiency tests, co-occurrence reported separately, solution-level substitution. | Interpret against the real data. |
| Robustness | Ready | Thresholds, anchors, estimands, country/sector/size/period omission, alternative taxonomy, bootstrap stability — all wired into `run_analysis`. | None. |
| Net-effect comparison | Removed | Not part of the study. | Re-add only if a specific question needs it, using the observed outcome and the survey design, described as an additive-association contrast. |
| R validation | Ready | Config-driven canonical R/QCA run with structured term output and automated parity via `scripts/run_parity.py`. | Weighted metrics have no R counterpart; report them as Python-only. |
| Tables and figures | Partial | Table and figure helpers exist. | Wire a manuscript build once there are real outputs. |
| Manuscript | **Empty** | LaTeX scaffold mirrors the design. | Populate only from generated empirical outputs. |

"Ready" means the code path exists, is tested, and is executed by the pipeline. It does not mean it has ever seen real data.

## Execution order for the next version

The next release is not a feature release. It is the first research version, and it consists of one sequence:

1. Acquire the real EU-27 WBES data and record it in the manifest.
2. Preserve survey weights, strata, NUTS region, sector, size and timing in the analytical table.
3. Audit which variables are genuinely common across the country releases.
4. Redesign the condition set from the data dictionary and theory, in that order.
5. Decide whether `MGT` belongs in the primary model or only in the restricted-sample extension.
6. Construct the real innovation outcome, accounting for the reference window.
7. Define and justify the calibration anchors.
8. Run weighted and unweighted QCA and compare the estimands.
9. Validate against R/QCA and require parity to pass.
10. Analyse Northern/Western, Southern and Central/Eastern Europe.
11. Test directional portability with uncertainty.
12. Write the results.

Everything else is secondary. Adding abstractions, documentation, release infrastructure or manuscript scaffolding before step 1 is what produced a well-tested repository with an empty empirical centre.

## Interpretation rule

No QCA output in this repository is substantive until the manifest, schema audit, variable coverage audit, variable mapping, construct definitions, outcome definition and calibration anchors are complete, and `euro-fsqca readiness` reports no fatal blockers.
