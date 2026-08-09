# Europe-Wide Analysis

The Europe-wide QCA run is the main empirical analysis once the WBES data foundation is complete.

## Required Inputs

- verified EU-27 source manifest;
- completed schema audit;
- verified variable mapping;
- harmonised firm-level table;
- justified construct definitions;
- justified `INN` definition;
- common Europe-wide calibration anchors.

## Command

```bash
poetry run euro-fsqca run \
  --input data/processed/wbes_eu27_analysis.csv \
  --config configs/analysis.yml \
  --output-dir results/main
```

## Core Outputs

The Europe-wide folder contains:

- `necessity.csv`;
- `truth_table.csv`;
- `truth_table_diagnostics.csv`;
- `contradictory_rows.csv`;
- `solutions.csv`;
- `solution_terms.csv`.

The root output directory contains `qca_specification.json`, recording the conditions, outcome, frequency cutoff, consistency cutoff, PRI cutoff, logical-remainder policy, and common-calibration scope.

`solution_terms.csv` reports term fit plus the number of relevant establishments and country or regional distribution among cases with configuration membership above `0.5`.

## Guardrail

Do not report the Europe-wide result as substantive while the source manifest, mapping, construct, outcome, or calibration documents still contain unresolved placeholders.
