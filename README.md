# Configurational Pathways to Firm Innovation Across Europe

Research repository for a survey-design-aware fuzzy-set Qualitative Comparative Analysis (fsQCA) of firm innovation across the EU-27, testing whether capability configurations associated with high innovation are pan-European or context-dependent, and whether they **travel** between Northern/Western, Southern and Central/Eastern Europe.

Current release: `v0.3.0`

## Status: research infrastructure, no empirical results

**There are no findings in this repository, and there cannot be until the licensed EU-27 microdata is acquired.** The manifest is empty, every WBES construct mapping is unresolved, and the calibration anchors in `configs/analysis.yml` are placeholders.

This is stated in machine-checkable form rather than in prose. `configs/analysis.yml` is marked `status: template`, which makes `euro-fsqca run` refuse it, and the readiness command enumerates what is missing:

```bash
euro-fsqca readiness
```

```text
[FATAL  ] data_manifest: no WBES source files are recorded; the empirical analysis cannot start
[FATAL  ] variable_mapping: unresolved construct mappings: DIG_raw, EXTK_raw, FIN_raw, ...
[FATAL  ] analysis_config: configuration is marked as a template and is not an empirical design
[FATAL  ] calibration_anchors: placeholder 0/0.5/1 anchors remain for: DIG, EXTK, FIN, ...
[FATAL  ] survey_weights: no sampling weight column is configured, so no population claim is possible
[FATAL  ] survey_timing: no survey year column is configured; EU-27 fieldwork spans 2018-2022
```

The next milestone is not more features. It is the first version in which that command reports no blockers.

## What this repository provides

- A **survey-design-aware** fsQCA implementation: weighted consistency, coverage, PRI and necessity; weighted and effective-sample-size truth-table frequency; three explicit pooled estimands.
- **Conservative, parsimonious and intermediate** solutions with directional expectations, and core/peripheral classification.
- **Directed, term-level portability** with two-stage bootstrap uncertainty.
- Declared **analytical samples** with a recorded attrition table, so a condition asked of part of the frame cannot silently redefine the population.
- A robustness suite the pipeline actually runs: thresholds, calibration anchors, estimands, country/sector/size/period omission, alternative regional taxonomy, bootstrap stability.
- **R/QCA as the canonical engine** with automated, term-level Python-R parity.
- Data-first tooling for construct design: provenance validation, schema audit, cross-country variable-coverage audit.
- A synthetic pipeline for software validation only.

## What this repository does not include

- Raw or case-level WBES microdata.
- Verified release-specific WBES variable mappings.
- Any empirical finding about European firms.
- Justified calibration anchors.
- A populated results section.

## Research question

Which combinations of firm capabilities and resources are sufficient for high innovation across Europe, which configurations are genuinely pan-European rather than region-specific, and in which direction do regional recipes transfer?

### Conditions

- `DIG` — digital and technological capability
- `HC` — human capital
- `FIN` — financial capability
- `INT` — internationalisation
- `EXTK` — external knowledge integration
- `MGT` — management capability *(restricted sample only)*
- `INN` — high innovation performance, the outcome

The principal set relation for the primary sample is:

```text
{DIG, HC, FIN, INT, EXTK} => INN
```

The analysis is repeated for `~INN` to preserve causal asymmetry.

The condition list above is **provisional**. It must be re-derived from the variables that turn out to be comparable across the EU-27 releases before it is frozen; see `docs/research_design.md`.

### Why MGT is not in the primary model

The management module is administered to larger establishments. Requiring `MGT` would drop a large share of the frame and change the population a solution refers to. `MGT` is therefore estimated as a declared extension sample, and whether management changes the configurational structure is treated as a research question rather than an assumption.

## Survey design

WBES is a stratified probability sample with unequal inclusion probabilities, so a pooled European claim must say which population it describes. Set-theoretic metrics are weighted:

```text
Cons_w(X => Y) = sum_i w_i * min(X_i, Y_i) / sum_i w_i * X_i
```

Three estimands are reported side by side:

| Estimand | Claim |
| --- | --- |
| `unweighted` | the sampled establishments (conventional case-oriented QCA) |
| `firm_population` | the establishment population in the sampling frame |
| `equal_country` | countries weighted equally, so large member states do not determine the pooled solution |

Truth-table row inclusion counts sampled establishments, as the standard procedure does. Weight mass and Kish's effective sample size are reported per row for inspection, but they do not gate a reported solution: a non-standard `n.cut` would not be comparable with published fsQCA and could not be reproduced by the canonical R engine. Weighting is used to test whether the discovered configurations survive the design, which is the more informative question. See `docs/qca_engine_policy.md`.

## Survey timing

EU-27 fieldwork ran from 2018 to 2022 and standard innovation questions look back three years, so a 2019 and a 2021 respondent do not describe the same period, and some straddle the pandemic. Survey year, sector, size, strata and weights are carried through calibration and are used for period-stratified robustness rather than mentioned as a caveat.

## Regional design

The main analysis uses a pre-specified three-bloc analytical taxonomy: Northern/Western, Southern, and Central/Eastern Europe. The same Europe-wide calibration anchors are used in every bloc. A four-bloc alternative in `configs/regions.yml` is run by the pipeline as a robustness check.

This taxonomy is a research classification, not an official geography, and it still needs a stronger theoretical justification than proximity before publication.

## Repository structure

```text
.
├── configs/                 Analysis, calibration, samples and regional taxonomies
├── data/                    Raw/interim/processed data; case-level files are gitignored
├── docs/                    Research and reproducibility protocols
├── paper/                   LaTeX manuscript scaffold
├── r/                       Canonical CRAN QCA engine
├── results/                 Generated tables and diagnostics
├── scripts/                 Data preparation and parity helpers
├── src/euro_fsqca/          Python research package
└── tests/                   Unit and integration tests
```

## Pipeline architecture

```text
Licensed WBES files
        |
        v
data/manifest.csv ---> schema audit ---> variable-coverage audit
        |                                       |
        v                                       v
construct design ------------------------> variable mapping
        |
        v
analytical table ---> sample selection + attrition ---> calibration (design columns preserved)
        |                                                       |
        v                                                       v
survey weights (3 estimands) ---> Europe-wide QCA ---> regional QCA
        |                                                       |
        v                                                       v
directed portability + robustness ---> canonical R/QCA ---> Python-R parity
```

## Important data-access note

World Bank Enterprise Survey microdata must not be committed to this repository. Obtain the required EU-27 files through the World Bank Enterprise Surveys / Microdata Library under the applicable access terms, place them under `data/raw/`, and validate the local manifest before mapping variables.

The repository intentionally does **not** hard-code guessed WBES variable names. Survey releases differ, and `configs/wbes_variable_map.yml` is an auditable mapping worksheet, not a claim about any particular release.

## Quick start with synthetic data

The synthetic demo validates the computational pipeline. It must never be used as empirical evidence.

```bash
poetry install
make validate-spec
make run-demo
```

Or without Poetry, when dependencies are already available:

```bash
PYTHONPATH=src python -m euro_fsqca.cli demo \
  --output data/processed/demo_raw.csv --n 6000 --seed 42

PYTHONPATH=src python -m euro_fsqca.cli run \
  --input data/processed/demo_raw.csv \
  --config configs/analysis.demo.yml \
  --output-dir results/demo
```

Generated outputs include the analytical-sample attrition table, weight and timing diagnostics, Europe-wide and regional truth tables, necessity diagnostics, conservative/parsimonious/intermediate solutions with core-peripheral roles, the negated-outcome analysis, directed portability with bootstrap intervals, conjunctural dependence and substitution tests, the full robustness suite.

## Working with WBES microdata

### 1. Validate source provenance

```bash
make validate-data
```

### 2. Inspect the exact release

```bash
poetry run python -m euro_fsqca.cli inspect \
  --input data/raw/<your_wbes_file>.dta \
  --output results/wbes_schema.csv

make schema-audit
```

### 3. Find what is actually comparable

```bash
make variable-audit
```

This ranks every variable by how many country releases contain it and populate it well enough to use. **Design the constructs from this evidence.** Choosing six desired conditions and then hunting for variables that resemble them is the failure mode this step exists to prevent.

### 4. Complete the semantic variable mapping

Edit `configs/wbes_variable_map.yml`, recording exact source variables, recodes, missing-value rules and construct definitions, then:

```bash
make validate-mapping
```

### 5. Create the analytical table

The pre-calibration table must contain the identifiers, the construct inputs, **and the design columns**:

```text
firm_id, country, sampling_weight, stratum, survey_year, sector, size_class, n_employees,
DIG_raw, HC_raw, FIN_raw, INT_raw, EXTK_raw, MGT_raw, INN_raw
```

Dropping the design columns makes population inference and subgroup robustness impossible, so `calibrate_frame` preserves them.

### 6. Set the design and calibration

In `configs/analysis.yml`: fill the `survey` block with the released weight and strata variables, the `timing` block with the survey year, the sample filters with the real screener rules, and each anchor with a substantive justification. Then set `status: research`.

### 7. Check readiness, then run

```bash
make readiness
make check-harmonisation
make construct-diagnostics
make calibration-diagnostics
make run-main
make r-crosscheck
make parity
```

## Main methodological safeguards

- one calibration scale for the pan-European comparison
- explicit weighted and unweighted estimands, with the pooled estimand named
- survey weights, strata, timing, sector and size preserved through calibration
- restricted-population conditions isolated in declared extension samples
- explicit analysis of the outcome and its negation
- separate pan-European and macroregional minimisations
- directed, term-level portability with bootstrap uncertainty
- sensitivity across thresholds, anchors, estimands, subsamples and taxonomies
- no regression comparison in the main study, so no coefficient can be mistaken for a configurational result
- raw microdata excluded from version control
- R/QCA as the canonical engine, with automated parity

## Boolean minimisation

Conservative solutions use no logical remainders. Parsimonious solutions treat unobserved rows as don't-cares while preserving observed negative rows. Intermediate solutions admit only easy counterfactuals given the declared directional expectations, which is what makes core/peripheral classification available. The exact rule is documented in `docs/qca_formulas.md`.

For publication, the CRAN `QCA` package is authoritative; the Python implementation is the independent cross-check.

## Tests

```bash
make check
```

The suite covers weighted and unweighted set metrics, effective sample size, calibration anchors, sample selection and attrition, intermediate solutions and core/peripheral roles, complementarity and substitution, portability, regional assignment, truth-table construction, minimisation, parity normalisation, readiness gating, and an end-to-end synthetic run.

Python quality conventions are documented in `docs/python_quality.md`.

## Manuscript

The LaTeX scaffold under `paper/` mirrors the empirical workflow and is intentionally written as a protocol. Populate tables only after the mapping and calibration decisions are frozen and the readiness check passes.

## Docker

```bash
docker build -t europe-fsqca-innovation .
docker run --rm europe-fsqca-innovation --help
```

Mount licensed microdata at runtime rather than copying it into the image.
