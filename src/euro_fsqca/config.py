"""Typed configuration models for the research pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class Anchors(BaseModel):
    """Direct-calibration anchors for a monotone fuzzy set."""

    exclusion: float
    crossover: float
    inclusion: float
    idm: float = Field(default=0.95, gt=0.5, lt=1.0)

    @model_validator(mode="after")
    def validate_order(self) -> Anchors:
        """Require a strictly monotone three-anchor scale."""
        increasing = self.exclusion < self.crossover < self.inclusion
        decreasing = self.inclusion < self.crossover < self.exclusion
        if not (increasing or decreasing):
            raise ValueError("anchors must be strictly increasing or strictly decreasing")
        return self


class CompositeSpec(BaseModel):
    """Definition of a raw construct before fuzzy calibration."""

    columns: list[str]
    aggregation: Literal["mean", "weighted_mean", "min", "max"] = "mean"
    weights: list[float] | None = None
    missing: Literal["complete", "available"] = "available"

    @model_validator(mode="after")
    def validate_weights(self) -> CompositeSpec:
        """Validate weighted composites."""
        if self.aggregation == "weighted_mean" and (
            self.weights is None or len(self.weights) != len(self.columns)
        ):
            raise ValueError("weighted_mean requires one weight per column")
        return self


class SetSpec(BaseModel):
    """Specification for one calibrated condition or outcome."""

    source: str | None = None
    composite: CompositeSpec | None = None
    anchors: Anchors

    @model_validator(mode="after")
    def validate_source(self) -> SetSpec:
        """Require exactly one source mechanism."""
        if (self.source is None) == (self.composite is None):
            raise ValueError("set must define exactly one of source or composite")
        return self


class TruthTableConfig(BaseModel):
    """Thresholds used to code truth-table rows."""

    frequency_cutoff: int = Field(default=5, ge=1)
    consistency_cutoff: float = Field(default=0.80, gt=0.5, le=1.0)
    pri_cutoff: float = Field(default=0.50, ge=0.0, le=1.0)


class RobustnessConfig(BaseModel):
    """Sensitivity-grid settings."""

    enabled: bool = True
    consistency_cutoffs: list[float] = Field(default_factory=lambda: [0.78, 0.80, 0.82, 0.85])
    pri_cutoffs: list[float] = Field(default_factory=lambda: [0.50, 0.55, 0.60])
    frequency_cutoffs: list[int] = Field(default_factory=lambda: [3, 5, 8, 10])
    anchor_shift_proportions: list[float] = Field(default_factory=lambda: [-0.05, 0.0, 0.05])


class AnalysisConfig(BaseModel):
    """Complete empirical design configuration."""

    case_id: str
    country_column: str
    conditions: dict[str, SetSpec]
    outcome: dict[str, SetSpec]
    truth_table: TruthTableConfig = Field(default_factory=TruthTableConfig)
    robustness: RobustnessConfig = Field(default_factory=RobustnessConfig)
    regions_file: str = "configs/regions.yml"
    primary_region_scheme: str = "macro3"

    @property
    def outcome_name(self) -> str:
        """Return the single configured outcome name."""
        if len(self.outcome) != 1:
            raise ValueError("exactly one outcome is required per pipeline run")
        return next(iter(self.outcome))


def load_config(path: str | Path) -> AnalysisConfig:
    """Load and validate a YAML analysis configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise TypeError("configuration root must be a mapping")
    return AnalysisConfig.model_validate(payload)
