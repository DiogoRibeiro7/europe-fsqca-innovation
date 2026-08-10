from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.figures import write_bar_svg, write_heatmap_svg


def test_write_heatmap_svg(tmp_path: Path) -> None:
    output = tmp_path / "heatmap.svg"
    frame = pd.DataFrame({"source": ["A"], "target": ["B"], "value": [0.8]})

    write_heatmap_svg(frame, row="source", column="target", value="value", output=output, title="T")

    assert output.exists()
    assert "<svg" in output.read_text(encoding="utf-8")


def test_write_bar_svg(tmp_path: Path) -> None:
    output = tmp_path / "bars.svg"
    frame = pd.DataFrame({"label": ["A"], "value": [0.5]})

    write_bar_svg(frame, label="label", value="value", output=output, title="T")

    assert output.exists()
    assert "<rect" in output.read_text(encoding="utf-8")
