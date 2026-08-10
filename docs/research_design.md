# Research Design

## Objective

Identify alternative combinations of firm capabilities and resources that are sufficient for high innovation across Europe, and determine whether those combinations travel across macroregional contexts.

## Research questions

1. Which configurations are sufficient for high firm innovation across Europe?
2. Which configurations are sufficient for low innovation?
3. Which pan-European configurations retain high consistency in Northern/Western, Southern and Central/Eastern Europe?
4. Which region-specific configurations disappear in the pooled European analysis?
5. Which capabilities behave as substitutes, complements, core conditions or peripheral conditions, and does that differ by region?
6. Does the answer change when the pooled analysis refers to the establishment population rather than to the sample?

## Unit of analysis

Establishment, using harmonised World Bank Enterprise Survey EU-27 microdata.

## Design order

The order of work is part of the design and must not be reversed:

1. acquire the licensed EU-27 microdata and record provenance in `data/manifest.csv`;
2. audit which variables are actually comparable across country releases (`euro-fsqca variable-audit`);
3. derive conceptual domains from that evidence;
4. specify a measurement model and fill `configs/wbes_variable_map.yml`;
5. justify calibration anchors from the observed distributions and from theory;
6. only then freeze the condition set.

Defining six desired conditions and then searching for WBES variables that can be made to resemble them inverts this order and produces constructs that cannot be defended. `euro-fsqca readiness` reports how far the repository has progressed through it.

## Main outcome

`INN`: fuzzy membership in the set of establishments with high innovation performance.

The exact operationalisation must be determined from the verified questionnaire and microdata dictionary. A binary product-innovation indicator should not automatically be transformed into a fuzzy outcome. Prefer a theoretically defensible graded construct when the harmonised survey content permits it. Note that standard Enterprise Survey innovation questions refer to the three years preceding the interview, so the outcome is not measured over the same window in every country.

## Candidate conditions

- `DIG`: digital and technological capability
- `HC`: human capital
- `FIN`: financial capability
- `INT`: internationalisation
- `EXTK`: external knowledge integration
- `MGT`: management capability — **restricted sample only**

## Analytical samples

The management module is administered to larger establishments, so including `MGT` in the primary model would silently redefine the analytical population. Two samples are therefore declared:

| Sample | Population | Conditions |
| --- | --- | --- |
| `primary` | broad EU-27 coverage from small establishments upwards | `DIG`, `HC`, `FIN`, `INT`, `EXTK` |
| `management_20plus` | establishments asked the management questions | the five above plus `MGT` |

`analytical_samples.csv` records establishments and weight mass surviving each rule, so the change in population is visible rather than assumed away. Whether management changes the configurational structure is itself a research question, answered by comparing the two samples, not by pooling them.

## Survey design and the pooled estimand

WBES is a stratified probability sample with unequal inclusion probabilities. A pooled European claim therefore has to say which population it refers to. Three estimands are reported (see `docs/qca_formulas.md`):

- `unweighted` — the sampled establishments, the conventional case-oriented QCA reading;
- `firm_population` — the establishment population in the sampling frame;
- `equal_country` — countries weighted equally, so the largest member states do not determine the pooled solution.

`survey.primary_estimand` names the one that carries the headline solution; `estimand_sensitivity.csv` reports all three.

## Main estimands

The central empirical object is not a marginal coefficient. It is a sufficient configuration such as:

```text
DIG*HC*INT*~FIN => INN
```

The project evaluates consistency, coverage, PRI, truth-table inclusion, Boolean minimisation, core/peripheral structure and directional configuration portability, each under a stated estimand.

## Analytical hierarchy

1. Analytical-sample construction with a recorded attrition table
2. Survey-design diagnostics: weight concentration, effective sample size, fieldwork timing
3. Pan-European necessity analysis
4. Pan-European sufficiency truth table
5. Conservative, parsimonious and intermediate minimisation, with core/peripheral classification
6. Negated-outcome analysis
7. Regional fit of unchanged pan-European solution terms
8. Independent macroregional truth tables and solutions
9. Directed term-level portability with two-stage bootstrap uncertainty
10. Complementarity and substitution tests
11. Threshold, calibration, estimand, omission, taxonomy and bootstrap robustness
12. Net-effect comparison: survey-weighted model on the observed outcome
13. Canonical R/QCA run and automated Python-R parity

## Synthetic validation

Synthetic scenarios with known sufficient configurations are available for unit tests, integration tests and documentation examples. The synthetic generator imitates the *structure* of a stratified survey — unequal weights, size and sector strata, staggered fieldwork years — so that the design-aware code paths are exercised. It imitates nothing about the substantive content of the surveys and must never be reported as a European finding.

## Interpretation rule

A regional difference is substantive only when it survives reasonable threshold and calibration perturbations, holds under more than one estimand, and is not merely a consequence of region-specific recoding or of a region-specific analytical population.
