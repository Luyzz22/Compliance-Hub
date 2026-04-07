from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.classification_models import ClassificationQuestionnaire, RiskClassification


class InventoryProviderType(StrEnum):
    internal = "internal"
    external = "external"


class ScopeFlag(StrEnum):
    in_scope = "in_scope"
    out_of_scope = "out_of_scope"
    review_needed = "review_needed"


class KiRegisterStatus(StrEnum):
    planned = "planned"
    registered = "registered"
    partial = "partial"
    not_required = "not_required"


class AISystemInventoryProfileUpsert(BaseModel):
    provider_name: str | None = Field(default=None, max_length=255)
    provider_type: InventoryProviderType = InventoryProviderType.external
    use_case: str = Field(..., min_length=1, max_length=500)
    business_process: str | None = Field(default=None, max_length=255)
    eu_ai_act_scope: ScopeFlag = ScopeFlag.review_needed
    iso_42001_scope: ScopeFlag = ScopeFlag.review_needed
    nis2_scope: ScopeFlag = ScopeFlag.review_needed
    dsgvo_special_risk: ScopeFlag = ScopeFlag.review_needed
    register_status: KiRegisterStatus = KiRegisterStatus.planned
    register_metadata: dict[str, str] = Field(default_factory=dict)
    authority_reporting_flags: dict[str, bool] = Field(default_factory=dict)


class AISystemInventoryProfileRead(AISystemInventoryProfileUpsert):
    tenant_id: str
    ai_system_id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


class KIRegisterEntryUpsert(BaseModel):
    status: KiRegisterStatus = KiRegisterStatus.planned
    authority_name: str | None = Field(default=None, max_length=255)
    national_register_id: str | None = Field(default=None, max_length=255)
    reportable_incident: bool = False
    reportable_change: bool = False
    fields: dict[str, str] = Field(default_factory=dict)


class KIRegisterEntryRead(KIRegisterEntryUpsert):
    tenant_id: str
    ai_system_id: str
    version: int
    created_at: datetime
    created_by: str


class KIRegisterPostureSummary(BaseModel):
    registered: int = 0
    planned: int = 0
    partial: int = 0
    unknown: int = 0


class AuthorityExportScope(StrEnum):
    initial = "initial"
    updates = "updates"
    incident_context = "incident_context"


class AuthorityExportSystemRow(BaseModel):
    system_id: str
    name: str
    risk_level: str
    ai_act_category: str
    register_status: str
    eu_ai_act_scope: str
    reportable_incident: bool = False
    reportable_change: bool = False


class AuthorityExportEnvelope(BaseModel):
    format_version: str = "1.0"
    tenant_id: str
    generated_at: datetime
    scope: AuthorityExportScope
    generated_by: str = "authority_export_v1"
    systems: list[AuthorityExportSystemRow]
    disclaimer: str = (
        "Diese Ausgabe ist eine strukturierte Arbeitsgrundlage und keine Rechtsberatung."
    )


class AuthorityExportResponse(BaseModel):
    export: AuthorityExportEnvelope
    markdown_de: str


class WizardDecisionResponse(BaseModel):
    decision_version: Literal["eu_ai_act_v1"]
    classification: RiskClassification
    minimum_question_set_complete: bool
    advisory_note_de: str
    mapped_inventory_scope: dict[str, str]


class WizardDecisionRequest(BaseModel):
    ai_system_id: str
    questionnaire: ClassificationQuestionnaire
