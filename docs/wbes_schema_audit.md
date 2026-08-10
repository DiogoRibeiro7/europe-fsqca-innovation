# WBES Schema Audit

## Labels are read, not guessed

A WBES variable name says almost nothing. `h1` and `wk2` are only interpretable
through the question text the release carries as a variable label, and their
numeric codes only through the value labels. Stata and SPSS sources are read
through `pyreadstat` so both survive into the audit.

CSV and Parquet carry no such metadata. They are reported as unlabelled rather
than given invented labels.

## Artifacts

```bash
make schema-audit
```

| File | Content |
| --- | --- |
| `outputs/data/wbes_schema_inventory.parquet` | Per source and variable: label, value labels, dtype, observed values, potential missing codes, non-missing count. |
| `outputs/data/wbes_schema_comparison.csv` | Cross-source view: how many countries carry the variable, how many populate it usably, and whether the label agrees. |
| `outputs/data/schema_audit.csv` | The inventory in CSV, which is what the readiness check reads. |

## The label-agreement column

`label_agreement` is the column to read first:

| Value | Meaning |
| --- | --- |
| `identical` | Every source that carries the variable asks the same question. |
| `conflicting` | The same variable name asks a different question in different releases. |
| `no_label` | No source carries question text for it. |

`conflicting` is the dangerous case. A variable present in every country with a
consistent name and an inconsistent question looks comparable and is not.
Mapping it on the strength of its name would put a different measurement in the
same construct for different countries.

The schema audit compares all source files listed in `data/manifest.csv`. It is designed to support variable mapping without assuming that matching column names have matching meaning.

## Command

```bash
poetry run euro-fsqca schema-audit \
  --manifest data/manifest.csv \
  --root data/raw \
  --output outputs/data/schema_audit.csv
```

The output path is ignored by Git because it can describe restricted source files. Commit only documentation and mapping decisions that are safe to share.

## Output Columns

| Column | Meaning |
| ------ | ------- |
| `source_name` | Dataset name from the source manifest. |
| `country` | Country from the source manifest. |
| `survey_year` | Survey year from the source manifest. |
| `wbes_version` | WBES release or version when available. |
| `column` | Source variable name. |
| `label` | Variable label when supplied by a validated metadata reader. |
| `dtype` | Data type observed after reading the source file. |
| `valid_values` | Compact JSON list of distinct values when cardinality is low. |
| `missing_value_codes` | Potential special missing codes observed in the data. |
| `survey_module` | Reserved for verified module metadata. |
| `n_non_missing` | Number of non-missing observations. |
| `missing_share` | Share missing in that source file. |
| `n_unique` | Distinct non-missing values. |
| `availability` | Whether the variable appears in all, most, or some source files. |
| `presence_count` | Number of source files where the variable appears. |
| `total_sources` | Number of manifest files included in the audit. |
| `countries_present` | Countries where the variable appears. |
| `years_present` | Survey years where the variable appears. |
| `definition_status` | Review status for definition compatibility. |

## Interpretation Rules

- A shared column name is not sufficient evidence of a shared concept.
- Low-cardinality value lists help find changed coding, but labels and questionnaires must still be checked.
- Potential missing codes are reported for review; they are not automatically recoded.
- Variables used for `DIG`, `HC`, `FIN`, `INT`, `MGT`, `EXTK`, or `INN` must be verified before empirical analysis.

## Current Status

The repository now includes the audit command and output schema. The project remains blocked on licensed WBES files and verified question wording before final variable mapping can be completed.
