from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SetupStepKey(StrEnum):
    """Abgleich mit Guided-Setup-Wizard (Workspace)."""

    INVENTORY = "INVENTORY"
    CLASSIFICATION = "CLASSIFICATION"
    NIS2_KPIS = "NIS2_KPIS"
    POLICIES = "POLICIES"
    ACTIONS = "ACTIONS"
    EVIDENCE = "EVIDENCE"
    READINESS = "READINESS"


class TenantSetupStatus(BaseModel):
    """Aggregierter Setup-Status aus bestehenden Entitäten (keine eigene Persistenz)."""

    tenant_id: str

    ai_inventory_completed: bool = Field(
        description="Mindestens ein KI-System im Mandanten-Register.",
    )
    classification_completed: bool = Field(
        description="Alle registrierten Systeme haben einen EU-AI-Act-Klassifikationsdatensatz.",
    )
    classification_coverage_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Anteil Systeme mit Klassifikation (für Transparenz / künftige Schwellen).",
    )
    nis2_kpis_seeded: bool = Field(
        description=(
            "Mind. ein KI-System im Register und jedes High-Risk-System hat mindestens einen "
            "NIS2-/KRITIS-KPI-Eintrag; ohne High-Risk-Systeme (aber mit Register) als erfüllt."
        ),
    )
    policies_published: bool = Field(
        description="Mindestens eine Policy im Policies-Modul.",
    )
    actions_defined: bool = Field(
        description="Mindestens eine Governance-Action.",
    )
    evidence_attached: bool = Field(
        description=(
            "Mindestens eine Evidenz-Datei mit Verknüpfung zu System, Action oder Audit-Record."
        ),
    )
    eu_ai_act_readiness_baseline_created: bool = Field(
        description=(
            "Proxy: mindestens ein Compliance-Status-Eintrag wurde über 'not_started' hinaus "
            "bearbeitet (Readiness-/Gap-Engagement)."
        ),
    )

    completed_steps: int = Field(ge=0, le=7, description="Anzahl abgeschlossener Wizard-Schritte.")
    total_steps: int = Field(default=7, ge=1)
