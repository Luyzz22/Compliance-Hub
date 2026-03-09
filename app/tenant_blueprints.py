from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ComplianceBlueprint:
    id: str
    title: str
    description: str
    frameworks: list[str]
    maturity_level: str


BLUEPRINTS: Final[list[ComplianceBlueprint]] = [
    ComplianceBlueprint(
        id="NIS2_BASELINE_MIDMARKET",
        title="NIS2-Baseline für Mittelstand",
        description="Basis-Set an Controls für NIS2/ISO 27001 im DACH-Mittelstand.",
        frameworks=["NIS2", "ISO_27001"],
        maturity_level="starter",
    ),
    ComplianceBlueprint(
        id="AI_GOVERNANCE_STARTER",
        title="AI Governance Starter (EU AI Act + ISO 42001)",
        description="Einstiegs-Blueprint für High-Level AI-Governance im Mittelstand.",
        frameworks=["EU_AI_ACT", "ISO_42001", "ISO_27001", "GDPR"],
        maturity_level="starter",
    ),
]


def preload_blueprints() -> list[ComplianceBlueprint]:
    # For now, just return the static list.
    # Later: persist to DB or cache.
    return BLUEPRINTS


def list_blueprint_ids() -> list[str]:
    return [blueprint.id for blueprint in BLUEPRINTS]
