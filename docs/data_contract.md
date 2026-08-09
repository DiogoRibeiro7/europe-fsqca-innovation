# Data Contract

## Analytical table

The pipeline expects one row per firm/establishment.

Required identifiers:

- `firm_id`: stable case identifier
- `country`: canonical English country name matching `configs/regions.yml`

Required raw constructs:

- `DIG_raw`
- `HC_raw`
- `FIN_raw`
- `INT_raw`
- `MGT_raw`
- `EXTK_raw`
- `INN_raw`

## Missing data

Missing WBES responses must remain missing until an explicit rule is documented. Do not silently convert refusal, don't know, not applicable, or survey routing codes to zero.

## Recoding

Every source-variable recode must record:

- source variable name
- source label/question wording
- original coding
- missing-value coding
- transformation
- output construct
- rationale

## Privacy and reproducibility

Never commit raw or case-level derived WBES microdata. Commit only code, schemas, aggregate diagnostics, variable mappings, and publication-safe output.
