from __future__ import annotations

import pandas as pd

from euro_fsqca.qca.necessity import necessity_table


def test_necessity_table_includes_negations_and_trivial_flag() -> None:
    frame = pd.DataFrame({"A": [0.9, 0.8, 0.2], "Y": [0.8, 0.7, 0.2]})

    result = necessity_table(frame, conditions=["A"], outcome="Y")

    assert set(result["label"]) == {"A", "~A"}
    assert "trivial" in result.columns
    assert "n" in result.columns
