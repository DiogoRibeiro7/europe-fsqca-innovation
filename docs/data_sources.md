# Data Sources

This project uses World Bank Enterprise Surveys microdata for EU-27 establishments. The source files can be access-controlled and must not be committed unless the licence explicitly permits redistribution.

## Directory Stages

- `data/raw/`: immutable source files exactly as obtained by an authorised researcher.
- `data/interim/`: intermediate files created during schema audit and harmonisation.
- `data/processed/`: analytical files derived from verified mappings and documented transformations.

The repository keeps only `.gitkeep` placeholders in these directories. Case-level data and generated results are excluded from version control.

## Source Manifest

Record every raw source file in `data/manifest.csv` before processing. The manifest has these columns:

| Column | Meaning |
| ------ | ------- |
| `source_name` | Human-readable dataset name. |
| `download_location` | Official source page or local acquisition note. |
| `retrieval_date` | Date the file was obtained, using `YYYY-MM-DD`. |
| `country` | Country covered by the source file. |
| `survey_year` | Survey year or wave. |
| `wbes_version` | WBES release or version when available. |
| `file_name` | File path relative to `data/raw/`, or an absolute local path. |
| `checksum` | SHA-256 checksum of the raw file. |
| `file_size` | File size in bytes. |
| `processing_status` | Current status, such as `pending`, `audited`, or `excluded`. |

## Validation

Run:

```bash
poetry run euro-fsqca validate-data --manifest data/manifest.csv --root data/raw
```

The command checks that every listed source file exists and matches the recorded SHA-256 checksum and file size. Processing should stop when a listed file is missing or mismatched.

The empty template manifest validates successfully with zero checked files. That
is a property of `validate-data`, not evidence of readiness: an empty manifest
means no analysis has been done. Use `euro-fsqca readiness`, which treats an
empty manifest as a fatal blocker.

Add one row per licensed source file before running empirical processing.

## Required Design Variables

The harmonised analytical table must carry more than the construct inputs. The
following are required and must not be dropped during harmonisation, because
population inference and subgroup robustness are impossible without them:

| Variable | Why it is required |
| --- | --- |
| sampling weight | Inclusion probabilities differ by stratum; without it no population claim is possible. |
| stratum identifier | Needed for stratified resampling and for weight diagnostics. |
| survey year | Fieldwork ran 2018-2022 and the innovation reference window moves with it. |
| sector | Sampling stratum and an omission-robustness dimension. |
| size class and employment count | Sampling stratum, omission dimension, and the screener for the management module. |
| region (NUTS where released) | Sub-national context and a sampling stratum. |

`calibrate_frame` preserves every column listed in `survey`, `timing` and
`design_columns` in the analysis configuration. Anything not listed there is
dropped at calibration, so declare these columns before running the pipeline.

## Authorised Acquisition

An authorised researcher should obtain the EU-27 WBES files from the World Bank Enterprise Surveys or Microdata Library under the applicable access terms, store them in `data/raw/`, calculate checksums locally, and record the metadata in `data/manifest.csv`.

Raw files must remain unchanged. If a corrected source file is obtained, add or update the manifest row with the new checksum and document the reason in the project notes.
