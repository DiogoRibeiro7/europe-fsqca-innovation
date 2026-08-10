"""Typed configuration models for the research pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from euro_fsqca.qca.truth_table import TruthTableThresholds
from euro_fsqca.survey import WEIGHT_SCHEMES, WeightScheme

Direction = Literal["present", "absent", "either"]


class Anchors(BaseModel):
    """Direct-calibration anchors for a monotone fuzzy set."""

    exclusion: float
    crossover: float
    inclusion: float
    idm: float = Field(default=0.95, gt=0.5, lt=1.0)
    justification: str = ""

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
    direction: Direction = "either"

    @model_validator(mode="after")
    def validate_source(self) -> SetSpec:
        """Require exactly one source mechanism."""
        if (self.source is None) == (self.composite is None):
            raise ValueError("set must define exactly one of source or composite")
        return self


class TruthTableConfig(BaseModel):
    """Thresholds used to code truth-table rows.

    Row inclusion always counts sampled establishments. Weighted and
    effective-sample-size row existence are exploratory only, because making
    them canonical would put this study outside the standard procedure that
    reviewers and the CRAN ``QCA`` package implement. See
    ``docs/qca_engine_policy.md``.
    """

    frequency_cutoff: int = Field(default=5, ge=1)
    consistency_cutoff: float = Field(default=0.80, gt=0.5, le=1.0)
    pri_cutoff: float = Field(default=0.50, ge=0.0, le=1.0)

    def thresholds(self) -> TruthTableThresholds:
        """Return the runtime truth-table thresholds for the canonical analysis."""
        return TruthTableThresholds(
            frequency=self.frequency_cutoff,
            consistency=self.consistency_cutoff,
            pri=self.pri_cutoff,
            frequency_basis="cases",
        )


def _default_estimands() -> list[WeightScheme]:
    return ["unweighted"]


class SurveyDesignConfig(BaseModel):
    """Sampling-design metadata for design-aware set-theoretic analysis.

    ``primary_estimand`` selects the estimand used for the headline solution.
    ``estimands`` lists every estimand recomputed for the sensitivity table.
    """

    weight_column: str | None = None
    strata_column: str | None = None
    psu_column: str | None = None
    primary_estimand: WeightScheme = "unweighted"
    estimands: list[WeightScheme] = Field(default_factory=_default_estimands)

    @model_validator(mode="after")
    def validate_estimands(self) -> SurveyDesignConfig:
        """Require known estimands and a weight column whenever weighting is used."""
        for estimand in [self.primary_estimand, *self.estimands]:
            if estimand not in WEIGHT_SCHEMES:
                raise ValueError(f"unknown estimand: {estimand}")
        if self.primary_estimand not in self.estimands:
            self.estimands = [self.primary_estimand, *self.estimands]
        needs_weight = any(estimand != "unweighted" for estimand in self.estimands)
        if needs_weight and not self.weight_column:
            raise ValueError("weighted estimands require survey.weight_column")
        return self

    @property
    def weighted(self) -> bool:
        """Return whether the primary estimand uses survey weights."""
        return self.primary_estimand != "unweighted"


class TimingConfig(BaseModel):
    """Survey timing metadata.

    EU-27 fieldwork ran from 2018 to 2022 and standard innovation questions
    use a three-year reference window, so a 2019 and a 2021 respondent do not
    describe the same period. Timing is carried through the analysis and used
    as an explicit robustness dimension rather than silently ignored.
    """

    year_column: str | None = None
    date_column: str | None = None
    reference_period_years: int = Field(default=3, ge=1)
    periods: dict[str, list[int]] = Field(default_factory=dict)
    period_column: str = "survey_period"

    @model_validator(mode="after")
    def validate_periods(self) -> TimingConfig:
        """Reject a year assigned to more than one period."""
        seen: set[int] = set()
        for years in self.periods.values():
            for year in years:
                if year in seen:
                    raise ValueError(f"survey year {year} appears in multiple periods")
                seen.add(year)
        if self.periods and not self.year_column:
            raise ValueError("timing.periods requires timing.year_column")
        return self


class SampleFilter(BaseModel):
    """One documented inclusion rule for an analytical sample."""

    column: str
    min: float | None = None
    max: float | None = None
    isin: list[str] | None = None
    require_non_missing: bool = False
    description: str = ""

    @model_validator(mode="after")
    def validate_rule(self) -> SampleFilter:
        """Require at least one active criterion."""
        if (
            self.min is None
            and self.max is None
            and self.isin is None
            and not self.require_non_missing
        ):
            raise ValueError(f"filter on {self.column} defines no criterion")
        return self


class SampleSpec(BaseModel):
    """An analytical sample with its own population and condition set.

    Conditions that are only asked of part of the frame — management practices
    are asked of establishments with at least twenty employees — change the
    analytical population. Such conditions belong to a restricted extension
    sample rather than to the primary model.
    """

    label: str
    conditions: list[str] | None = None
    filters: list[SampleFilter] = Field(default_factory=list)
    description: str = ""
    primary: bool = False


class RobustnessConfig(BaseModel):
    """Sensitivity-grid settings."""

    enabled: bool = True
    consistency_cutoffs: list[float] = Field(default_factory=lambda: [0.78, 0.80, 0.82, 0.85])
    pri_cutoffs: list[float] = Field(default_factory=lambda: [0.50, 0.55, 0.60])
    frequency_cutoffs: list[int] = Field(default_factory=lambda: [3, 5, 8, 10])
    anchor_shift_proportions: list[float] = Field(default_factory=lambda: [-0.05, 0.0, 0.05])
    bootstrap_replicates: int = Field(default=200, ge=0)
    portability_bootstrap_replicates: int = Field(default=200, ge=0)
    # The two-stage bootstrap re-derives a source solution per replicate, so it
    # costs a truth table per replicate per region pair. It is configured
    # separately rather than silently capped.
    portability_discovery_replicates: int = Field(default=50, ge=0)
    alternative_region_scheme: str | None = None
    # Exploratory only: rebuilds the truth table on weight mass and on effective
    # sample size for comparison. It never feeds a reported solution.
    weighted_truth_table_exploration: bool = False
    random_seed: int = 42


class AnalysisConfig(BaseModel):
    """Complete empirical design configuration."""

    case_id: str
    country_column: str
    conditions: dict[str, SetSpec]
    outcome: dict[str, SetSpec]
    truth_table: TruthTableConfig = Field(default_factory=TruthTableConfig)
    robustness: RobustnessConfig = Field(default_factory=RobustnessConfig)
    survey: SurveyDesignConfig = Field(default_factory=SurveyDesignConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    samples: dict[str, SampleSpec] = Field(default_factory=dict)
    design_columns: list[str] = Field(default_factory=list)
    regions_file: str = "configs/regions.yml"
    directional_expectations_file: str | None = None
    primary_region_scheme: str = "macro3"
    status: Literal["template", "research"] = "research"

    @model_validator(mode="after")
    def validate_design(self) -> AnalysisConfig:
        """Validate sample condition sets and default to a single primary sample."""
        if not self.samples:
            self.samples = {
                "primary": SampleSpec(
                    label="primary",
                    conditions=list(self.conditions),
                    description="All configured conditions on the full analytical table.",
                    primary=True,
                )
            }
        for key, sample in self.samples.items():
            if sample.conditions is None:
                sample.conditions = list(self.conditions)
            unknown = [name for name in sample.conditions if name not in self.conditions]
            if unknown:
                raise ValueError(f"sample {key!r} references unknown conditions: {unknown}")
            if not sample.conditions:
                raise ValueError(f"sample {key!r} defines no conditions")
        if not any(sample.primary for sample in self.samples.values()):
            next(iter(self.samples.values())).primary = True
        if sum(sample.primary for sample in self.samples.values()) > 1:
            raise ValueError("exactly one sample may be marked primary")
        if self.robustness.weighted_truth_table_exploration and not self.survey.weight_column:
            raise ValueError(
                "the weighted truth-table exploration requires survey.weight_column"
            )
        return self

    @property
    def outcome_name(self) -> str:
        """Return the single configured outcome name."""
        if len(self.outcome) != 1:
            raise ValueError("exactly one outcome is required per pipeline run")
        return next(iter(self.outcome))

    @property
    def primary_sample(self) -> SampleSpec:
        """Return the sample carrying the headline analysis."""
        return next(sample for sample in self.samples.values() if sample.primary)

    @property
    def directional_expectations(self) -> dict[str, Direction]:
        """Return the directional expectation declared for each condition."""
        return {name: spec.direction for name, spec in self.conditions.items()}

    def passthrough_columns(self) -> list[str]:
        """Return every non-calibrated column the analysis must carry forward.

        Survey weights, strata, timing, sector and size are required after
        calibration for design-aware estimation and for subgroup robustness,
        so they must never be dropped when the calibrated frame is built.
        """
        columns = [
            self.survey.weight_column,
            self.survey.strata_column,
            self.survey.psu_column,
            self.timing.year_column,
            self.timing.date_column,
            *self.design_columns,
            *(
                filter_spec.column
                for sample in self.samples.values()
                for filter_spec in sample.filters
            ),
        ]
        seen: list[str] = []
        for column in columns:
            if column and column not in seen:
                seen.append(column)
        return seen


def load_config(path: str | Path) -> AnalysisConfig:
    """Load and validate a YAML analysis configuration."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    if not isinstance(payload, dict):
        raise TypeError("configuration root must be a mapping")
    return AnalysisConfig.model_validate(payload)
