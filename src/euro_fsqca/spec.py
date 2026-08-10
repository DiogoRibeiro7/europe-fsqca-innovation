"""Study-level specification loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from euro_fsqca.config import load_config


class ResearchSpec(BaseModel):
    """Study-level contract for a reproducible fsQCA run."""

    title: str
    unit_of_analysis: str
    analysis_config: str
    variable_mapping: str
    data_manifest: str
    regions_file: str
    primary_region_scheme: str
    robustness_region_scheme: str
    case_id: str
    country_column: str
    condition_sets: list[str] = Field(min_length=1)
    outcome_set: str
    missing_data_policy: str
    calibration_scope: str
    truth_table_policy: str
    random_seed: int | None = None
    robustness_checks: list[str] = Field(default_factory=list)
    output_root: str
    required_outputs: list[str] = Field(default_factory=list)


class SpecValidationReport(BaseModel):
    """Validation result for a study-level specification."""

    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Return whether validation found no blocking errors."""
        return not self.errors


def load_research_spec(path: str | Path) -> ResearchSpec:
    """Load and validate a YAML study-level specification."""
    spec_path = Path(path)
    with spec_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise TypeError("research specification root must be a mapping")
    return ResearchSpec.model_validate(payload)


def validate_research_spec(
    spec: ResearchSpec, *, base_dir: str | Path = "."
) -> SpecValidationReport:
    """Cross-check a study-level specification against local project files."""
    root = Path(base_dir)
    errors: list[str] = []
    warnings: list[str] = []

    for label, value in {
        "analysis_config": spec.analysis_config,
        "variable_mapping": spec.variable_mapping,
        "data_manifest": spec.data_manifest,
        "regions_file": spec.regions_file,
    }.items():
        if not (root / value).exists():
            errors.append(f"{label} does not exist: {value}")

    analysis_path = root / spec.analysis_config
    if analysis_path.exists():
        analysis_config = load_config(analysis_path)
        if spec.case_id != analysis_config.case_id:
            errors.append("case_id does not match analysis configuration")
        if spec.country_column != analysis_config.country_column:
            errors.append("country_column does not match analysis configuration")
        if spec.primary_region_scheme != analysis_config.primary_region_scheme:
            errors.append("primary_region_scheme does not match analysis configuration")
        if spec.regions_file != analysis_config.regions_file:
            errors.append("regions_file does not match analysis configuration")
        if set(spec.condition_sets) != set(analysis_config.conditions):
            errors.append("condition_sets do not match analysis configuration")
        if spec.outcome_set != analysis_config.outcome_name:
            errors.append("outcome_set does not match analysis configuration")

    regions_path = root / spec.regions_file
    if regions_path.exists():
        with regions_path.open("r", encoding="utf-8") as stream:
            regions_payload = yaml.safe_load(stream)
        if not isinstance(regions_payload, dict):
            errors.append("regions_file root must be a mapping")
        else:
            for scheme in [spec.primary_region_scheme, spec.robustness_region_scheme]:
                if scheme not in regions_payload:
                    errors.append(f"region scheme is missing: {scheme}")
            primary_regions = regions_payload.get(spec.primary_region_scheme, {})
            if isinstance(primary_regions, dict):
                countries = [
                    country for members in primary_regions.values() for country in members
                ]
                if len(countries) != len(set(countries)):
                    errors.append("primary regional taxonomy assigns at least one country twice")
            else:
                errors.append("primary regional taxonomy must be a mapping")

    output_root = Path(spec.output_root)
    if output_root.parts[:2] == ("data", "raw"):
        errors.append("output_root must not be inside data/raw")
    for relative_output in spec.required_outputs:
        output_path = output_root / relative_output
        if output_path.parts[:2] == ("data", "raw"):
            errors.append(f"required output must not be inside data/raw: {relative_output}")

    if spec.random_seed is None:
        warnings.append("random_seed is not set")

    return SpecValidationReport(errors=errors, warnings=warnings)
