# Construct Validation

This project treats construct measurement as a research decision, not as a side effect of executable code.

## Required Justification

Each of the six conditions must have a written justification before empirical QCA:

| Construct | Theoretical meaning | WBES variables | Transformation | Aggregation | Missing-data rule | Expected direction | Current status |
| --------- | ------------------- | -------------- | -------------- | ----------- | ----------------- | ------------------ | -------------- |
| `DIG` | Digital and technological capability. | Not verified. | Not verified. | Not verified. | Not verified. | Higher capability should increase membership. | Blocked on WBES mapping. |
| `HC` | Human capital capability. | Not verified. | Not verified. | Not verified. | Not verified. | Higher capability should increase membership. | Blocked on WBES mapping. |
| `FIN` | Financial capacity and lower financing constraint. | Not verified. | Not verified. | Not verified. | Not verified. | Higher capacity should increase membership. | Blocked on WBES mapping. |
| `INT` | Internationalisation. | Not verified. | Not verified. | Not verified. | Not verified. | Greater international exposure should increase membership. | Blocked on WBES mapping. |
| `MGT` | Management capability. | Not verified. | Not verified. | Not verified. | Not verified. | Stronger practices should increase membership. | Blocked on WBES mapping. |
| `EXTK` | External knowledge access. | Not verified. | Not verified. | Not verified. | Not verified. | Greater external knowledge access should increase membership. | Blocked on WBES mapping. |

## Diagnostics Command

Run after a verified pre-calibration table exists:

```bash
poetry run euro-fsqca construct-diagnostics \
  --input data/processed/wbes_eu27_analysis.csv \
  --config configs/analysis.yml \
  --output-dir outputs/constructs
```

Generated files:

- `construct_summary.csv`
- `construct_country_summary.csv`
- `construct_region_summary.csv`
- `construct_correlations.csv`
- `component_correlations.csv`

## Review Rules

- Do not select among alternative operationalisations by choosing the strongest QCA result.
- Keep a main operationalisation fixed before final analysis.
- Use reasonable alternatives only as robustness checks.
- For multi-item formative constructs, justify aggregation by measurement logic, not by a reflective scale statistic alone.
