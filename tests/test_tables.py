from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from euro_fsqca.tables import write_generated_table


def test_write_generated_table_writes_metadata(tmp_path: Path) -> None:
    table = tmp_path / "table.csv"

    metadata = write_generated_table(
        pd.DataFrame({"x": [1]}),
        table,
        generating_function="test",
        source_dataset="demo",
        calibration_specification="config",
        qca_specification="qca",
        build_id="abc",
    )

    payload = json.loads((tmp_path / "table.csv.metadata.json").read_text(encoding="utf-8"))
    assert table.exists()
    assert metadata.build_id == "abc"
    assert payload["generating_function"] == "test"
