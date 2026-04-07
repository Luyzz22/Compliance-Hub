from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.enterprise_control_center_models import EnterpriseControlCenterItem


class PreparationPackFocus(StrEnum):
    audit = "audit"
    authority = "authority"
    mixed = "mixed"


class PreparationPackSection(BaseModel):
    title_de: str
    summary_de: str
    evidence_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    due_items: list[str] = Field(default_factory=list)


class AuthorityAuditPreparationPackResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    focus: PreparationPackFocus
    source_sections: list[str]
    section_a_executive_posture: PreparationPackSection
    section_b_open_critical_missing_evidence: PreparationPackSection
    section_c_audit_trail_readiness: PreparationPackSection
    section_d_nis2_incident_deadline_status: PreparationPackSection
    section_e_ai_act_register_authority_status: PreparationPackSection
    section_f_recommended_next_preparation_actions: PreparationPackSection
    top_urgent_items: list[EnterpriseControlCenterItem]
    markdown_de: str
