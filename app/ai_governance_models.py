from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.compliance_gap_models import AIComplianceOverview
from app.incident_models import AIIncidentOverview
from app.supplier_risk_models import AISupplierRiskOverview


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


class AIKpiAlert(BaseModel):
    """Einzelalert für Board-KPIs (NIS2 / EU AI Act / ISO 42001)."""

    id: str
    tenant_id: str
    kpi_key: str
    severity: Literal["info", "warning", "critical"]
    message: str
    created_at: datetime
    resolved_at: datetime | None = None


class AIKpiAlertExport(BaseModel):
    """Export-Objekt für Board-Alerts (Reporting / CISO / Vorstand)."""

    tenant_id: str
    generated_at: datetime
    format_version: str = "1.0"
    alerts: list[AIKpiAlert]


class AIBoardGovernanceReport(BaseModel):
    """Vorstands-/Aufsichtsreport: alle AI-Governance-Kennzahlen gebündelt (PDF/Word-Mapping)."""

    tenant_id: str
    generated_at: datetime
    period: str = "last_12_months"
    kpis: AIBoardKpiSummary
    compliance_overview: AIComplianceOverview
    incidents_overview: AIIncidentOverview
    supplier_risk_overview: AISupplierRiskOverview
    alerts: list[AIKpiAlert]


# Export-Job für PDF-/DMS-Integration (Webhook, SAP BTP, DMS)
# Backward-kompatibel: sap_btp, sharepoint weiterhin gültig (kein HTTP-Call).
TargetSystem = Literal[
    "generic_webhook",
    "sap_btp",
    "sharepoint",
    "sap_btp_http",  # SAP BTP HTTP-Inbound / Cloud Integration
    "dms_generic",  # DMS/Archiv (Platzhalter)
]
ExportJobStatus = Literal["pending", "sent", "failed", "not_implemented"]


class BoardReportExportJobCreate(BaseModel):
    """Request-Body für Anlage eines Board-Report-Export-Jobs."""

    target_system: TargetSystem
    callback_url: str | None = None
    metadata: dict[str, str] | None = None


class BoardReportExportJob(BaseModel):
    """Export-Job für Board-Report (in-memory, Tenant-isoliert)."""

    id: str
    tenant_id: str
    created_at: datetime
    status: ExportJobStatus
    target_system: TargetSystem
    callback_url: str | None = None
    metadata: dict[str, str] | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
