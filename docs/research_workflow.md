# Research Workflow

This document records the expected empirical workflow and the current implementation status.

| Stage | Status | Current implementation | Blocker or next step |
| ----- | ------ | ---------------------- | -------------------- |
| WBES data | Blocked | Raw, interim, and processed directories exist and case-level files are ignored. | Add source manifest and place licensed source files locally. |
| Schema validation | Partial | `euro-fsqca inspect` can create a privacy-safe schema report for one file. | Add multi-file EU-27 schema comparison and machine-readable audit output. |
| Variable mapping | Partial | Mapping worksheet exists for `DIG`, `HC`, `FIN`, `INT`, `MGT`, `EXTK`, and `INN`. | Verify exact release-specific variables, labels, and transformations. |
| Data quality checks | Missing | No full harmonisation diagnostics exist yet. | Add missingness, impossible-value, duplicate, category, and anomaly reports. |
| Construct construction | Partial | Composite builder supports configured aggregation and missing-data rules. | Add validated construct definitions, coverage reports, and measurement justification. |
| Calibration | Partial | Direct calibration and anchor shifting are implemented from config. | Add calibration diagnostics and empirically justified anchors. |
| Europe-wide QCA | Partial | Pipeline can run necessity, truth table, minimisation, fit, negative outcome, and regression comparison on complete calibrated input. | Run only after WBES mapping and calibration are verified. |
| Regional QCA | Partial | Pipeline groups by configured macroregion using the same calibration. | Add richer regional comparison tables and sample-size guardrails. |
| Portability | Partial | Existing code evaluates configuration fit by region. | Add directed pairwise, matrix, heatmap, network, and country outputs. |
| Robustness | Partial | Threshold and anchor sweeps exist. | Add solution-similarity, sample, bootstrap, diversity, and complementarity diagnostics. |
| R validation | Partial | R script can independently run QCA from exported calibrated data. | Add machine-readable parity checks, tolerances, and regional reports. |
| Tables and figures | Missing | Demo examples exist, but production table and figure generation is incomplete. | Generate all scientific outputs from code with metadata. |
| Manuscript | Partial | LaTeX scaffold mirrors the research design. | Populate only from generated empirical outputs after validation. |

## Execution Order

1. Establish the real data foundation.
2. Validate the analytical engine.
3. Produce Europe-wide and regional results.
4. Test robustness and portability.
5. Generate validation artifacts, tables, and figures.
6. Build the manuscript and release report.

The final QCA analysis should not be treated as substantive until the WBES source manifest, schema audit, variable mapping, construct definitions, outcome definition, and calibration anchors are complete.
