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
    primary_sample: str | None = None
    extension_samples: list[str] = Field(default_factory=list)
    primary_estimand: str | None = None
    estimands: list[str] = Field(default_factory=list)
    missing_data_policy: str
    calibration_scope: str
    truth_table_policy: str
    survey_design_policy: str | None = None
    timing_policy: str | None = None
    canonical_qca_engine: str | None = None
    python_role: str | None = None
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
        primary_sample = analysis_config.primary_sample
        if set(spec.condition_sets) != set(primary_sample.conditions or []):
            errors.append("condition_sets do not match the primary sample of the analysis config")
        if spec.outcome_set != analysis_config.outcome_name:
            errors.append("outcome_set does not match analysis configuration")
        if spec.primary_sample and spec.primary_sample != primary_sample.label:
            errors.append("primary_sample does not match analysis configuration")
        declared_extensions = {
            sample.label for sample in analysis_config.samples.values() if not sample.primary
        }
        if spec.extension_samples and set(spec.extension_samples) != declared_extensions:
            errors.append("extension_samples do not match analysis configuration")
        primary_estimand = analysis_config.survey.primary_estimand
        if spec.primary_estimand and spec.primary_estimand != primary_estimand:
            errors.append("primary_estimand does not match analysis configuration")
        if spec.estimands and set(spec.estimands) != set(analysis_config.survey.estimands):
            errors.append("estimands do not match analysis configuration")
        if analysis_config.status == "template":
            warnings.append(
                "analysis configuration is marked as a template: no empirical run is possible yet"
            )
        if analysis_config.survey.weight_column is None:
            warnings.append(
                "no survey weight column is configured, so results describe the sampled "
                "establishments rather than the establishment population"
            )
        if analysis_config.timing.year_column is None:
            warnings.append(
                "no survey year column is configured, so fieldwork timing is not carried"
            )

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
