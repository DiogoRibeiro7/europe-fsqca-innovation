"""Generated table writing with reproducibility metadata."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from euro_fsqca.data.io import write_table


@dataclass(frozen=True)
class TableMetadata:
    """Metadata required for a generated scientific table."""

    generating_function: str
    source_dataset: str
    calibration_specification: str
    qca_specification: str
    build_id: str
    generated_at: str


def write_generated_table(
    frame: pd.DataFrame,
    path: str | Path,
    *,
    generating_function: str,
    source_dataset: str,
    calibration_specification: str,
    qca_specification: str,
    build_id: str,
) -> TableMetadata:
    """Write a table and adjacent metadata JSON."""
    target = Path(path)
    metadata = TableMetadata(
        generating_function=generating_function,
        source_dataset=source_dataset,
        calibration_specification=calibration_specification,
        qca_specification=qca_specification,
        build_id=build_id,
        generated_at=datetime.now(UTC).isoformat(),
    )
    write_table(frame, target)
    metadata_path = target.with_suffix(target.suffix + ".metadata.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
    return metadata
