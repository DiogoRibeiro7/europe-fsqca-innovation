# Regional Taxonomy: Theoretical Basis

## The problem this document exists to solve

The primary taxonomy groups EU-27 member states into Northern/Western,
Southern and Central/Eastern Europe. Until now it was defended by geography and
a loose appeal to system maturity. That is not enough.

The contribution this study is aiming at is **cross-regional configurational
portability**: whether a capability recipe that works in one European context
travels to another. That claim is only meaningful if the regions differ in
something that would plausibly cause a recipe to travel or not. Geography is
not such a thing. Proximity does not explain why a configuration built on
external knowledge integration should perform differently in Poland than in
Portugal.

If no defensible basis can be established, the honest response is to drop the
bloc language and report country-level heterogeneity instead. That is a
different and smaller paper, but it is a real one.

## Requirements for an acceptable basis

Any taxonomy used in this study must satisfy all five:

1. **Declared in advance.** Fixed before regional solutions are inspected. A
   grouping adjusted after seeing which countries cluster is a description of
   the outcome, not an explanation of it.
2. **Mechanistically connected to the conditions.** It must bear on why `DIG`,
   `HC`, `FIN`, `INT` or `EXTK` would combine differently, not merely on
   whether innovation levels differ.
3. **Exogenous to the outcome.** Measured from a source independent of firm
   innovation in the WBES sample. Grouping on innovation performance and then
   discovering that innovation configurations differ is circular.
4. **Applicable to every member state.** No residual category and no country
   assigned by convenience.
5. **Stable over the fieldwork window.** Fieldwork ran 2018 to 2022. A basis
   that changed materially within that window cannot classify the sample.

## Candidate bases

### National innovation-system maturity

The most direct fit. The argument for regional heterogeneity in configurational
terms is that the same firm capability substitutes for, or depends on, different
system-level resources depending on the surrounding innovation system. Public
research capacity and institutional R&D intensity are the obvious observable
proxies.

*Assessment:* strongest mechanistic link to the research question. Requires an
external indicator, and the cut points between blocs must be justified rather
than eyeballed.

### Financial-system structure

Bears directly on `FIN`. Bank-based and market-based systems allocate
innovation finance differently, so the role of a firm's own financing capability
should differ between them.

*Assessment:* mechanistically tight but narrow. It explains one condition well
and the others hardly at all, so it is better as a moderator than as the
primary grouping.

### Position in European production networks

Bears on `INT` and `EXTK`. Whether a country's firms sit at the design end or
the assembly end of European value chains should change what external knowledge
integration and internationalisation buy them.

*Assessment:* strong link to two conditions and to the portability question
specifically, since it describes an asymmetric relationship between regions
rather than a ranking. Requires trade-in-value-added data.

### Post-transition institutional history

The implicit basis of the current Central/Eastern bloc, and the only candidate
already reflected in the grouping. It is defensible for that bloc and says
nothing about the North/West and South distinction.

*Assessment:* usable for one boundary, insufficient for the taxonomy.

## Recommendation

Use **innovation-system maturity as the primary basis**, with **position in
European production networks** as the pre-declared alternative taxonomy, since
it is the basis most directly connected to directional portability. Keep the
current geographic three-bloc grouping only as a robustness specification, and
label it as geographic rather than theoretical.

This recommendation is not yet implemented. Implementing it requires choosing
the external indicator, defending the cut points, and re-declaring the taxonomy
before any regional solution is read.

## Status

| Requirement | State |
| --- | --- |
| Declared in advance | Met: the current grouping predates any regional result |
| Mechanistically connected | **Not met**: geography is not a mechanism |
| Exogenous to the outcome | Met: no WBES outcome enters the grouping |
| Covers every member state | Met |
| Stable over 2018 to 2022 | Met |

One requirement is unmet, and it is the one that matters most for the intended
contribution.

## Consequences for the manuscript

Until this is resolved, the paper may not describe a configuration as
characteristic of an innovation-system type. It may describe it as
characteristic of a group of countries defined geographically, which is a much
weaker claim, and it must say which of the two it is doing.

`regional_taxonomy_robustness.csv` re-derives every regional solution under the
four-bloc alternative, so a finding that depends on where a boundary was drawn
is visible rather than hidden. That is a check on sensitivity, not a substitute
for a theoretical basis.

## Related

- `docs/regional_taxonomy.md` records the current grouping and the
  pre-registration rule.
- `docs/portability_analysis.md` describes what is computed once the taxonomy
  is settled.
