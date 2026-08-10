# Python-R Validation

R is an independent validation layer for QCA results. Python remains the main data-processing and analysis implementation.

## Exchange Files

Python should export:

- calibrated membership data;
- truth-table specification;
- Python truth table;
- Python solution summaries;
- term-level fit tables.

R reads the exported calibrated data and independently writes:

- `truth_table.csv`;
- `solutions.csv`;
- text captures for manual inspection.

## Comparison Statuses

Machine-readable comparisons use:

- `PASS`: same structure and metrics within tolerance;
- `TOLERANCE_DIFFERENCE`: same structure but metric differences exceed tolerance;
- `STRUCTURAL_DIFFERENCE`: rows or solution structures do not align;
- `FAIL`: validation could not run.

## Tolerances

Default numerical tolerance is `1e-6` for consistency, coverage, and PRI. If Python and R differ because of documented algorithmic conventions, record that difference instead of forcing text equality.

## Required Reports

The Europe-wide solution and each main regional solution need an R validation report before being used as substantive evidence.

## Environment Setup

Use the R setup check before cross-validation:

```bash
make r-check-env
```

Install the R dependencies explicitly when the check reports missing packages:

```bash
make r-setup
```

Run the cross-check after Python has exported calibrated memberships:

```bash
make r-crosscheck
```
