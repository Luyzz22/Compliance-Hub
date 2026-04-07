from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.rbac.roles import EnterpriseRole


class IdentityProviderType(StrEnum):
    azure_ad = "azure_ad"
    saml_generic = "saml_generic"
    sap_ias = "sap_ias"
    google_workspace = "google_workspace"
    okta = "okta"
    other = "other"


class ReadinessStatus(StrEnum):
    not_started = "not_started"
    planned = "planned"
    configured = "configured"
    validated = "validated"


class IntegrationTargetType(StrEnum):
    sap_btp = "sap_btp"
    sap_s4hana = "sap_s4hana"
    datev = "datev"
    ms_dynamics = "ms_dynamics"
    generic_api = "generic_api"


class IntegrationReadinessStatus(StrEnum):
    not_started = "not_started"
    discovery = "discovery"
    mapped = "mapped"
    ready_for_implementation = "ready_for_implementation"


class TenantEntityNode(BaseModel):
    entity_code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(default="business_unit", max_length=80)
    parent_entity_code: str | None = Field(default=None, max_length=80)


class RoleMappingRule(BaseModel):
    external_group_or_claim: str = Field(..., min_length=1, max_length=255)
    mapped_role: EnterpriseRole
    notes: str | None = Field(default=None, max_length=500)


class SSOReadinessConfig(BaseModel):
    provider_type: IdentityProviderType = IdentityProviderType.azure_ad
    onboarding_status: ReadinessStatus = ReadinessStatus.not_started
    role_mapping_status: ReadinessStatus = ReadinessStatus.not_started
    identity_domain: str | None = Field(default=None, max_length=255)
    metadata_hint: str | None = Field(default=None, max_length=500)
    role_mapping_rules: list[RoleMappingRule] = Field(default_factory=list)


class IntegrationReadinessItem(BaseModel):
    target_type: IntegrationTargetType
    readiness_status: IntegrationReadinessStatus = IntegrationReadinessStatus.not_started
    owner: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    blocker: str | None = Field(default=None, max_length=500)
    evidence_ref: str | None = Field(default=None, max_length=500)


class EnterpriseOnboardingReadinessUpsert(BaseModel):
    enterprise_name: str | None = Field(default=None, max_length=255)
    tenant_structure: list[TenantEntityNode] = Field(default_factory=list)
    advisor_visibility_enabled: bool = True
    sso_readiness: SSOReadinessConfig = Field(default_factory=SSOReadinessConfig)
    integration_readiness: list[IntegrationReadinessItem] = Field(default_factory=list)
    rollout_notes: str | None = Field(default=None, max_length=2000)


class OnboardingBlocker(BaseModel):
    key: str
    title_de: str
    severity: str


class EnterpriseOnboardingReadinessResponse(BaseModel):
    tenant_id: str
    updated_at_utc: datetime
    updated_by: str
    enterprise_name: str | None = None
    tenant_structure: list[TenantEntityNode]
    advisor_visibility_enabled: bool
    sso_readiness: SSOReadinessConfig
    integration_readiness: list[IntegrationReadinessItem]
    rollout_notes: str | None = None
    blockers: list[OnboardingBlocker]
