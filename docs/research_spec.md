# Research Specification

`configs/research_spec.yml` is the project-level study contract. It records the unit of analysis, canonical set names, outcome, regional schemes, missing-data policy, calibration scope, robustness checks, and required outputs.

The file deliberately points to separate lower-level artifacts:

- `configs/analysis.yml` stores calibration anchors and QCA thresholds.
- `configs/wbes_variable_map.yml` stores release-specific source-variable mapping.
- `configs/regions.yml` stores regional membership.
- `data/manifest.csv` stores source-file provenance.

Use the validator before running the empirical pipeline:

```bash
PYTHONPATH=src python -m euro_fsqca.cli validate-spec --spec configs/research_spec.yml
```

The validator checks that the study-level condition and outcome names match the
**primary sample** of the analysis configuration, that the declared samples and
estimands agree between the two files, that regional schemes exist, that
countries are assigned once within the primary taxonomy, and that required
output paths stay outside the raw-data area.

It also warns when the analysis configuration is still marked as a template,
when no survey weight column is configured, and when no survey year column is
configured. Those warnings are not cosmetic: each one marks a claim the study
cannot currently make. `euro-fsqca readiness` reports the same conditions as
blocking errors.
