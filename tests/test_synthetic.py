from __future__ import annotations

from euro_fsqca.qca.minimize import minimize_truth_table
from euro_fsqca.qca.truth_table import TruthTableThresholds, build_truth_table
from euro_fsqca.synthetic import generate_known_scenario


def test_known_scenario_recovers_dig_hc_path() -> None:
    frame = generate_known_scenario("dig_hc", n=500, seed=1, noise=0.0)
    table = build_truth_table(
        frame,
        conditions=["DIG", "HC", "FIN", "INT", "MGT", "EXTK"],
        outcome="INN",
        thresholds=TruthTableThresholds(frequency=2, consistency=0.8, pri=0.5),
    )

    solution = minimize_truth_table(
        table,
        conditions=["DIG", "HC", "FIN", "INT", "MGT", "EXTK"],
        kind="parsimonious",
    )

    assert "DIG" in solution.expression
    assert "HC" in solution.expression


def test_known_scenario_supports_dual_path() -> None:
    frame = generate_known_scenario("dual_path", n=100, seed=2)

    assert {"DIG", "HC", "FIN", "INT", "MGT", "EXTK", "INN"}.issubset(frame.columns)
