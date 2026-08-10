"""Run the canonical R/QCA engine and compare it with the Python cross-check.

Usage:
    python scripts/run_parity.py --results results/main --config configs/analysis.yml

Every analysis group exports the exact cases it analysed to
``<group>/analysis_cases.csv``. R consumes that file, not the pooled table, so a
regional validation cannot silently be run against the whole European sample.

Truth-table rows and solution terms are both compared, on Boolean structure and
on numeric fit. The script exits non-zero on any difference, so parity can gate
a release instead of being asserted in prose.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from euro_fsqca.analysis.parity import (
    compare_solution_terms,
    compare_truth_tables,
    load_python_solution_terms,
    load_r_solution_terms,
    parity_status_summary,
)
from euro_fsqca.config import load_config

DEFAULT_GROUPS = ("europe",)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/main"))
    parser.add_argument("--config", type=Path, default=Path("configs/analysis.yml"))
    parser.add_argument(
        "--group",
        action="append",
        default=None,
        help="Analysis group directory to compare. Repeatable. Defaults to every "
        "group that exported an analysis_cases.csv.",
    )
    parser.add_argument("--r-output", type=Path, default=None)
    parser.add_argument("--rscript", default="Rscript")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/validation/python_r_parity.csv"),
    )
    parser.add_argument(
        "--skip-r",
        action="store_true",
        help="Compare against existing R output without re-running R.",
    )
    return parser.parse_args()


def discover_groups(results: Path) -> list[str]:
    """Return every group directory that exported its analysed cases."""
    groups = sorted(
        path.parent.name
        for path in results.glob("*/analysis_cases.csv")
    )
    return groups or list(DEFAULT_GROUPS)


def group_outcome(cases: Path, outcome: str) -> str | None:
    """Return the outcome column this group actually analysed.

    The negated-outcome group carries ``NOT_<outcome>`` rather than the
    configured outcome, and a group that carries neither cannot be compared.
    """
    columns = set(pd.read_csv(cases, nrows=1).columns)
    if outcome in columns:
        return outcome
    negated = f"NOT_{outcome}"
    return negated if negated in columns else None


def run_r(
    *,
    rscript: str,
    cases: Path,
    config: Path,
    output_dir: Path,
    outcome: str,
) -> int:
    """Run the canonical engine over one group's case file."""
    command = [
        rscript,
        str(Path("r") / "qca_crosscheck.R"),
        str(cases),
        str(config),
        str(output_dir),
        outcome,
    ]
    return subprocess.run(command, check=False).returncode


def compare_group(
    *,
    group: str,
    group_dir: Path,
    r_dir: Path,
    conditions: list[str],
) -> pd.DataFrame:
    """Compare one group's truth table and solution terms across engines."""
    frames: list[pd.DataFrame] = []

    python_truth = group_dir / "truth_table.csv"
    r_truth = r_dir / "truth_table.csv"
    if python_truth.exists() and r_truth.exists():
        present = [
            condition
            for condition in conditions
            if condition in pd.read_csv(r_truth, nrows=1).columns
        ]
        table = compare_truth_tables(
            pd.read_csv(python_truth), pd.read_csv(r_truth), conditions=present
        )
        table.insert(0, "object", "truth_table")
        frames.append(table)

    python_terms = group_dir / "solution_terms.csv"
    r_terms = r_dir / "solution_terms.csv"
    if python_terms.exists() and r_terms.exists():
        terms = compare_solution_terms(
            load_python_solution_terms(python_terms, conditions),
            load_r_solution_terms(r_terms, conditions),
        )
        terms.insert(0, "object", "solution_terms")
        frames.append(terms)

    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined.insert(0, "group", group)
    return combined


def main() -> int:
    """Run the canonical engine per group and write one parity report."""
    args = parse_args()
    config = load_config(args.config)
    conditions = list(config.conditions)
    groups = args.group or discover_groups(args.results)

    reports: list[pd.DataFrame] = []
    for group in groups:
        group_dir = args.results / group
        cases = group_dir / "analysis_cases.csv"
        if not cases.exists():
            print(f"skipping {group}: no analysis_cases.csv", file=sys.stderr)
            continue
        outcome = group_outcome(cases, config.outcome_name)
        if outcome is None:
            print(f"skipping {group}: no recognisable outcome column", file=sys.stderr)
            continue
        r_dir = (
            args.r_output
            if args.r_output is not None and len(groups) == 1
            else args.results / "r_validation" / group
        )
        if not args.skip_r:
            if shutil.which(args.rscript) is None:
                print(f"{args.rscript} is not available on PATH", file=sys.stderr)
                return 2
            code = run_r(
                rscript=args.rscript,
                cases=cases,
                config=args.config,
                output_dir=r_dir,
                outcome=outcome,
            )
            if code != 0:
                print(f"R cross-check failed for {group}", file=sys.stderr)
                return code
        report = compare_group(
            group=group, group_dir=group_dir, r_dir=r_dir, conditions=conditions
        )
        if not report.empty:
            reports.append(report)

    if not reports:
        print("no comparable outputs found", file=sys.stderr)
        return 2

    comparison = pd.concat(reports, ignore_index=True, sort=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(args.output, index=False)
    summary = parity_status_summary(comparison)
    summary.to_csv(args.output.with_name("python_r_parity_summary.csv"), index=False)
    print(summary.to_string(index=False))
    print(f"parity report written to {args.output}")

    failures = comparison[~comparison["status"].isin(["PASS", "NUMERICAL_TOLERANCE"])]
    if not failures.empty:
        print(f"\n{len(failures)} differences require documentation:", file=sys.stderr)
        for _, row in failures.head(10).iterrows():
            print(
                f"  [{row['status']}] {row['group']} {row['object']}: "
                f"{row.get('quantity') or row.get('metric')} {row.get('detail', '')}".rstrip(),
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
