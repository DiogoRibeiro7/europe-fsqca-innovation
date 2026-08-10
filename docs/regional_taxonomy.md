# Regional Taxonomy

## Primary three-bloc comparison

The project uses a research taxonomy rather than claiming an official geographic classification.

### Northern/Western Europe

Austria, Belgium, Denmark, Finland, France, Germany, Ireland, Luxembourg, Netherlands, Sweden.

### Southern Europe

Cyprus, Greece, Italy, Malta, Portugal, Spain.

### Central/Eastern Europe

Bulgaria, Croatia, Czechia, Estonia, Hungary, Latvia, Lithuania, Poland, Romania, Slovakia, Slovenia.

## Why combine North and West

The user-facing conceptual comparison is North, South, and East. Keeping Germany, France, Benelux, Austria, and the Nordic economies in one mature-system bloc avoids arbitrarily relabelling Western Europe as Northern Europe while preserving a three-way design.

## Robustness classification

`configs/regions.yml` also defines a four-bloc alternative. In that version the Baltic states are grouped with the north, and a distinct west is retained.

## Open problem: this grouping is geographic, not theoretical

As it stands the grouping is defended by geography. That cannot carry a claim
about *why* a configuration should travel between blocs, which is what the
portability contribution requires.

`docs/regional_taxonomy_theory.md` sets out the requirements an acceptable basis
must meet, assesses four candidates, and recommends innovation-system maturity
as the primary basis with position in European production networks as the
pre-declared alternative. Until that is implemented, the paper may describe a
configuration as characteristic of a geographically defined group of countries,
and may not describe it as characteristic of an innovation-system type.

`regional_taxonomy_robustness.csv` re-derives every regional solution under the
four-bloc alternative, so a finding that depends on where the boundary was drawn
is visible rather than hidden. That is a sensitivity check, not a substitute for
a theoretical basis.

## Pre-registration rule

Do not move individual countries between blocs after seeing fsQCA solutions. Any alternative grouping must be defined before comparing outcomes and reported as a robustness specification.
