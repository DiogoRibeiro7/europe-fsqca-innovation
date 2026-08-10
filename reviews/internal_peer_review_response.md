# Internal Peer Review Response

Response date: 2026-08-10.

## Response Summary

The review confirms that the repository is ready as a reproducible methodological scaffold, but not ready for substantive empirical claims. The remaining blockers require licensed WBES files and research decisions that cannot be replaced by code.

## Response Matrix

| Review issue | Status | Response |
| ------------ | ------ | -------- |
| Source data are not present. | Open | Raw WBES files must remain outside version control. The repository now provides manifest validation and schema audit commands, but the licensed files must be added locally. |
| WBES source variables are not mapped. | Open | `configs/wbes_variable_map.yml` remains the controlled mapping worksheet. Exact release, wording, source variables, recodes, and missing rules still need to be completed. |
| Calibration anchors are placeholders. | Open | Anchor choices remain configured in `configs/analysis.yml`. They must be justified before running the empirical analysis. |
| R validation packages are missing locally. | Partially resolved | `make r-check-env` and `make r-setup` now document the R setup path. `renv` and `QCA` still need to be installed locally before validation can run. |
| Manuscript lacks empirical tables. | Partially resolved | The manuscript now has data-gated table slots and artifact references. Tables must be generated from verified empirical outputs. |

## Repository Changes Already Supporting the Response

- Data provenance validation and schema audit commands.
- Variable mapping validation.
- Harmonisation and construct diagnostics.
- Calibration diagnostics and sensitivity checks.
- Truth-table, diversity, necessity, complementarity, robustness, and portability diagnostics.
- Generated table metadata.
- Study-level specification validation.
- Reproducibility make targets.
- R environment check and cross-validation command wrapper.
- Data-gated manuscript scaffold.
- Novelty review with narrowed contribution claim.

## Remaining Work Before Submission

1. Acquire the licensed WBES EU-27 release locally.
2. Complete `data/manifest.csv` with file names, checksums, source, access date, and license notes.
3. Complete `configs/wbes_variable_map.yml` from the exact survey release.
4. Build the analytical table and record exclusions.
5. Freeze calibration anchors with written justification.
6. Run the empirical pipeline and R validation.
7. Generate tables, figures, manuscript text, and release report from verified outputs.

## Claim Control

Until the open items are resolved, the manuscript may describe the research design and software, but it must not report synthetic outputs as empirical evidence or infer regional findings from placeholders.
