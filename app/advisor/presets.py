"""Advisor preset micro-flows for DATEV/SAP-aligned use cases.

Each preset defines:
- A flow_type identifier for evidence/metrics tagging
- Input schema with channel-specific metadata
- Query shaping: builds the natural-language query from structured input
- Extra tags to force-include in the response

Presets are thin wrappers around the generic advisor service — no separate
business logic, just prompt/context shaping.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.advisor.channels import AdvisorChannel, ChannelMetadata


class FlowType(StrEnum):
    eu_ai_act_risk_assessment = "eu_ai_act_risk_assessment"
    nis2_obligations = "nis2_obligations"
    iso42001_gap_check = "iso42001_gap_check"


# ---------------------------------------------------------------------------
# Preset 1: EU AI Act Risk Assessment
# ---------------------------------------------------------------------------


class EuAiActRiskAssessmentInput(BaseModel):
    """Input for the 'Is my AI use case high-risk?' preset."""

    use_case_description: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Description of the planned AI use case",
    )
    industry_sector: str = Field(
        default="",
        description="Industry sector (e.g. 'Finanzdienstleistungen', 'Gesundheit')",
    )
    intended_purpose: str = Field(
        default="",
        description="Intended purpose of the AI system",
    )
    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str = ""


def build_eu_ai_act_risk_query(inp: EuAiActRiskAssessmentInput) -> str:
    parts = [
        "Ist der folgende geplante KI-Anwendungsfall voraussichtlich "
        "hochrisikorelevant nach dem EU AI Act (Verordnung 2024/1689)?",
        f"\nAnwendungsfall: {inp.use_case_description}",
    ]
    if inp.industry_sector:
        parts.append(f"Branche: {inp.industry_sector}")
    if inp.intended_purpose:
        parts.append(f"Zweckbestimmung: {inp.intended_purpose}")
    parts.append(
        "\nBitte bewerte anhand Art. 6 und Anhang III, ob eine "
        "Hochrisiko-Klassifizierung wahrscheinlich ist, und nenne "
        "die relevanten Kriterien."
    )
    return "\n".join(parts)


EU_AI_ACT_RISK_EXTRA_TAGS = ["eu_ai_act", "high_risk", "conformity_assessment"]


# ---------------------------------------------------------------------------
# Preset 2: NIS2 Obligations
# ---------------------------------------------------------------------------


class Nis2ObligationsInput(BaseModel):
    """Input for the 'What NIS2 obligations apply?' preset."""

    entity_role: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description=(
            "Role of the entity (e.g. 'KRITIS-naher Zulieferer', "
            "'Betreiber wesentlicher Dienste', 'Digitaler Dienstleister')"
        ),
    )
    sector: str = Field(
        default="",
        description="Sector (e.g. 'Energie', 'Transport', 'Digitale Infrastruktur')",
    )
    employee_count: str = Field(
        default="",
        description="Approximate size (e.g. '50-249', '250+')",
    )
    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str = ""


def build_nis2_obligations_query(inp: Nis2ObligationsInput) -> str:
    parts = [
        "Welche NIS2-Pflichten (Richtlinie 2022/2555) betreffen "
        f"eine Organisation mit der Rolle '{inp.entity_role}'?",
    ]
    if inp.sector:
        parts.append(f"Sektor: {inp.sector}")
    if inp.employee_count:
        parts.append(f"Größenordnung: {inp.employee_count} Mitarbeiter")
    parts.append(
        "\nBitte nenne die wesentlichen Pflichten (Meldepflichten, "
        "Risikomanagement, Governance) und relevante Fristen."
    )
    return "\n".join(parts)


NIS2_OBLIGATIONS_EXTRA_TAGS = ["nis2", "incident_reporting", "risk_management"]


# ---------------------------------------------------------------------------
# Preset 3: ISO 42001 Gap Check
# ---------------------------------------------------------------------------


class Iso42001GapCheckInput(BaseModel):
    """Input for the 'ISO 42001 gap check' preset."""

    current_measures: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Description of current AI governance measures in place",
    )
    ai_system_count: str = Field(
        default="",
        description="Number of AI systems in scope",
    )
    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None
    tenant_id: str = ""


def build_iso42001_gap_query(inp: Iso42001GapCheckInput) -> str:
    parts = [
        "Welche Lücken bestehen voraussichtlich gegenüber "
        "ISO 42001 (AI Management System) bei folgenden "
        "aktuellen Governance-Maßnahmen?",
        f"\nAktuelle Maßnahmen: {inp.current_measures}",
    ]
    if inp.ai_system_count:
        parts.append(f"Anzahl KI-Systeme im Scope: {inp.ai_system_count}")
    parts.append(
        "\nBitte identifiziere die wichtigsten Lücken und priorisiere Handlungsempfehlungen."
    )
    return "\n".join(parts)


ISO42001_GAP_EXTRA_TAGS = ["iso_42001", "risk_management", "conformity_assessment"]


# ---------------------------------------------------------------------------
# Registry for preset resolution
# ---------------------------------------------------------------------------

PRESET_REGISTRY: dict[FlowType, dict[str, Any]] = {
    FlowType.eu_ai_act_risk_assessment: {
        "build_query": build_eu_ai_act_risk_query,
        "extra_tags": EU_AI_ACT_RISK_EXTRA_TAGS,
        "input_model": EuAiActRiskAssessmentInput,
    },
    FlowType.nis2_obligations: {
        "build_query": build_nis2_obligations_query,
        "extra_tags": NIS2_OBLIGATIONS_EXTRA_TAGS,
        "input_model": Nis2ObligationsInput,
    },
    FlowType.iso42001_gap_check: {
        "build_query": build_iso42001_gap_query,
        "extra_tags": ISO42001_GAP_EXTRA_TAGS,
        "input_model": Iso42001GapCheckInput,
    },
}
