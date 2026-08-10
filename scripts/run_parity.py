"""Run the R/QCA cross-check and compare it with the Python solution terms.

Usage:
    python scripts/run_parity.py --results results/main --config configs/analysis.yml

The script drives ``r/qca_crosscheck.R`` with the same analysis configuration
the Python pipeline used, then compares the two engines term by term. It exits
non-zero when any comparison fails, so parity can gate a release instead of
being asserted in prose.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from euro_fsqca.analysis.parity import (
    compare_solution_terms,
    load_python_solution_terms,
    load_r_solution_terms,
    parity_status_summary,
)
from euro_fsqca.config import load_config


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/main"))
    parser.add_argument("--config", type=Path, default=Path("configs/analysis.yml"))
    parser.add_argument("--group", default="europe", help="Analysis group directory to compare.")
    parser.add_argument("--r-output", type=Path, default=None)
    parser.add_argument("--rscript", default="Rscript")
    parser.add_argument(
        "--skip-r",
        action="store_true",
        help="Compare against an existing R output directory without re-running R.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the cross-check and write a parity report."""
    args = parse_args()
    config = load_config(args.config)
    conditions = list(config.conditions)
    group_dir = args.results / args.group
    python_terms_path = group_dir / "solution_terms.csv"
    if not python_terms_path.exists():
        print(f"missing Python solution terms: {python_terms_path}", file=sys.stderr)
        return 2

    r_output = args.r_output or (args.results / "r_validation" / args.group)
    if not args.skip_r:
        if shutil.which(args.rscript) is None:
            print(f"{args.rscript} is not available on PATH", file=sys.stderr)
            return 2
        calibrated = args.results / "calibrated_memberships.csv"
        command = [
            args.rscript,
            str(Path("r") / "qca_crosscheck.R"),
            str(calibrated),
            str(args.config),
            str(r_output),
            config.outcome_name,
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            print("R cross-check failed", file=sys.stderr)
            return completed.returncode

    r_terms_path = r_output / "solution_terms.csv"
    if not r_terms_path.exists():
        print(f"missing R solution terms: {r_terms_path}", file=sys.stderr)
        return 2

    comparison = compare_solution_terms(
        load_python_solution_terms(python_terms_path, conditions),
        load_r_solution_terms(r_terms_path, conditions),
    )
    report_path = args.results / "parity_report.csv"
    comparison.to_csv(report_path, index=False)
    summary = parity_status_summary(comparison)
    summary.to_csv(args.results / "parity_summary.csv", index=False)
    print(summary.to_string(index=False))
    print(f"parity report written to {report_path}")
    failures = comparison[comparison["status"] != "PASS"]
    if not failures.empty:
        print(f"{len(failures)} parity differences found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
