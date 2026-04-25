"""Compliance Compass — fusionsbasiertes Vertrauens- & Steuerungssignal (MVP, deterministisch)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

COMPASS_VERSION = "compass-2026.1"


class CompassPillarKey:
    """Stabile API-Schlüssel (Frontend-Filter, Analytics)."""

    STRATEGIC_MATURITY = "strategic_maturity"
    EXECUTION_FIDELITY = "execution_fidelity"
    OPERATIONAL_CADENCE = "operational_cadence"
    CONTROL_RESILIENCE = "control_resilience"


class CompassPillarOut(BaseModel):
    """Eine Säule des Kompasses (0–100), mit kurzer Begründung (DE, Nutzer-UI)."""

    key: str = Field(description="Stabiler Säulen-Key, z. B. strategic_maturity")
    label_de: str = Field(description="Kurzlabel auf Deutsch (Executive UI).")
    score_0_100: int = Field(ge=0, le=100)
    weight_in_fusion: float = Field(
        ge=0.0,
        le=1.0,
        description="Gewicht innerhalb des gewichteten Fusions-Index (Summe = 1.0).",
    )
    detail_de: str = Field(
        default="",
        description="1 Zeile, warum der Score so liegt (MVP, deterministisch).",
    )


class CompassProvenanceOut(BaseModel):
    """Rückverfolgbarkeit der Signalquellen (ohne PII) — RAI-Transparenz."""

    readiness_score: int = Field(ge=0, le=100)
    readiness_level: str = Field(description="Level Readiness-Modell: basic / managed / embedded")
    workflow_open_or_active: int = Field(
        ge=0,
        description="Tasks: open+in_progress+escalated",
    )
    workflow_overdue: int = Field(ge=0)
    workflow_escalated: int = Field(
        ge=0,
        description="Task-Status escalated (alle, nicht nur offen)",
    )
    workflow_events_24h: int = Field(
        ge=0,
        description="governance_workflow_events (24h) im Mandanten",
    )
    last_run_completed_at_utc: datetime | None = None
    rule_bundle_version_last_run: str = Field(
        default="",
        description="Zuletzt in einem Run beobachtete Regelversion (kann leer sein).",
    )
    explainability_de: str = Field(
        default=(
            "Der Index kombiniert Mandantssignale (Readiness, Workflow, Eskalation, "
            "Sync). Keine PII in dieser API-Antwort."
        )
    )


class ComplianceCompassSnapshotOut(BaseModel):
    """Eine Abfrage — Executive-Dashboard, Board-ready."""

    tenant_id: str
    as_of_utc: datetime
    model_version: str = Field(
        default=COMPASS_VERSION,
        description="Semantik-Version; bei Algorithmus-Änderung hochzählen.",
    )
    fusion_index_0_100: int = Field(
        ge=0,
        le=100,
        description="Fusions-Index 0–100 (CISO & Board, deterministisch).",
    )
    confidence_0_100: int = Field(
        ge=0,
        le=100,
        description="Signal-Vollständigkeit; niedriger = dünne Datenlage.",
    )
    posture: str = Field(
        description="Kurzlabel: strong | steady | watch | elevated (nicht regulatorisch).",
    )
    narrative_de: str = Field(
        default="",
        description="2–3 Sätze, Executive-Sprache, deutsch.",
    )
    pillars: list[CompassPillarOut] = Field(default_factory=list)
    provenance: CompassProvenanceOut

    privacy_de: str = Field(
        default=("Berechnung pro Mandant. Keine personenbezogenen Details in dieser Antwort."),
        description="Trust-Strip Text (UI).",
    )
