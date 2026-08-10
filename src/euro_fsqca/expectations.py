"""Directional expectations for intermediate solutions.

An intermediate solution is only defensible if the expectations that generate
it were fixed in advance from theory. This module keeps the operative polarity
in the analysis configuration, where the canonical R engine reads it, and keeps
the justification in a separate register, and then refuses to let the two
disagree.

The register also records whether the expectations are frozen. Until they are,
any intermediate solution is a development artefact rather than a result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from euro_fsqca.config import AnalysisConfig

#: Register polarity as written by a researcher, mapped to the config vocabulary.
POLARITY_TO_DIRECTION = {
    "present": "present",
    "absent": "absent",
    "unconstrained": "either",
}

#: Statuses that are not yet usable for a reported intermediate solution.
PROVISIONAL_STATUSES = {"provisional", "blocked_on_measurement"}

#: A directional claim at this status must name the argument it rests on.
ANCHORED_STATUS = "theoretical"

VALID_STATUSES = {ANCHORED_STATUS, "provisional", "blocked_on_measurement"}


class ExpectationError(ValueError):
    """Raised when the directional-expectation register is malformed."""


@dataclass(frozen=True)
class Expectation:
    """One declared directional expectation."""

    condition: str
    polarity: str
    justification: str
    basis: str
    status: str
    references: tuple[str, ...] = ()

    @property
    def direction(self) -> str:
        """Return the polarity in analysis-configuration vocabulary."""
        return POLARITY_TO_DIRECTION[self.polarity]

    @property
    def provisional(self) -> bool:
        """Return whether this expectation may not yet support a reported result."""
        return self.status in PROVISIONAL_STATUSES

    @property
    def anchored(self) -> bool:
        """Return whether the expectation names the argument it rests on."""
        return self.status == ANCHORED_STATUS and bool(self.references)


@dataclass(frozen=True)
class ExpectationRegister:
    """The complete set of declared expectations for one outcome."""

    outcome: str
    expectations: dict[str, Expectation]
    frozen: bool
    freeze_condition: str = ""

    @property
    def provisional_conditions(self) -> list[str]:
        """Return conditions whose expectation is not yet usable."""
        return sorted(name for name, item in self.expectations.items() if item.provisional)

    @property
    def unanchored_conditions(self) -> list[str]:
        """Return directional expectations with no published anchor."""
        return sorted(
            name
            for name, item in self.expectations.items()
            if item.polarity != "unconstrained" and not item.anchored
        )

    @property
    def cited_keys(self) -> set[str]:
        """Return every bibliography key the register refers to."""
        return {key for item in self.expectations.values() for key in item.references}

    @property
    def unconstrained_conditions(self) -> list[str]:
        """Return conditions for which no direction is asserted."""
        return sorted(
            name for name, item in self.expectations.items() if item.polarity == "unconstrained"
        )


def load_expectations(path: str | Path) -> ExpectationRegister:
    """Load and validate the directional-expectation register."""
    with Path(path).open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise ExpectationError("expectation register root must be a mapping")
    raw = payload.get("expectations")
    if not isinstance(raw, dict) or not raw:
        raise ExpectationError("expectation register must declare at least one expectation")

    expectations: dict[str, Expectation] = {}
    for condition, spec in raw.items():
        if not isinstance(spec, dict):
            raise ExpectationError(f"{condition}: expectation must be a mapping")
        polarity = str(spec.get("polarity", "")).strip()
        if polarity not in POLARITY_TO_DIRECTION:
            raise ExpectationError(
                f"{condition}: polarity must be present, absent or unconstrained, "
                f"not {polarity!r}"
            )
        justification = str(spec.get("justification", "")).strip()
        if polarity != "unconstrained" and not justification:
            raise ExpectationError(
                f"{condition}: a directional expectation requires a justification"
            )
        status = str(spec.get("status", "provisional")).strip()
        if status not in VALID_STATUSES:
            raise ExpectationError(
                f"{condition}: status must be one of {sorted(VALID_STATUSES)}, not {status!r}"
            )
        references = tuple(str(key).strip() for key in spec.get("references", []) or [])
        if status == ANCHORED_STATUS and not references:
            raise ExpectationError(
                f"{condition}: status {ANCHORED_STATUS!r} requires at least one reference; "
                "an expectation without a named argument is an assertion"
            )
        expectations[str(condition)] = Expectation(
            condition=str(condition),
            polarity=polarity,
            justification=justification,
            basis=str(spec.get("basis", "")).strip(),
            status=status,
            references=references,
        )

    review = payload.get("review", {}) or {}
    if not isinstance(review, dict):
        raise ExpectationError("review must be a mapping")
    return ExpectationRegister(
        outcome=str(payload.get("outcome", "")),
        expectations=expectations,
        frozen=bool(review.get("frozen", False)),
        freeze_condition=str(review.get("freeze_condition", "")).strip(),
    )


def missing_references(
    register: ExpectationRegister,
    bibliography_path: str | Path,
) -> list[str]:
    """Return cited keys that the bibliography does not define.

    A dangling citation is a justification that cannot be checked, which is the
    same problem as no justification at all.
    """
    path = Path(bibliography_path)
    if not path.exists():
        return sorted(register.cited_keys)
    text = path.read_text(encoding="utf-8")
    defined = set(re.findall(r"@\w+\{\s*([^,\s]+)\s*,", text))
    return sorted(key for key in register.cited_keys if key not in defined)


def compare_with_config(
    register: ExpectationRegister,
    config: AnalysisConfig,
) -> list[str]:
    """Return the disagreements between the register and the analysis config.

    The canonical R engine reads the polarity from the analysis configuration,
    so a register that disagrees with it would document expectations that were
    never used.
    """
    problems: list[str] = []
    if register.outcome and register.outcome != config.outcome_name:
        problems.append(
            f"register declares outcome {register.outcome!r} but the analysis "
            f"configures {config.outcome_name!r}"
        )
    for condition, spec in config.conditions.items():
        expectation = register.expectations.get(condition)
        if expectation is None:
            problems.append(f"{condition}: no directional expectation is declared")
            continue
        if expectation.direction != spec.direction:
            problems.append(
                f"{condition}: register says {expectation.polarity!r} but the analysis "
                f"configuration says {spec.direction!r}"
            )
    extra = sorted(set(register.expectations) - set(config.conditions))
    if extra:
        problems.append(
            "register declares expectations for conditions that are not analysed: "
            + ", ".join(extra)
        )
    return problems
