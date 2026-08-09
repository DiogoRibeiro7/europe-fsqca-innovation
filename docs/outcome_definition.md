# Innovation Outcome Definition

`INN` is the primary outcome for the fsQCA design. It must be defined before substantive analysis and must not be selected because it produces a simpler QCA solution.

## Current Status

The outcome definition is not empirically verified. The repository currently contains:

- `configs/wbes_variable_map.yml`: `INN_raw` marked as `unavailable`.
- `configs/analysis.yml`: placeholder calibration anchors for `INN`.
- `configs/analysis.demo.yml`: synthetic demonstration settings only.

No final WBES source variable should be treated as selected until the schema audit and question wording review are complete.

## Required Source Review

The outcome review must separate available WBES innovation concepts when possible:

| Concept | Source variable | Country coverage | Survey year | Question text or label | Transformation | Missingness | Status |
| ------- | --------------- | ---------------- | ----------- | ---------------------- | -------------- | ----------- | ------ |
| Product innovation | Not verified | Not verified | Not verified | Not verified | Not verified | Not verified | Blocked |
| Process innovation | Not verified | Not verified | Not verified | Not verified | Not verified | Not verified | Blocked |
| Organisational innovation | Not verified | Not verified | Not verified | Not verified | Not verified | Not verified | Blocked |
| Other innovation measure | Not verified | Not verified | Not verified | Not verified | Not verified | Not verified | Blocked |

## Main Definition Decision

The main `INN` measure must be one of:

- a direct indicator;
- a documented composite;
- a fuzzy construct from multiple innovation indicators.

Decision status: blocked on verified WBES metadata.

## Calibration

The final calibration record must include:

- full non-membership anchor;
- crossover point;
- full membership anchor;
- anchor justification;
- count below full non-membership;
- count near crossover;
- count above full membership;
- count at exact `0.5`;
- country and regional distributions.

Primary regional comparisons must use the same Europe-wide calibration scale.

## Robustness Alternatives

Alternative outcome definitions may be retained for robustness only when they are theoretically and measurably defensible. They must be documented before final QCA runs.

## Limitations To Report

- Innovation items may vary by survey year or country release.
- Binary and intensity measures should not be pooled without a stated measurement model.
- Special missing codes must be handled before numeric conversion.
- Low innovation should be analysed directly as `~INN` rather than inferred from high-innovation pathways.
