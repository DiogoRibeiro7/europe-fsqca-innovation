"""Python-to-R QCA parity.

R/QCA is the canonical publication engine for truth tables and minimisation;
the Python implementation is the independent numerical cross-check. Parity is
established at the level of individual solution terms, so the two engines are
compared on the objects the paper actually reports rather than on printed
console output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

ParityStatus = Literal[
    "PASS",
    "NUMERICAL_TOLERANCE",
    "ALGORITHM_DIFFERENCE",
    "FAIL",
    "TOLERANCE_DIFFERENCE",
    "STRUCTURAL_DIFFERENCE",
    "MISSING_METRIC",
]

TERM_METRICS = ["consistency", "coverage", "pri"]

#: A difference this small is floating-point noise between two engines.
NUMERICAL_TOLERANCE = 1e-6

#: Beyond this the engines disagree about the analysis, not about rounding.
ALGORITHM_TOLERANCE = 1e-3


@dataclass(frozen=True)
class ParityTolerance:
    """Numerical tolerances for Python-to-R comparisons."""

    consistency: float = 1e-6
    coverage: float = 1e-6
    pri: float = 1e-6


def canonical_configuration(expression: str, conditions: list[str]) -> str:
    """Normalise a conjunction so Python and R terms can be matched exactly.

    The R ``QCA`` package writes negation either as a tilde or as a lowercase
    condition name depending on options and version; both are accepted here and
    rendered in the tilde form, with literals ordered by the configured
    condition order.
    """
    text = str(expression).strip()
    if not text or text in {"0", "1"}:
        return text
    lookup = {condition.upper(): condition for condition in conditions}
    order = {condition: index for index, condition in enumerate(conditions)}
    literals: list[tuple[int, str]] = []
    for token in text.split("*"):
        literal = token.strip()
        if not literal:
            continue
        negated = literal.startswith("~")
        name = literal[1:].strip() if negated else literal
        canonical = lookup.get(name.upper(), name)
        if not negated and canonical != name and canonical.upper() == name.upper():
            # A token that matches a condition only case-insensitively is the
            # lowercase notation for absence used by some QCA output settings.
            negated = True
        literals.append(
            (order.get(canonical, len(order)), f"{'~' if negated else ''}{canonical}")
        )
    return "*".join(literal for _, literal in sorted(literals))


def load_r_solution_terms(path: str | Path, conditions: list[str]) -> pd.DataFrame:
    """Load the structured term table written by ``r/qca_crosscheck.R``."""
    frame = pd.read_csv(path)
    required = {"solution", "configuration"}
    missing = required - set(frame.columns)
    if missing:
        raise KeyError(f"R solution terms are missing columns: {sorted(missing)}")
    result = frame.copy()
    result["configuration"] = result["configuration"].map(
        lambda value: canonical_configuration(value, conditions)
    )
    if "raw_coverage" in result.columns and "coverage" not in result.columns:
        result["coverage"] = result["raw_coverage"]
    return result


def load_python_solution_terms(
    path: str | Path,
    conditions: list[str],
    *,
    estimand: str | None = None,
) -> pd.DataFrame:
    """Load pipeline solution terms for comparison with R.

    R/QCA has no notion of survey weights, so parity is checked against the
    unweighted estimand; weighted set metrics are a Python-only extension and
    are reported separately.
    """
    frame = pd.read_csv(path)
    result = frame.copy()
    if "estimand" in result.columns:
        target = estimand or "unweighted"
        available = set(result["estimand"].astype(str))
        chosen = target if target in available else sorted(available)[0]
        result = result[result["estimand"].astype(str) == chosen].copy()
    result["configuration"] = result["configuration"].map(
        lambda value: canonical_configuration(value, conditions)
    )
    return result


def compare_solution_terms(
    python_terms: pd.DataFrame,
    r_terms: pd.DataFrame,
    *,
    tolerance: ParityTolerance | None = None,
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    """Compare Python and R solution terms configuration by configuration."""
    limits = tolerance or ParityTolerance()
    metric_names = metrics or TERM_METRICS
    key_columns = ["solution", "configuration"]
    for frame, label in ((python_terms, "Python"), (r_terms, "R")):
        missing = set(key_columns) - set(frame.columns)
        if missing:
            raise KeyError(f"missing {label} columns: {sorted(missing)}")

    python_subset = python_terms[
        key_columns + [column for column in metric_names if column in python_terms.columns]
    ].drop_duplicates(subset=key_columns)
    r_subset = r_terms[
        key_columns + [column for column in metric_names if column in r_terms.columns]
    ].drop_duplicates(subset=key_columns)

    merged = python_subset.merge(
        r_subset, on=key_columns, how="outer", suffixes=("_python", "_r"), indicator=True
    )
    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        key = {column: row[column] for column in key_columns}
        if row["_merge"] != "both":
            rows.append(
                {
                    **key,
                    "metric": "configuration",
                    "python_value": float("nan"),
                    "r_value": float("nan"),
                    "difference": float("nan"),
                    "status": "ALGORITHM_DIFFERENCE",
                    "detail": (
                        "term only in Python" if row["_merge"] == "left_only" else "term only in R"
                    ),
                }
            )
            continue
        for metric in metric_names:
            left_column = f"{metric}_python"
            right_column = f"{metric}_r"
            if left_column not in merged.columns or right_column not in merged.columns:
                rows.append(
                    {
                        **key,
                        "metric": metric,
                        "python_value": float("nan"),
                        "r_value": float("nan"),
                        "difference": float("nan"),
                        "status": "MISSING_METRIC",
                        "detail": "metric not reported by both engines",
                    }
                )
                continue
            left = float(row[left_column])
            right = float(row[right_column])
            difference = abs(left - right)
            limit = getattr(limits, metric, NUMERICAL_TOLERANCE)
            status = "PASS" if difference <= limit else classify_difference(difference)
            rows.append(
                {
                    **key,
                    "metric": metric,
                    "python_value": left,
                    "r_value": right,
                    "difference": difference,
                    "status": status,
                    "detail": "",
                }
            )
    return pd.DataFrame(rows)


def classify_difference(difference: float) -> ParityStatus:
    """Grade a numerical difference between the two engines."""
    if difference <= NUMERICAL_TOLERANCE:
        return "PASS"
    if difference <= ALGORITHM_TOLERANCE:
        return "NUMERICAL_TOLERANCE"
    return "ALGORITHM_DIFFERENCE"


def compare_truth_tables(
    python_table: pd.DataFrame,
    r_table: pd.DataFrame,
    *,
    conditions: list[str],
) -> pd.DataFrame:
    """Compare truth tables row by row on membership, frequency and fit.

    The R ``QCA`` package writes one row per configuration with ``OUT``, ``n``,
    ``incl`` and ``PRI``. Rows are matched on the condition bit pattern, so the
    comparison is over Boolean structure rather than over printed output.
    """
    missing_python = [column for column in conditions if column not in python_table.columns]
    missing_r = [column for column in conditions if column not in r_table.columns]
    if missing_python or missing_r:
        raise KeyError(
            f"truth tables must share the condition columns; missing "
            f"Python={missing_python} R={missing_r}"
        )

    left = python_table.copy()
    right = r_table.copy()
    for frame in (left, right):
        for condition in conditions:
            frame[condition] = frame[condition].astype(int)
    merged = left.merge(right, on=conditions, how="outer", suffixes=("_py", "_r"), indicator=True)

    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        key = {"row": "".join(str(int(row[condition])) for condition in conditions)}
        if row["_merge"] != "both":
            rows.append(
                {
                    **key,
                    "quantity": "row_membership",
                    "python_value": float("nan"),
                    "r_value": float("nan"),
                    "difference": float("nan"),
                    "status": "ALGORITHM_DIFFERENCE",
                    "detail": (
                        "row only in Python" if row["_merge"] == "left_only" else "row only in R"
                    ),
                }
            )
            continue
        for quantity, python_column, r_column in (
            ("frequency", "frequency", "n"),
            ("consistency", "consistency", "incl"),
            ("pri", "pri", "PRI"),
        ):
            if python_column not in merged.columns or r_column not in merged.columns:
                continue
            left_value = float(row[python_column])
            right_value = float(row[r_column])
            difference = abs(left_value - right_value)
            rows.append(
                {
                    **key,
                    "quantity": quantity,
                    "python_value": left_value,
                    "r_value": right_value,
                    "difference": difference,
                    "status": classify_difference(difference),
                    "detail": "",
                }
            )
        if "positive" in merged.columns and "OUT" in merged.columns:
            python_positive = bool(row["positive"])
            r_positive = str(row["OUT"]).strip() == "1"
            rows.append(
                {
                    **key,
                    "quantity": "row_inclusion",
                    "python_value": float(python_positive),
                    "r_value": float(r_positive),
                    "difference": float(python_positive != r_positive),
                    "status": "PASS" if python_positive == r_positive else "ALGORITHM_DIFFERENCE",
                    "detail": ""
                    if python_positive == r_positive
                    else f"Python OUT={int(python_positive)}, R OUT={row['OUT']}",
                }
            )
    return pd.DataFrame(rows)


def compare_qca_outputs(
    python: pd.DataFrame,
    r: pd.DataFrame,
    *,
    key_columns: list[str],
    metric_columns: list[str],
    tolerance: float = 1e-6,
) -> pd.DataFrame:
    """Compare machine-readable Python and R QCA outputs on arbitrary keys."""
    missing_python = set(key_columns + metric_columns) - set(python.columns)
    missing_r = set(key_columns + metric_columns) - set(r.columns)
    if missing_python:
        raise KeyError(f"missing Python columns: {sorted(missing_python)}")
    if missing_r:
        raise KeyError(f"missing R columns: {sorted(missing_r)}")

    merged = python.merge(
        r,
        on=key_columns,
        how="outer",
        suffixes=("_python", "_r"),
        indicator=True,
    )
    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        key = {column: row[column] for column in key_columns}
        if row["_merge"] != "both":
            rows.append({**key, "metric": "", "status": "STRUCTURAL_DIFFERENCE", "difference": ""})
            continue
        for metric in metric_columns:
            left = float(row[f"{metric}_python"])
            right = float(row[f"{metric}_r"])
            difference = abs(left - right)
            status: ParityStatus = "PASS" if difference <= tolerance else "TOLERANCE_DIFFERENCE"
            rows.append(
                {
                    **key,
                    "metric": metric,
                    "status": status,
                    "difference": difference,
                }
            )
    return pd.DataFrame(rows)


def parity_status_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    """Count comparison rows by parity status."""
    if comparison.empty:
        return pd.DataFrame(columns=["status", "n"])
    return (
        comparison.groupby("status", dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values("status")
        .reset_index(drop=True)
    )


def parity_passed(comparison: pd.DataFrame) -> bool:
    """Return whether every comparison row is within tolerance."""
    if comparison.empty:
        return False
    return bool((comparison["status"] == "PASS").all())
