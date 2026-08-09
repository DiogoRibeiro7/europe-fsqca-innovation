#!/usr/bin/env python3
"""Template for building the canonical WBES analytical table.

This script intentionally refuses to guess WBES variable names. After running
`euro-fsqca inspect`, replace the placeholders below with exact verified source
variables and recoding logic from the selected survey release.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from euro_fsqca.data.io import read_table, write_table

REQUIRED_CANONICAL = [
    "firm_id",
    "country",
    "DIG_raw",
    "HC_raw",
    "FIN_raw",
    "INT_raw",
    "MGT_raw",
    "EXTK_raw",
    "INN_raw",
]


def build_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Build the canonical pre-calibration table after source mapping is frozen."""
    raise NotImplementedError(
        "Map the exact WBES release to canonical constructs first. "
        "See configs/wbes_variable_map.yml and docs/wbes_variable_mapping.md."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = read_table(args.input)
    result = build_table(raw)
    missing = [column for column in REQUIRED_CANONICAL if column not in result.columns]
    if missing:
        raise ValueError(f"canonical output is missing columns: {missing}")
    write_table(result[REQUIRED_CANONICAL], args.output)


if __name__ == "__main__":
    main()
