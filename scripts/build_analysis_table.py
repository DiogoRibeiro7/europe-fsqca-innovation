#!/usr/bin/env python3
r"""Build the standardised raw WBES table from the licensed source files.

This is the ingestion step, and only the ingestion step. It reads every source
file recorded in the manifest, resolves the structural metadata that each
release names differently, and preserves provenance. Analytical variables pass
through untouched.

Construct construction and calibration are deliberately *not* done here. They
depend on the schema audit and the verified variable mapping, which cannot be
completed before the real files have been inspected.

Usage:
    python scripts/build_analysis_table.py \\
        --manifest data/manifest.csv \\
        --raw-root data/raw \\
        --output data/interim/wbes_eu27_raw.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

from euro_fsqca.data.ingest import ingest_manifest, load_ingestion_spec
from euro_fsqca.data.io import write_table


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--spec", type=Path, default=Path("configs/wbes_ingestion.yml")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/wbes_eu27_raw.parquet")
    )
    parser.add_argument(
        "--report-dir", type=Path, default=Path("outputs/data")
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="Skip checksum verification. Use only while assembling the manifest.",
    )
    return parser.parse_args()


def main() -> int:
    """Run ingestion and write the standardised raw table with its reports."""
    args = parse_args()
    spec = load_ingestion_spec(args.spec)
    result = ingest_manifest(
        args.manifest,
        raw_root=args.raw_root,
        spec=spec,
        verify_checksums=not args.skip_checksums,
    )

    write_table(result.frame, args.output)
    write_table(result.resolution, args.report_dir / "ingestion_resolution.csv")
    write_table(result.sources, args.report_dir / "ingestion_sources.csv")

    unresolved = result.resolution[~result.resolution["resolved"].astype(bool)]
    print(f"Ingested {len(result.sources)} source files into {args.output}")
    print(f"Establishments: {len(result.frame)}; columns: {result.frame.shape[1]}")
    print(f"Countries: {result.frame['country'].nunique()}")
    if not unresolved.empty:
        print(
            f"Optional metadata not resolved in {len(unresolved)} source/field pairs; "
            f"see {args.report_dir / 'ingestion_resolution.csv'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
