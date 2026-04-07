"""KI-Register-Modelle: Erweiterte Pflichtfelder gemäß EU AI Act (Art. 49, 72)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PostMarketSurveillanceStatus(StrEnum):
    pending = "pending"
    scheduled = "scheduled"
    completed = "completed"
    overdue = "overdue"


class KIRegisterEntry(BaseModel):
    """Erweiterter KI-Register-Eintrag mit EU-AI-Act-Pflichtfeldern."""

    ai_system_id: str
    tenant_id: str
    name: str
    description: str
    # Rollen
    provider_name: str | None = None
    deployer_name: str | None = None
    # Pflichtfelder
    intended_purpose: str | None = Field(
        default=None,
        description="Bestimmungsgemäßer Zweck des KI-Systems (Art. 13).",
    )
    training_data_provenance: str | None = Field(
        default=None,
        description="Herkunft und Zusammensetzung der Trainingsdaten (Art. 10).",
    )
    fria_reference: str | None = Field(
        default=None,
        description="Referenz zur Grundrechte-Folgenabschätzung (FRIA) oder DSFA.",
    )
    provider_responsibilities: str | None = Field(
        default=None,
        description="Dokumentierte Provider-Verantwortlichkeiten.",
    )
    deployer_responsibilities: str | None = Field(
        default=None,
        description="Dokumentierte Deployer-Verantwortlichkeiten.",
    )
    # Klassifikation
    risk_category: str | None = None
    ai_act_category: str | None = None
    annex_iii_category: int | None = None
    # Verknüpfungen
    related_incident_ids: list[str] = Field(default_factory=list)
    related_risk_ids: list[str] = Field(default_factory=list)
    # Post-Market Surveillance (Art. 72)
    pms_status: PostMarketSurveillanceStatus = PostMarketSurveillanceStatus.pending
    pms_next_review_date: datetime | None = None
    pms_last_review_date: datetime | None = None
    # Meta
    business_unit: str | None = None
    owner_email: str | None = None
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None


class KIRegisterUpdateRequest(BaseModel):
    """PATCH-Body für KI-Register-Eintrag."""

    intended_purpose: str | None = None
    training_data_provenance: str | None = None
    fria_reference: str | None = None
    provider_name: str | None = None
    deployer_name: str | None = None
    provider_responsibilities: str | None = None
    deployer_responsibilities: str | None = None
    pms_next_review_date: datetime | None = None


class KIRegisterListResponse(BaseModel):
    """Paginated KI-Register-Übersicht."""

    tenant_id: str
    total: int
    items: list[KIRegisterEntry]


class KIRegisterAuthorityExport(BaseModel):
    """Strukturierter Export für nationale Aufsichtsbehörden."""

    tenant_id: str
    export_timestamp: datetime
    format: str = Field(description="json | xml")
    systems: list[KIRegisterEntry]


class BoardAggregation(BaseModel):
    """Aggregations-Endpoint für Board-Reporting."""

    tenant_id: str
    total_systems: int
    high_risk_by_use_case: dict[str, int] = Field(
        default_factory=dict,
        description="Anzahl High-Risk-Systeme nach Use-Case-Domain.",
    )
    by_role: dict[str, int] = Field(
        default_factory=dict,
        description="Verteilung nach Rollen (Provider/Deployer etc.).",
    )
    open_actions_count: int = Field(
        ge=0,
        description="Offene Maßnahmen aus Wizard-/Gap-Ergebnissen.",
    )
    pms_overdue_count: int = Field(
        ge=0,
        description="KI-Systeme mit überfälliger Post-Market-Surveillance.",
    )
