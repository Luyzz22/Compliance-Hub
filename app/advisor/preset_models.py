"""Enterprise preset input/output models with GRC alignment.

Each preset has:
- A typed input with enterprise context (tenant, client, system)
- A typed result separating human-readable and machine-readable fields
- GRC-specific fields that downstream ISMS/GRC modules can consume

Response contract version: v1 — callers can rely on field stability.

Example consumption (SAP BTP adapter):

    resp = call_preset("/api/v1/advisor/presets/eu-ai-act-risk-assessment", body)
    if resp.grc.high_risk_likelihood == "likely":
        create_sap_grc_finding(
            risk_category=resp.grc.risk_category,
            use_case_type=resp.grc.use_case_type,
            recommendation=resp.machine.suggested_next_steps[0],
        )

Example consumption (DATEV DMS adapter):

    resp = call_preset("/api/v1/advisor/presets/nis2-obligations", body)
    create_datev_aufgabe(
        mandant=resp.context.client_id,
        pflichten=resp.grc.obligation_tags,
        hinweis=resp.human.answer_de,
    )
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.advisor.channels import AdvisorChannel, ChannelMetadata
from app.advisor.enterprise_context import EnterpriseContext
from app.advisor.errors import AdvisorError

RESPONSE_CONTRACT_VERSION = "v1"


# ---------------------------------------------------------------------------
# Shared base for all preset inputs
# ---------------------------------------------------------------------------


class PresetInputBase(BaseModel):
    """Fields shared across all preset input schemas."""

    context: EnterpriseContext = Field(default_factory=EnterpriseContext)
    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None

    # Legacy compat: callers can still set tenant_id at top level
    tenant_id: str = ""

    def effective_tenant_id(self) -> str:
        return self.context.tenant_id or self.tenant_id


# ---------------------------------------------------------------------------
# Preset 1: EU AI Act Risk Assessment
# ---------------------------------------------------------------------------


class AiActRiskPresetInput(PresetInputBase):
    """Input for EU AI Act high-risk classification assessment.

    Example:
        {
            "context": {"tenant_id": "kanzlei-mueller", "client_id": "mandant-12345"},
            "use_case_description": "KI-gestützte Kreditwürdigkeitsprüfung",
            "industry_sector": "Finanzdienstleistungen",
            "intended_purpose": "Bonitätsbewertung natürlicher Personen",
            "channel": "datev"
        }
    """

    use_case_description: str = Field(
        ...,
        min_length=10,
        max_length=4000,
    )
    industry_sector: str = ""
    intended_purpose: str = ""


class AiActRiskGrc(BaseModel):
    """GRC fields for EU AI Act risk assessment results."""

    risk_category: str = Field(
        default="unclassified",
        description="high_risk | limited_risk | minimal_risk | unclassified",
    )
    use_case_type: str = Field(
        default="",
        description="E.g. 'credit_scoring', 'recruitment', 'biometric_identification'",
    )
    high_risk_likelihood: str = Field(
        default="unknown",
        description="likely | unlikely | unclear | unknown",
    )
    annex_iii_category: str = Field(
        default="",
        description="Annex III category if applicable (e.g. '1(a) biometrics')",
    )
    conformity_assessment_required: bool | None = None


# ---------------------------------------------------------------------------
# Preset 2: NIS2 Obligations
# ---------------------------------------------------------------------------


class Nis2ObligationsPresetInput(PresetInputBase):
    """Input for NIS2 obligation mapping.

    Example:
        {
            "context": {"tenant_id": "acme-gmbh", "system_id": "WERK-SUED"},
            "entity_role": "KRITIS-naher Zulieferer",
            "sector": "Energie",
            "employee_count": "250+",
            "channel": "sap"
        }
    """

    entity_role: str = Field(..., min_length=3, max_length=500)
    sector: str = ""
    employee_count: str = ""


class Nis2ObligationsGrc(BaseModel):
    """GRC fields for NIS2 obligation results."""

    nis2_entity_type: str = Field(
        default="",
        description="essential | important | out_of_scope",
    )
    obligation_tags: list[str] = Field(
        default_factory=list,
        description=(
            "E.g. ['incident_reporting', 'risk_management', 'supply_chain', "
            "'bcm', 'governance', 'registration']"
        ),
    )
    reporting_deadlines: list[str] = Field(
        default_factory=list,
        description="E.g. ['24h_early_warning', '72h_notification']",
    )


# ---------------------------------------------------------------------------
# Preset 3: ISO 42001 Gap Check
# ---------------------------------------------------------------------------


class Iso42001GapCheckPresetInput(PresetInputBase):
    """Input for ISO 42001 gap analysis.

    Example:
        {
            "context": {"tenant_id": "tech-ag", "client_id": "", "system_id": "AI-PLATFORM-01"},
            "current_measures": "ISMS nach ISO 27001 zertifiziert, kein formales KI-Governance",
            "ai_system_count": "12",
            "channel": "web"
        }
    """

    current_measures: str = Field(..., min_length=10, max_length=4000)
    ai_system_count: str = ""


class Iso42001GapGrc(BaseModel):
    """GRC fields for ISO 42001 gap check results."""

    control_families: list[str] = Field(
        default_factory=list,
        description=(
            "Affected control families: governance, risk, data, monitoring, lifecycle, transparency"
        ),
    )
    gap_severity: str = Field(
        default="unknown",
        description="critical | major | minor | none | unknown",
    )
    iso27001_overlap: bool | None = Field(
        default=None,
        description="Whether existing ISO 27001 controls partially cover the gap",
    )


# ---------------------------------------------------------------------------
# Unified preset response
# ---------------------------------------------------------------------------


class PresetHumanReadable(BaseModel):
    """Human-readable portion of the preset response (for advisors/UI)."""

    answer_de: str = ""
    is_escalated: bool = False
    escalation_reason: str = ""
    confidence_level: str = "low"


class PresetMachineReadable(BaseModel):
    """Machine-readable portion for downstream systems (SAP/DATEV/GRC)."""

    tags: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    ref_ids: dict[str, str] = Field(default_factory=dict)
    intent: str = ""


class PresetResponseMeta(BaseModel):
    """Response metadata for tracing, caching, and versioning."""

    version: str = RESPONSE_CONTRACT_VERSION
    flow_type: str = ""
    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None
    latency_ms: float | None = None
    is_cached: bool = False
    context: EnterpriseContext = Field(default_factory=EnterpriseContext)


class PresetResult(BaseModel):
    """Enterprise-ready preset response with separated concerns.

    - ``human``: text answer for advisors and UIs
    - ``machine``: structured tags, steps, references for integrations
    - ``grc``: domain-specific GRC fields (varies per preset type)
    - ``meta``: tracing, versioning, caching metadata
    - ``error``: non-None on failure

    Contract version: v1. Fields are additive; no removals without
    version bump.
    """

    human: PresetHumanReadable = Field(default_factory=PresetHumanReadable)
    machine: PresetMachineReadable = Field(default_factory=PresetMachineReadable)
    grc: dict[str, Any] = Field(
        default_factory=dict,
        description="Preset-specific GRC fields (AiActRiskGrc, Nis2ObligationsGrc, etc.)",
    )
    meta: PresetResponseMeta = Field(default_factory=PresetResponseMeta)
    error: AdvisorError | None = None
    needs_manual_followup: bool = False
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
