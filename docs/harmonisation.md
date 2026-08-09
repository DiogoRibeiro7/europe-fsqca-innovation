# Harmonisation

The harmonisation layer checks whether a firm-level analytical table preserves source identity and records data-quality issues before QCA analysis.

## Required Identifiers

Each establishment-level record should preserve:

- `firm_id`
- `country`
- `region`
- `survey_year`
- `sector`
- `size_class`
- `source_dataset`

Missing identifiers are reported rather than silently ignored.

## Special Missing Values

WBES response codes such as do not know, refused, or not applicable must be recorded before conversion to standard missing values. Use `recode_special_missing` with an explicit column-by-column codebook so the project can preserve missingness semantics.

## Diagnostics

Run:

```bash
poetry run euro-fsqca check-harmonisation \
  --input data/processed/wbes_eu27_analysis.csv \
  --report-output outputs/data/harmonisation_report.csv \
  --exclusion-output outputs/data/exclusion_log.csv
```

The report can flag:

- missing identifiers
- missingness
- duplicate case identifiers
- unexpected categories
- impossible continuous values
- extreme continuous values

The exclusion log records rule IDs, reasons, affected counts, and affected countries. A row with `rule_id=none` means no exclusion rules have been configured for that run.

## Interpretation

Diagnostics do not remove observations by themselves. Exclusions must be configured as explicit rules and reviewed before downstream analysis.
