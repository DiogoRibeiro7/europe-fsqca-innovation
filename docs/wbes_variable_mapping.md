# WBES Variable Mapping Workflow

The repository deliberately postpones exact WBES variable names until the selected EU-27 release is inspected.

## Procedure

1. Acquire the permitted microdata release.
2. Put it under `data/raw/`.
3. Run `euro-fsqca inspect` to export column names, dtypes, missingness, and cardinality.
4. Read the matching questionnaire and variable labels.
5. Fill `configs/wbes_variable_map.yml`.
6. Build canonical raw constructs.
7. Freeze the mapping before calibration or outcome analysis.

## Candidate topic families

The World Bank Enterprise Surveys cover finance, trade, workforce, management practices, innovation and technology, firm profile, and firm performance. The exact availability and wording must be verified for the chosen EU-27 release.

## Anti-pattern

Do not choose variables because they produce cleaner truth tables. Measurement must precede configurational analysis.
