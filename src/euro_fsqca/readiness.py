"""Empirical-readiness assessment.

A repository can pass every unit test, build every figure and still have no
research in it. This module makes that state machine-checkable: it reports the
blockers that stand between the current tree and a defensible empirical run, so
that "the pipeline executes" is never mistaken for "the study was done".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from euro_fsqca.config import AnalysisConfig, load_config
from euro_fsqca.data.mapping import load_variable_mapping
from euro_fsqca.data.provenance import load_manifest
from euro_fsqca.expectations import (
    ExpectationError,
    compare_with_config,
    load_expectations,
)

FATAL = "fatal"
WARNING = "warning"
OK = "ok"

PLACEHOLDER_ANCHORS = (0.0, 0.5, 1.0)


@dataclass(frozen=True)
class ReadinessItem:
    """One readiness check and its verdict."""

    check: str
    status: str
    detail: str


def assess_readiness(
    *,
    config_path: str | Path,
    mapping_path: str | Path,
    manifest_path: str | Path,
    raw_root: str | Path = "data/raw",
    schema_audit_path: str | Path = "outputs/data/schema_audit.csv",
) -> pd.DataFrame:
    """Return a table of readiness checks for an empirical run."""
    items: list[ReadinessItem] = []
    config: AnalysisConfig | None = None
    try:
        config = load_config(config_path)
    except Exception as exc:  # pragma: no cover - surfaced through the CLI
        items.append(ReadinessItem("analysis_config", FATAL, f"cannot load config: {exc}"))

    items.append(_check_manifest(manifest_path, raw_root))
    items.append(_check_schema_audit(schema_audit_path))
    items.extend(_check_mapping(mapping_path))
    if config is not None:
        items.extend(_check_config(config))
    return pd.DataFrame(
        [{"check": item.check, "status": item.status, "detail": item.detail} for item in items]
    )


def readiness_blockers(report: pd.DataFrame) -> list[str]:
    """Return the fatal blockers recorded in a readiness report."""
    if report.empty:
        return []
    fatal = report[report["status"] == FATAL]
    return [f"{row['check']}: {row['detail']}" for _, row in fatal.iterrows()]


def _check_manifest(manifest_path: str | Path, raw_root: str | Path) -> ReadinessItem:
    path = Path(manifest_path)
    if not path.exists():
        return ReadinessItem("data_manifest", FATAL, f"missing manifest: {manifest_path}")
    try:
        entries = load_manifest(path)
    except Exception as exc:
        return ReadinessItem("data_manifest", FATAL, f"unreadable manifest: {exc}")
    if not entries:
        return ReadinessItem(
            "data_manifest",
            FATAL,
            "no WBES source files are recorded; the empirical analysis cannot start",
        )
    missing = [
        entry.file_name
        for entry in entries
        if not (Path(raw_root) / entry.relative_path).exists()
        and not entry.relative_path.is_absolute()
    ]
    if missing:
        return ReadinessItem(
            "data_manifest",
            FATAL,
            f"{len(missing)} recorded source files are not present under {raw_root}",
        )
    return ReadinessItem("data_manifest", OK, f"{len(entries)} source files recorded and present")


def _check_schema_audit(schema_audit_path: str | Path) -> ReadinessItem:
    path = Path(schema_audit_path)
    if not path.exists():
        return ReadinessItem(
            "schema_audit",
            FATAL,
            f"no schema audit at {schema_audit_path}; run it against the real releases "
            "before mapping any variable",
        )
    try:
        audit = pd.read_csv(path)
    except Exception as exc:
        return ReadinessItem("schema_audit", FATAL, f"unreadable schema audit: {exc}")
    if audit.empty:
        return ReadinessItem("schema_audit", FATAL, "the schema audit is empty")
    sources = int(audit["source_name"].nunique()) if "source_name" in audit.columns else 0
    return ReadinessItem(
        "schema_audit",
        OK,
        f"schema audit covers {sources} source files",
    )


def _check_mapping(mapping_path: str | Path) -> list[ReadinessItem]:
    path = Path(mapping_path)
    if not path.exists():
        return [ReadinessItem("variable_mapping", FATAL, f"missing mapping: {mapping_path}")]
    try:
        mappings = load_variable_mapping(path)
    except Exception as exc:
        return [ReadinessItem("variable_mapping", FATAL, f"unreadable mapping: {exc}")]
    unresolved = [
        mapping.canonical_project_name
        for mapping in mappings
        if mapping.verification_status != "verified" or not mapping.source_variables
    ]
    if unresolved:
        return [
            ReadinessItem(
                "variable_mapping",
                FATAL,
                "unresolved construct mappings: " + ", ".join(sorted(unresolved)),
            )
        ]
    return [ReadinessItem("variable_mapping", OK, f"{len(mappings)} constructs verified")]


def _check_config(config: AnalysisConfig) -> list[ReadinessItem]:
    items: list[ReadinessItem] = []
    if config.status == "template":
        items.append(
            ReadinessItem(
                "analysis_config",
                FATAL,
                "configuration is marked as a template and is not an empirical design",
            )
        )
    else:
        items.append(ReadinessItem("analysis_config", OK, "configuration is marked as research"))

    specs = {**config.conditions, **config.outcome}
    placeholder = [
        name
        for name, spec in specs.items()
        if (spec.anchors.exclusion, spec.anchors.crossover, spec.anchors.inclusion)
        == PLACEHOLDER_ANCHORS
    ]
    if placeholder:
        items.append(
            ReadinessItem(
                "calibration_anchors",
                FATAL,
                "placeholder 0/0.5/1 anchors remain for: " + ", ".join(sorted(placeholder)),
            )
        )
    else:
        unjustified = sorted(name for name, spec in specs.items() if not spec.anchors.justification)
        items.append(
            ReadinessItem(
                "calibration_anchors",
                WARNING if unjustified else OK,
                "anchors without a recorded justification: " + ", ".join(unjustified)
                if unjustified
                else "all anchors carry a justification",
            )
        )

    if not config.survey.weight_column:
        items.append(
            ReadinessItem(
                "survey_weights",
                FATAL,
                "no sampling weight column is configured, so no population claim is possible",
            )
        )
    else:
        items.append(
            ReadinessItem(
                "survey_weights",
                OK if len(config.survey.estimands) > 1 else WARNING,
                f"weight column {config.survey.weight_column} with estimands "
                + ", ".join(config.survey.estimands),
            )
        )

    if not config.timing.year_column:
        items.append(
            ReadinessItem(
                "survey_timing",
                FATAL,
                "no survey year column is configured; EU-27 fieldwork spans 2018-2022",
            )
        )
    else:
        items.append(
            ReadinessItem(
                "survey_timing",
                OK if config.timing.periods else WARNING,
                "survey year is carried through; "
                + ("periods declared" if config.timing.periods else "no periods declared"),
            )
        )

    primary = config.primary_sample
    primary_conditions = list(primary.conditions or [])
    if len(primary_conditions) < 2:
        items.append(
            ReadinessItem(
                "condition_set",
                FATAL,
                "the primary sample defines fewer than two conditions, so there is no "
                "configuration to analyse",
            )
        )
    else:
        items.append(
            ReadinessItem(
                "condition_set",
                OK,
                f"primary sample {primary.label} analyses " + ", ".join(primary_conditions),
            )
        )

    # A condition measured on part of the frame must be confined to a sample
    # whose eligibility rule is executable, not described in a comment.
    unfiltered = sorted(
        sample.label
        for sample in config.samples.values()
        if not sample.primary and not sample.filters
    )
    if unfiltered:
        items.append(
            ReadinessItem(
                "sample_filters",
                FATAL,
                "restricted samples declare no executable filters: " + ", ".join(unfiltered)
                + ". Encode the questionnaire eligibility rule or remove the sample.",
            )
        )
    else:
        items.append(
            ReadinessItem(
                "sample_filters",
                OK,
                f"{len(config.samples)} samples declared with executable inclusion rules",
            )
        )

    items.append(_check_expectations(config))
    return items


def _check_expectations(config: AnalysisConfig) -> ReadinessItem:
    """Check the directional-expectation register behind intermediate solutions."""
    undirected = sorted(
        name for name, spec in config.conditions.items() if spec.direction == "either"
    )
    if config.directional_expectations_file is None:
        return ReadinessItem(
            "directional_expectations",
            WARNING,
            "no expectation register is declared; intermediate solutions rest on "
            "undocumented directional claims"
            + (f" (unconstrained: {', '.join(undirected)})" if undirected else ""),
        )

    path = Path(config.directional_expectations_file)
    if not path.exists():
        return ReadinessItem(
            "directional_expectations",
            FATAL,
            f"missing expectation register: {config.directional_expectations_file}",
        )
    try:
        register = load_expectations(path)
    except ExpectationError as exc:
        return ReadinessItem("directional_expectations", FATAL, str(exc))

    problems = compare_with_config(register, config)
    if problems:
        return ReadinessItem(
            "directional_expectations",
            FATAL,
            "the expectation register and the analysis configuration disagree: "
            + "; ".join(problems),
        )
    if not register.frozen:
        return ReadinessItem(
            "directional_expectations",
            FATAL,
            "the expectation register is not frozen"
            + (
                f" (still provisional: {', '.join(register.provisional_conditions)})"
                if register.provisional_conditions
                else ""
            )
            + "; an intermediate solution derived from unfrozen expectations is a "
            "development artefact, not a result",
        )
    return ReadinessItem(
        "directional_expectations",
        OK,
        f"{len(register.expectations)} expectations frozen"
        + (f"; unconstrained: {', '.join(register.unconstrained_conditions)}"
           if register.unconstrained_conditions else ""),
    )
