"""Validation for WBES-to-project variable mappings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml

from euro_fsqca.data.io import write_table

VerificationStatus = Literal["verified", "conditional", "unavailable", "incompatible"]

VALID_STATUSES = {"verified", "conditional", "unavailable", "incompatible"}
REQUIRED_CANONICAL_NAMES = [
    "DIG_raw",
    "HC_raw",
    "FIN_raw",
    "INT_raw",
    "MGT_raw",
    "EXTK_raw",
    "INN_raw",
]


class MappingValidationError(ValueError):
    """Raised when a variable mapping file is incomplete or invalid."""


@dataclass(frozen=True)
class SourceVariable:
    """One verified or candidate WBES source variable."""

    source_variable: str
    country: str
    survey_year: str
    question_text_or_label: str
    transformation: str
    missing_value_rule: str
    verification_status: VerificationStatus
    notes: str = ""


@dataclass(frozen=True)
class ConstructMapping:
    """Mapping metadata for one canonical construct input."""

    canonical_project_name: str
    construct: str
    concept: str
    verification_status: VerificationStatus
    source_variables: list[SourceVariable]
    transformation: str
    missing_value_rule: str
    notes: str = ""


@dataclass(frozen=True)
class MappingValidationReport:
    """Validation summary for a variable mapping file."""

    mappings: list[ConstructMapping]
    errors: list[str]

    @property
    def ok(self) -> bool:
        """Return true when no validation errors were found."""
        return not self.errors

    @property
    def unresolved(self) -> list[ConstructMapping]:
        """Return constructs that are not ready for main empirical use."""
        return [
            mapping
            for mapping in self.mappings
            if mapping.verification_status in {"unavailable", "incompatible"}
        ]


def load_variable_mapping(path: str | Path) -> list[ConstructMapping]:
    """Load WBES variable mapping metadata from YAML."""
    mapping_path = Path(path)
    with mapping_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict) or not isinstance(payload.get("constructs"), dict):
        raise MappingValidationError("mapping file must define a constructs mapping")

    mappings: list[ConstructMapping] = []
    for canonical_name, raw_spec in payload["constructs"].items():
        if not isinstance(raw_spec, dict):
            raise MappingValidationError(f"{canonical_name} must be a mapping")
        source_variables = _parse_source_variables(canonical_name, raw_spec)
        status = _status(canonical_name, raw_spec.get("verification_status", "unavailable"))
        mappings.append(
            ConstructMapping(
                canonical_project_name=str(
                    raw_spec.get("canonical_project_name", canonical_name)
                ),
                construct=str(raw_spec.get("construct", canonical_name.removesuffix("_raw"))),
                concept=str(raw_spec.get("concept", "")),
                verification_status=status,
                source_variables=source_variables,
                transformation=str(raw_spec.get("transformation", raw_spec.get("rule", ""))),
                missing_value_rule=str(raw_spec.get("missing_value_rule", "")),
                notes=str(raw_spec.get("notes", "")),
            )
        )
    return mappings


def validate_variable_mapping(
    mappings: list[ConstructMapping],
    *,
    require_main_ready: bool = False,
) -> MappingValidationReport:
    """Validate construct mappings and optionally require empirical readiness."""
    errors: list[str] = []
    by_name = {mapping.canonical_project_name: mapping for mapping in mappings}
    for required in REQUIRED_CANONICAL_NAMES:
        if required not in by_name:
            errors.append(f"missing required canonical mapping: {required}")

    for mapping in mappings:
        if mapping.verification_status not in VALID_STATUSES:
            errors.append(
                f"{mapping.canonical_project_name} has invalid status: "
                f"{mapping.verification_status}"
            )
        if mapping.verification_status == "verified" and not mapping.source_variables:
            errors.append(
                f"{mapping.canonical_project_name} is verified without source variables"
            )
        if mapping.verification_status == "incompatible":
            errors.append(f"{mapping.canonical_project_name} is incompatible")
        for variable in mapping.source_variables:
            if variable.verification_status not in VALID_STATUSES:
                errors.append(
                    f"{mapping.canonical_project_name}/{variable.source_variable} has "
                    f"invalid status: {variable.verification_status}"
                )
            if variable.verification_status == "verified" and not (
                variable.question_text_or_label
                and variable.transformation
                and variable.missing_value_rule
            ):
                errors.append(
                    f"{mapping.canonical_project_name}/{variable.source_variable} is "
                    "verified without full documentation"
                )

        if require_main_ready and mapping.verification_status != "verified":
            errors.append(
                f"{mapping.canonical_project_name} is not verified for main analysis"
            )

    return MappingValidationReport(mappings=mappings, errors=errors)


def mapping_coverage_report(mappings: list[ConstructMapping]) -> pd.DataFrame:
    """Create a construct-level coverage report from mapping metadata."""
    rows: list[dict[str, object]] = []
    for mapping in mappings:
        usable_variables = [
            variable
            for variable in mapping.source_variables
            if variable.verification_status in {"verified", "conditional"}
        ]
        rows.append(
            {
                "canonical_project_name": mapping.canonical_project_name,
                "construct": mapping.construct,
                "verification_status": mapping.verification_status,
                "n_source_variables": len(mapping.source_variables),
                "n_usable_variables": len(usable_variables),
                "countries": ";".join(sorted({variable.country for variable in usable_variables})),
                "survey_years": ";".join(
                    sorted({variable.survey_year for variable in usable_variables})
                ),
                "main_ready": mapping.verification_status == "verified"
                and bool(usable_variables),
                "notes": mapping.notes,
            }
        )
    return pd.DataFrame(rows)


def write_mapping_coverage(mappings: list[ConstructMapping], path: str | Path) -> None:
    """Write the mapping coverage report to disk."""
    write_table(mapping_coverage_report(mappings), path)


def _parse_source_variables(
    canonical_name: str,
    raw_spec: dict[str, Any],
) -> list[SourceVariable]:
    raw_variables = raw_spec.get("source_variables", [])
    if not isinstance(raw_variables, list):
        raise MappingValidationError(f"{canonical_name}.source_variables must be a list")
    variables: list[SourceVariable] = []
    for index, item in enumerate(raw_variables, start=1):
        if not isinstance(item, dict):
            raise MappingValidationError(
                f"{canonical_name}.source_variables[{index}] must be a mapping"
            )
        variables.append(
            SourceVariable(
                source_variable=str(item.get("source_variable", "")),
                country=str(item.get("country", "")),
                survey_year=str(item.get("survey_year", "")),
                question_text_or_label=str(item.get("question_text_or_label", "")),
                transformation=str(item.get("transformation", "")),
                missing_value_rule=str(item.get("missing_value_rule", "")),
                verification_status=_status(
                    canonical_name,
                    item.get("verification_status", "unavailable"),
                ),
                notes=str(item.get("notes", "")),
            )
        )
    return variables


def _status(canonical_name: str, value: object) -> VerificationStatus:
    text = str(value)
    if text not in VALID_STATUSES:
        raise MappingValidationError(f"{canonical_name} has unknown status: {text}")
    return text  # type: ignore[return-value]
