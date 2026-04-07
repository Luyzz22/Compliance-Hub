from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceSystemType(StrEnum):
    sap_btp = "sap_btp"
    sap_s4hana = "sap_s4hana"
    datev = "datev"
    ms_dynamics = "ms_dynamics"
    generic_api = "generic_api"


class EvidenceDomain(StrEnum):
    invoice = "invoice"
    approval = "approval"
    access = "access"
    vendor = "vendor"
    ai_inventory = "ai_inventory"
    policy_artifact = "policy_artifact"
    workflow_evidence = "workflow_evidence"
    tax_export_context = "tax_export_context"


class IntegrationBlueprintStatus(StrEnum):
    planned = "planned"
    designing = "designing"
    blocked = "blocked"
    ready_for_build = "ready_for_build"


class IntegrationReadinessPosture(StrEnum):
    integration_ready = "integration_ready"
    preparing = "preparing"
    blocked = "blocked"


class EnterpriseIntegrationBlueprintRow(BaseModel):
    blueprint_id: str = Field(..., min_length=1, max_length=120)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    source_system_type: SourceSystemType
    evidence_domains: list[EvidenceDomain] = Field(default_factory=list)
    onboarding_readiness_ref: str | None = Field(default=None, max_length=255)
    security_prerequisites: list[str] = Field(default_factory=list)
    data_owner: str | None = Field(default=None, max_length=255)
    technical_owner: str | None = Field(default=None, max_length=255)
    integration_status: IntegrationBlueprintStatus = IntegrationBlueprintStatus.planned
    blockers: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None
    updated_by: str | None = None


class EnterpriseIntegrationBlueprintUpsert(BaseModel):
    blueprint_id: str = Field(..., min_length=1, max_length=120)
    source_system_type: SourceSystemType
    evidence_domains: list[EvidenceDomain] = Field(default_factory=list)
    onboarding_readiness_ref: str | None = Field(default=None, max_length=255)
    security_prerequisites: list[str] = Field(default_factory=list)
    data_owner: str | None = Field(default=None, max_length=255)
    technical_owner: str | None = Field(default=None, max_length=255)
    integration_status: IntegrationBlueprintStatus = IntegrationBlueprintStatus.planned
    blockers: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class EnterpriseIntegrationCandidate(BaseModel):
    blueprint_id: str
    source_system_type: SourceSystemType
    score: int = Field(ge=0, le=100)
    recommendation_de: str
    unlocked_evidence_domains: list[EvidenceDomain] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class EnterpriseIntegrationBlueprintResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    readiness_status: IntegrationReadinessPosture
    blueprint_rows: list[EnterpriseIntegrationBlueprintRow]
    blockers: list[str] = Field(default_factory=list)
    top_enterprise_integration_candidates: list[EnterpriseIntegrationCandidate]
    markdown_de: str | None = None
