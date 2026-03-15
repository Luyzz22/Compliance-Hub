from __future__ import annotations

from pydantic import BaseModel, Field


class AIGovernanceKpiSummary(BaseModel):
    tenant_id: str
    governance_maturity_score: float = Field(ge=0.0, le=1.0)
    ai_systems_with_owner: int
    ai_systems_total: int
    high_risk_with_dpia: int
    high_risk_total: int
    policy_violations_open: int
    audit_events_last_30_days: int
    has_documented_ai_policy: bool = False
    has_ai_risk_register: bool = False


class AIBoardKpiSummary(BaseModel):
    tenant_id: str
    ai_systems_total: int
    active_ai_systems: int
    high_risk_systems: int
    open_policy_violations: int

    # Aggregierter Board-Score (0..1)
    board_maturity_score: float

    # Cluster-Scores (0..1)
    compliance_coverage_score: float
    risk_governance_score: float
    operational_resilience_score: float
    responsible_ai_score: float

    # Kerntreiber für das Board
    high_risk_systems_without_dpia: int
    critical_systems_without_owner: int
    nis2_control_gaps: int  # Summe offener NIS2-Kontrollen (Runbook, Backup, Supplier-Risiko)

    # NIS2-spezifische KPIs (Incident- und Supplier-Risiko, Art. 21 / Art. 24)
    nis2_incident_readiness_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Anteil KI-Systeme mit Incident- und Backup-Runbook (NIS2 Art. 21)",
    )
    nis2_supplier_risk_coverage_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Anteil KI-Systeme mit Lieferanten-Risiko-Register (NIS2 Art. 24)",
    )

    # ISO 42001 – AI-Governance-Reife (AI-Managementsystem)
    iso42001_governance_score: float = Field(
        ge=0.0,
        le=1.0,
        description=("Abgeleiteter Reifegrad-Score für ISO 42001 AI-MS (Kontext, Risiko, Betrieb)"),
    )

    # Trends optional (im ersten Schritt statisch 0)
    score_change_vs_last_quarter: float
    incidents_last_quarter: int
    complaints_last_quarter: int
