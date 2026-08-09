from __future__ import annotations

from euro_fsqca.analysis.robustness import (
    classify_solution_change,
    signed_literal_jaccard,
    signed_literals,
)


def test_signed_literals_extracts_terms() -> None:
    assert signed_literals("DIG*HC + ~FIN*MGT") == {"DIG", "HC", "~FIN", "MGT"}


def test_signed_literal_jaccard_compares_structure() -> None:
    assert signed_literal_jaccard("DIG*HC", "DIG*HC") == 1.0
    assert signed_literal_jaccard("DIG*HC", "DIG*FIN") == 1 / 3


def test_classify_solution_change() -> None:
    assert classify_solution_change("DIG*HC", "DIG*HC") == "same_configuration"
    assert classify_solution_change("DIG*HC", "DIG*HC*FIN") == "one_added_condition"
    assert classify_solution_change("DIG*HC", "DIG") == "one_removed_condition"
    assert classify_solution_change("DIG", "~DIG") == "polarity_change"
