from __future__ import annotations

import pandas as pd

from euro_fsqca.analysis.parity import (
    select_comparable_model,
    solution_ambiguity,
)

CONDITIONS = ["DEMOC", "ETHFRACT", "GEOCON", "POLDIS", "NATPRIDE"]

# The four equally minimal parsimonious models QCA returns for the CVF data,
# captured from a real run of r/qca_crosscheck.R. ~NATPRIDE and
# DEMOC*GEOCON*POLDIS appear in every model; the rest appear in some.
CVF_MODELS = {
    1: ["~NATPRIDE", "~DEMOC*ETHFRACT*POLDIS", "DEMOC*ETHFRACT*GEOCON", "DEMOC*GEOCON*POLDIS"],
    2: ["~NATPRIDE", "~DEMOC*ETHFRACT*POLDIS", "DEMOC*ETHFRACT*~POLDIS", "DEMOC*GEOCON*POLDIS"],
    3: ["~NATPRIDE", "DEMOC*ETHFRACT*GEOCON", "DEMOC*GEOCON*POLDIS", "ETHFRACT*GEOCON*POLDIS"],
    4: ["~NATPRIDE", "DEMOC*ETHFRACT*~POLDIS", "DEMOC*GEOCON*POLDIS", "ETHFRACT*GEOCON*POLDIS"],
}


def _r_terms() -> pd.DataFrame:
    rows = [
        {"solution": "parsimonious", "model": model, "configuration": configuration}
        for model, configurations in CVF_MODELS.items()
        for configuration in configurations
    ]
    return pd.DataFrame(rows)


def test_ambiguity_separates_invariant_from_model_specific_terms() -> None:
    ambiguity = solution_ambiguity(_r_terms())

    status = dict(zip(ambiguity["configuration"], ambiguity["status"], strict=True))
    # Present in all four models: the finding does not depend on model choice.
    assert status["~NATPRIDE"] == "invariant"
    assert status["DEMOC*GEOCON*POLDIS"] == "invariant"
    # Present in two of four: reporting it as the result would be a choice.
    assert status["DEMOC*ETHFRACT*GEOCON"] == "partial"
    assert status["~DEMOC*ETHFRACT*POLDIS"] == "partial"
    assert set(ambiguity["n_models"]) == {4}


def test_ambiguity_records_which_models_contain_each_term() -> None:
    ambiguity = solution_ambiguity(_r_terms())

    row = ambiguity[ambiguity["configuration"] == "DEMOC*ETHFRACT*GEOCON"].iloc[0]
    assert row["models"] == "1;3"
    assert row["model_share"] == 0.5


def test_single_model_solutions_are_marked_as_such() -> None:
    terms = pd.DataFrame(
        {
            "solution": ["conservative", "conservative"],
            "model": [1, 1],
            "configuration": ["DIG*HC", "FIN*INT"],
        }
    )

    ambiguity = solution_ambiguity(terms)

    assert set(ambiguity["status"]) == {"single_model"}


def test_ambiguity_is_empty_without_a_model_column() -> None:
    terms = pd.DataFrame({"solution": ["conservative"], "configuration": ["DIG*HC"]})

    assert solution_ambiguity(terms).empty


def test_comparison_uses_the_model_python_reproduced() -> None:
    python_terms = pd.DataFrame(
        {
            "solution": ["parsimonious"] * 4,
            "configuration": CVF_MODELS[3],
        }
    )

    chosen = select_comparable_model(
        python_terms, _r_terms(), solution="parsimonious", conditions=CONDITIONS
    )

    # Comparing against model 1 would report ambiguity as disagreement.
    assert chosen == 3


def test_comparison_falls_back_to_the_first_model_when_nothing_matches() -> None:
    python_terms = pd.DataFrame(
        {"solution": ["parsimonious"], "configuration": ["DEMOC*ETHFRACT"]}
    )

    chosen = select_comparable_model(
        python_terms, _r_terms(), solution="parsimonious", conditions=CONDITIONS
    )

    assert chosen == 1


def test_r_script_exports_every_model_not_only_the_first() -> None:
    from pathlib import Path

    content = (Path(__file__).resolve().parents[1] / "r" / "qca_crosscheck.R").read_text(
        encoding="utf-8"
    )

    # The defect being guarded against: solution$solution[[1]] taken alone.
    assert "for (index in seq_along(solution$solution))" in content
    assert "model = index" in content
    assert "n_models = length(solution$solution)" in content
    assert "IC$individual" in content
