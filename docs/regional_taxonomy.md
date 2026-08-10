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

## Open problem: the taxonomy still needs theory

As it stands this grouping is defended mainly by geography and by a loose appeal
to system maturity. That is not enough to carry a claim about *why* a
configuration should travel between blocs.

Before publication the taxonomy has to be justified by something the argument
actually uses. Candidate bases, to be chosen and defended explicitly:

- national innovation-system maturity (for example institutional R&D intensity
  or public research capacity);
- financial-system structure, which bears directly on the `FIN` condition;
- position in European production networks, which bears on `INT` and `EXTK`;
- post-transition institutional history, which is the implicit basis of the
  Central/Eastern bloc.

Whichever basis is chosen must be stated before the solutions are read, must
apply consistently to every member state, and must be measurable from a source
independent of the outcome. If no such basis can be defended, the honest move is
to report country-level heterogeneity and drop the bloc language, not to keep a
grouping the theory cannot support.

`regional_taxonomy_robustness.csv` re-derives every regional solution under the
four-bloc alternative, so a finding that depends on where the boundary was drawn
is visible rather than hidden.

## Pre-registration rule

Do not move individual countries between blocs after seeing fsQCA solutions. Any alternative grouping must be defined before comparing outcomes and reported as a robustness specification.
