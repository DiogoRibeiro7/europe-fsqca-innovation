# Internal Peer Review

Review date: 2026-08-10.

## Verdict

Major revision before empirical submission. The computational scaffold is strong, but the paper cannot make substantive claims until the licensed WBES release, variable mapping, calibration anchors, and R validation are complete.

## Blocking Issues

| Severity | Issue | Evidence | Required action |
| -------- | ----- | -------- | --------------- |
| Fatal | Source data are not present in the repository and cannot be inferred. | `data/manifest.csv` is a provenance shell and raw WBES data are intentionally ignored. | Add local licensed WBES files, validate checksums, and keep only manifest metadata committed. |
| Fatal | WBES source variables are not mapped. | `configs/wbes_variable_map.yml` records all constructs as unavailable. | Fill exact release, question wording, source variable, transformation, and missing-value rule for each construct. |
| Fatal | Calibration anchors are placeholders. | `configs/analysis.yml` warns not to run unchanged. | Freeze anchor justifications before any solution is interpreted. |
| Major | R validation cannot run on this machine until R packages are installed. | `make r-check-env` reports missing `renv` and `QCA`. | Run `make r-setup`, then run cross-validation on exported calibrated data. |
| Major | Manuscript contains placeholders instead of empirical tables. | `paper/sections/05_results.tex` points to generated artifacts. | Populate only from generated tables with metadata. |

## Positive Controls

- The Python pipeline runs end to end on synthetic data.
- Local quality gates cover linting, strict type checking, and tests.
- Regional membership is configured before empirical solution inspection.
- Robustness diagnostics include threshold, calibration, omission, bootstrap, diversity, necessity, and portability checks.
- The novelty claim is appropriately narrow and does not claim uniqueness for European innovation fsQCA.

## Required Revision Sequence

1. Validate source-file provenance.
2. Complete and audit the WBES variable map.
3. Construct the analytical table with documented exclusions.
4. Justify and freeze calibration anchors.
5. Run diagnostics and main analysis.
6. Run R validation and parity checks.
7. Generate manuscript tables and figures from code.
8. Update the manuscript and release report.

## Residual Risk

The largest remaining risk is measurement validity. If WBES releases do not contain comparable indicators for all six conditions across EU countries, the construct set must be revised before running QCA. Any revision must happen before inspecting empirical solutions.
