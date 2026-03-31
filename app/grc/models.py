"""GRC core entities — lightweight write-model for compliance artefacts.

These entities are created by advisor presets and represent structured
compliance records that downstream systems (SAP GRC, DATEV DMS, ISMS
tools) can consume.

Schema is intentionally small and additive. Status lifecycle enables
simple workflows without a full state machine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------


class RiskStatus(StrEnum):
    open = "open"
    accepted = "accepted"
    superseded = "superseded"


class ObligationStatus(StrEnum):
    identified = "identified"
    in_progress = "in_progress"
    fulfilled = "fulfilled"


class GapStatus(StrEnum):
    open = "open"
    remediation_planned = "remediation_planned"
    closed = "closed"


# ---------------------------------------------------------------------------
# Entity 1: AI Risk Assessment
# ---------------------------------------------------------------------------


class AiRiskAssessment(BaseModel):
    """EU AI Act risk assessment record."""

    id: str = Field(default_factory=lambda: _new_id("RISK"))
    tenant_id: str = ""
    client_id: str = ""
    system_id: str = ""

    risk_category: str = "unclassified"
    use_case_type: str = ""
    high_risk_likelihood: str = "unknown"
    annex_iii_category: str = ""
    conformity_assessment_required: bool | None = None

    status: RiskStatus = RiskStatus.open
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    source_preset_type: str = "eu_ai_act_risk_assessment"
    source_event_id: str = ""
    source_trace_id: str = ""
    source_version: str = "v1"

    tags: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def idempotency_key(self) -> str:
        return f"{self.tenant_id}:{self.client_id}:{self.system_id}:ai_risk"


# ---------------------------------------------------------------------------
# Entity 2: NIS2 Obligation Record
# ---------------------------------------------------------------------------


class Nis2ObligationRecord(BaseModel):
    """NIS2 obligation tracking record."""

    id: str = Field(default_factory=lambda: _new_id("NIS2"))
    tenant_id: str = ""
    client_id: str = ""
    system_id: str = ""

    nis2_entity_type: str = ""
    obligation_tags: list[str] = Field(default_factory=list)
    reporting_deadlines: list[str] = Field(default_factory=list)
    entity_role: str = ""
    sector: str = ""

    status: ObligationStatus = ObligationStatus.identified
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    source_preset_type: str = "nis2_obligations"
    source_event_id: str = ""
    source_trace_id: str = ""
    source_version: str = "v1"

    tags: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def idempotency_key(self) -> str:
        return f"{self.tenant_id}:{self.client_id}:{self.system_id}:nis2"


# ---------------------------------------------------------------------------
# Entity 3: ISO 42001 Gap Record
# ---------------------------------------------------------------------------


class Iso42001GapRecord(BaseModel):
    """ISO 42001 AI management system gap record."""

    id: str = Field(default_factory=lambda: _new_id("GAP"))
    tenant_id: str = ""
    client_id: str = ""
    system_id: str = ""

    control_families: list[str] = Field(default_factory=list)
    gap_severity: str = "unknown"
    iso27001_overlap: bool | None = None
    current_measures_summary: str = ""

    status: GapStatus = GapStatus.open
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    source_preset_type: str = "iso42001_gap_check"
    source_event_id: str = ""
    source_trace_id: str = ""
    source_version: str = "v1"

    tags: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def idempotency_key(self) -> str:
        return f"{self.tenant_id}:{self.client_id}:{self.system_id}:iso42001"
