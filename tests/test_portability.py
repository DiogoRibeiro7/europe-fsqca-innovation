from __future__ import annotations

import pandas as pd

from euro_fsqca.analysis.portability import directed_portability


def test_directed_portability_evaluates_region_pairs() -> None:
    frame = pd.DataFrame(
        {
            "macroregion": ["A", "A", "B", "B"],
            "DIG": [0.9, 0.8, 0.9, 0.2],
            "HC": [0.9, 0.8, 0.9, 0.2],
            "INN": [0.9, 0.8, 0.7, 0.1],
        }
    )

    table, matrix, network = directed_portability(
        frame,
        configurations={"A": [{"DIG": True, "HC": True}]},
        outcome="INN",
    )

    assert table.loc[0, "source_region"] == "A"
    assert table.loc[0, "target_region"] == "B"
    assert table.loc[0, "available_cases"] == 1
    assert not matrix.empty
    assert not network.empty
