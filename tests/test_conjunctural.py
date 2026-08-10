from __future__ import annotations

import numpy as np
import pandas as pd

from euro_fsqca.analysis.conjunctural import (
    condition_cooccurrence,
    conjunctural_dependence,
    term_substitutability,
)


def test_condition_cooccurrence_counts_pairs() -> None:
    result = condition_cooccurrence(
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


def test_detects_conjunctural_dependence() -> None:
    rng = np.random.default_rng(3)
    a = rng.uniform(0, 1, 400)
    b = rng.uniform(0, 1, 400)
    # The outcome follows the conjunction, so neither condition alone is
    # sufficient but their intersection is.
    frame = pd.DataFrame({"A": a, "B": b, "Y": np.minimum(a, b)})

    result = conjunctural_dependence(frame, conditions=["A", "B"], outcome="Y")

    row = result.iloc[0]
    assert row["consistency_conjunction"] > row["consistency_left"]
    assert row["consistency_conjunction"] > row["consistency_right"]
    assert row["relation"] == "conjuncturally_dependent"


def test_detects_potential_substitution() -> None:
    rng = np.random.default_rng(5)
    a = rng.uniform(0, 1, 400)
    b = rng.uniform(0, 1, 400)
    # Either condition alone produces the outcome, so they are substitutes.
    frame = pd.DataFrame({"A": a, "B": b, "Y": np.maximum(a, b)})

    result = conjunctural_dependence(frame, conditions=["A", "B"], outcome="Y")

    assert result.iloc[0]["relation"] == "potential_substitution"


def test_conjunctural_dependence_respects_weights() -> None:
    frame = pd.DataFrame(
        {
            "A": [0.9, 0.9, 0.9],
            "B": [0.9, 0.9, 0.9],
            "Y": [0.9, 0.9, 0.1],
        }
    )
    heavy_contradiction = pd.Series([1.0, 1.0, 20.0])

    unweighted = conjunctural_dependence(frame, conditions=["A", "B"], outcome="Y")
    weighted = conjunctural_dependence(
        frame, conditions=["A", "B"], outcome="Y", weights=heavy_contradiction
    )

    assert (
        weighted.iloc[0]["consistency_conjunction"]
        < unweighted.iloc[0]["consistency_conjunction"]
    )


def test_term_substitutability_finds_swapped_condition() -> None:
    terms = [
        {"DIG": True, "HC": True, "FIN": True},
        {"DIG": True, "HC": True, "INT": True},
        {"EXTK": True},
    ]

    result = term_substitutability(terms)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["shared_context"] == "DIG*HC"
    assert {row["substitute_left"], row["substitute_right"]} == {"FIN", "INT"}
