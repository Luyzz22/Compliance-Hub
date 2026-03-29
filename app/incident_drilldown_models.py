"""DTOs: Incident-Drilldown je KI-System und Lieferant (Laufzeit, aggregiert)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IncidentDrilldownCategoryCounts(BaseModel):
    """Rohzähler klassifizierter Laufzeit-Incidents im Fenster (nur ``event_type=incident``)."""

    safety: int = Field(ge=0)
    availability: int = Field(ge=0)
    other: int = Field(ge=0)


class TenantIncidentDrilldownItem(BaseModel):
    ai_system_id: str
    ai_system_name: str
    supplier_label_de: str = Field(
        description="Anzeige-Label für die dominante Event-Quelle (z. B. SAP AI Core).",
    )
    event_source: str = Field(
        description="Rohwert ``source`` aus ai_runtime_events (API/Export).",
    )
    incident_total_90d: int = Field(ge=0)
    incident_count_by_category: IncidentDrilldownCategoryCounts
    weighted_incident_share_safety: float = Field(ge=0.0, le=1.0)
    weighted_incident_share_availability: float = Field(ge=0.0, le=1.0)
    weighted_incident_share_other: float = Field(ge=0.0, le=1.0)
    oami_local_hint_de: str = Field(default="", max_length=200)


class TenantIncidentDrilldownOut(BaseModel):
    tenant_id: str
    window_days: int = Field(ge=1, le=366)
    systems_with_runtime_events: int = Field(
        ge=0,
        description="Systeme mit mindestens einem Laufzeit-Event im Fenster.",
    )
    systems_with_incidents: int = Field(
        ge=0,
        description="Systeme mit mindestens einem Incident im Fenster (Einträge in items).",
    )
    items: list[TenantIncidentDrilldownItem] = Field(default_factory=list)
