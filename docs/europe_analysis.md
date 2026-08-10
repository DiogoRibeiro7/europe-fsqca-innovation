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

The primary sample writes to the root of the output directory; every declared
extension sample writes to `sample_<label>/` with the same structure.

## Core Outputs

The Europe-wide folder contains:

- `necessity.csv`;
- `truth_table.csv` — with case, weighted and effective-sample-size frequency per row;
- `truth_table_diagnostics.csv`;
- `contradictory_rows.csv`;
- `solutions.csv` — one row per solution type and estimand;
- `solution_terms.csv` — one row per term and estimand;
- `core_peripheral.csv` — core and peripheral roles from the intermediate solution;
- `term_substitutability.csv`.

Three solution types are reported: conservative, parsimonious and intermediate. The intermediate solution requires directional expectations and is what licenses core/peripheral claims.

The root output directory contains `qca_specification.json`, recording the conditions, outcome, thresholds, frequency basis, logical-remainder policy, directional expectations, survey design, timing and declared samples. It also contains `analytical_samples.csv`, `weight_diagnostics.csv` and `survey_timing.csv`, which describe the population the solution refers to.

`solution_terms.csv` reports term fit under every configured estimand, plus the number of relevant establishments and the country or regional distribution among cases with configuration membership above `0.5`.

## Guardrail

Do not report the Europe-wide result as substantive while `euro-fsqca readiness` reports any fatal blocker. The command refuses a configuration marked `status: template`, which is the current state of `configs/analysis.yml`.
