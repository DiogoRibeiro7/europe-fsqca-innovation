# Research Design

## Objective

Identify alternative combinations of firm capabilities and resources that are sufficient for high innovation across Europe and determine whether those combinations travel across macroregional contexts.

## Research questions

1. Which configurations are sufficient for high firm innovation across Europe?
2. Which configurations are sufficient for low innovation?
3. Which pan-European configurations retain high consistency in Northern/Western, Southern, and Central/Eastern Europe?
4. Which region-specific configurations disappear in the pooled European analysis?
5. Which capabilities behave as substitutes, complements, universal core conditions, or region-specific core conditions?

## Unit of analysis

Firm/establishment, using harmonised World Bank Enterprise Survey microdata.

## Main outcome

`INN`: fuzzy membership in the set of firms with high innovation performance.

The exact operationalisation must be determined from the verified questionnaire and microdata dictionary. A binary product-innovation indicator should not automatically be transformed into a fuzzy outcome. Prefer a theoretically defensible graded construct when the harmonised survey content permits it.

## Candidate conditions

- `DIG`: digital and technological capability
- `HC`: human capital
- `FIN`: financial capability
- `INT`: internationalisation
- `MGT`: management capability
- `EXTK`: external knowledge integration

Six conditions imply 64 logically possible truth-table rows, which remains interpretable while allowing equifinality.

## Main estimands

The central empirical object is not a marginal coefficient. It is a sufficient configuration such as:

```text
DIG*HC*INT*~FIN => INN
```

The project evaluates consistency, coverage, PRI, truth-table inclusion, Boolean minimisation, and configuration portability.

## Analytical hierarchy

1. Pan-European necessity analysis
2. Pan-European sufficiency truth table
3. Conservative and parsimonious minimisation
4. Negated-outcome analysis
5. Regional fit of unchanged pan-European solution terms
6. Independent macroregional truth tables and solutions
7. Threshold and calibration sensitivity
8. Net-effect comparison using fractional logit
9. Optional R/QCA intermediate-solution cross-check

## Interpretation rule

A regional difference is substantive only when it survives reasonable threshold/calibration perturbations and is not merely a consequence of region-specific recoding.
