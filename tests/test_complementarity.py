from __future__ import annotations

from euro_fsqca.analysis.complementarity import condition_pair_matrix


def test_condition_pair_matrix_counts_pairs() -> None:
    result = condition_pair_matrix(
        {
            "europe": [
                {"DIG": True, "HC": True, "FIN": False},
                {"DIG": True, "HC": True},
            ]
        }
    )

    pair = result[(result["left"] == "DIG") & (result["right"] == "HC")]
    assert int(pair["n_terms"].iloc[0]) == 2
    assert "positive_positive" in set(result["pair_type"])
