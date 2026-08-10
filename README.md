# Configurational Pathways to Firm Innovation Across Europe

Research repository for a comparative fuzzy-set Qualitative Comparative Analysis (fsQCA) of firm innovation across Europe, with explicit comparison of Northern/Western, Southern, and Central/Eastern European macroregions.

## Research question

Which combinations of firm capabilities and resources are sufficient for high innovation across Europe, and which configurations are genuinely pan-European versus region-specific?

The main design studies six conditions:

- `DIG` — digital and technological capability
- `HC` — human capital
- `FIN` — financial capability
- `INT` — internationalisation
- `MGT` — management capability
- `EXTK` — external knowledge integration
- `INN` — high innovation performance, the primary outcome

The principal set relation is:

```text
{DIG, HC, FIN, INT, MGT, EXTK} => INN
```

The analysis is repeated for `~INN` to preserve causal asymmetry.

## Why fsQCA

The paper is designed around equifinality, conjunctural causation, substitution, complementarity, and causal asymmetry. It does not use fsQCA as a substitute for regression. A fractional-logit model is included only as a net-effect comparison.

## Regional design

The main analysis uses a pre-specified three-bloc analytical taxonomy:

1. Northern/Western Europe
2. Southern Europe
3. Central/Eastern Europe

The same Europe-wide calibration anchors are used in every bloc. A four-bloc alternative is supplied as a robustness classification in `configs/regions.yml`.

## Repository structure

```text
.
├── configs/                 Analysis, calibration and regional taxonomies
├── data/                    Raw/interim/processed data; case-level files are gitignored
├── docs/                    Research and reproducibility protocols
├── paper/                   LaTeX manuscript scaffold
├── r/                       Optional cross-check against the CRAN QCA package
├── results/                 Generated tables and diagnostics
├── scripts/                 Data preparation helpers
├── src/euro_fsqca/          Python research package
└── tests/                   Unit and integration tests
```

## Important data-access note

World Bank Enterprise Survey microdata should not be committed to this repository. Obtain the required EU-27 files through the World Bank Enterprise Surveys / Microdata Library under the applicable access terms, place them under `data/raw/`, and run the schema inspector before mapping variables.

The repository intentionally does **not** hard-code guessed WBES variable names. Survey releases can differ. Instead, `configs/wbes_variable_map.yml` is an auditable mapping worksheet.

## Quick start with synthetic data

The synthetic demo exists only to validate the computational pipeline. It must never be used as empirical evidence.

```bash
poetry install
make validate-spec
make run-demo
```

Or without Poetry, when dependencies are already available:

```bash
PYTHONPATH=src python -m euro_fsqca.cli demo \
  --output data/processed/demo_raw.csv \
  --n 6000 \
  --seed 42

PYTHONPATH=src python -m euro_fsqca.cli run \
  --input data/processed/demo_raw.csv \
  --config configs/analysis.demo.yml \
  --output-dir results/demo
```

Generated outputs include:

- Europe-wide truth table
- region-specific truth tables
- necessity diagnostics
- conservative and parsimonious Boolean solutions
- analysis of the negated outcome
- portability of European configurations across macroregions
- threshold-sensitivity results
- fractional-logit comparison

## Working with WBES microdata

### 1. Inspect the exact release

```bash
PYTHONPATH=src python -m euro_fsqca.cli inspect \
  data/raw/<your_wbes_file>.dta \
  --output results/wbes_schema.csv
```

### 2. Complete the semantic variable mapping

Edit:

```text
configs/wbes_variable_map.yml
```

Record the exact source variables, recodes, missing-value rules, and construct definitions.

### 3. Create the analytical table

The final pre-calibration table should contain at least:

```text
firm_id, country, DIG_raw, HC_raw, FIN_raw, INT_raw, MGT_raw, EXTK_raw, INN_raw
```

The construction of every `_raw` variable must be documented and reproducible.

### 4. Set calibration anchors

Edit `configs/analysis.yml`. The placeholder anchors are not empirical recommendations. Each exclusion, crossover, and inclusion anchor needs a substantive justification.

### 5. Run the main analysis

```bash
PYTHONPATH=src python -m euro_fsqca.cli run \
  --input data/processed/wbes_eu27_analysis.csv \
  --config configs/analysis.yml \
  --output-dir results/main
```

## Main methodological safeguards

- one calibration scale for the pan-European comparison
- explicit analysis of the outcome and its negation
- separate pan-European and macroregional minimisations
- portability diagnostics for European solution terms
- threshold sensitivity instead of one arbitrary specification
- no interpretation of a regression coefficient as an fsQCA result
- raw microdata excluded from version control
- optional R/QCA cross-check for publication tables

## Boolean minimisation

The Python implementation uses exact sum-of-products minimisation for conservative and parsimonious solutions. Conservative solutions use no logical remainders. Parsimonious solutions treat unobserved truth-table rows as don't-cares while preserving observed negative rows.

For publication, intermediate solutions and directional expectations should also be checked with the CRAN `QCA` package using `r/qca_crosscheck.R`.

## Tests

```bash
make check
```

The test suite covers calibration anchors, fuzzy-set fit parameters, regional assignment, truth-table construction, minimisation, and an end-to-end synthetic run.

## Reproducibility commands

The canonical command list is maintained in `docs/reproducibility_commands.md`. Use `make run-demo` for a synthetic pipeline check, and use `make validate-data`, `make schema-audit`, `make validate-mapping`, `make check-harmonisation`, `make construct-diagnostics`, `make calibration-diagnostics`, and `make run-main` after the licensed WBES files and analytical table are available locally.

## Manuscript

The LaTeX scaffold under `paper/` mirrors the empirical workflow. It is intentionally written as a protocol rather than as fabricated results. Populate tables only after the WBES mapping and calibration decisions are frozen.

## Status

`v0.1.0` is a complete methodological scaffold with a runnable synthetic demonstration. The remaining empirical dependency is the exact EU-27 WBES microdata release and its verified variable mapping.

## Docker

A Python-only container is included for deterministic execution of the main pipeline:

```bash
docker build -t europe-fsqca-innovation .
docker run --rm europe-fsqca-innovation --help
```

Mount licensed microdata at runtime rather than copying it into the image.
