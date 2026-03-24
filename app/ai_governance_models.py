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
    nis2_kritis_kpi_mean_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Mittelwert aller NIS2-/KRITIS-KPI-Werte (0–100), falls vorhanden.",
    )
    nis2_kritis_systems_full_coverage_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Anteil KI-Systeme mit allen drei KPI-Typen gepflegt.",
    )


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

    nis2_kritis_kpi_mean_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Mittelwert aller NIS2-/KRITIS-KPI-Werte (0–100).",
    )
    nis2_kritis_systems_full_coverage_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Anteil KI-Systeme mit allen drei KPI-Typen gepflegt.",
    )


class AIKpiAlertMetadata(BaseModel):
    """Optionale Kennzahlen-Kontext für Board-Alerts (v. a. NIS2-/KRITIS-KPI-Alerts)."""

    current_percent: float | None = Field(
        default=None,
        description="Ist-Wert in Prozent (0–100) oder Readiness-Anteil, je nach Alert.",
    )
    threshold_percent: float | None = Field(
        default=None,
        description="Verglichene Schwellwert-Angabe in Prozent (0–100), sofern anwendbar.",
    )
    kpi_type: str | None = Field(
        default=None,
        description="NIS2-/KRITIS-KPI-Typ, z. B. INCIDENT_RESPONSE_MATURITY.",
    )
    affected_system_ids: list[str] = Field(
        default_factory=list,
        description="Bis zu drei KI-System-IDs mit niedrigsten Werten / Fokus.",
        max_length=10,
    )
    coverage_ratio_current: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional: aktueller KPI-Vollständigkeits-Anteil (0–1) je System.",
    )
    coverage_ratio_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional: Schwellwert für coverage_ratio_current.",
    )


class AIKpiAlert(BaseModel):
    """Einzelalert für Board-KPIs (NIS2 / EU AI Act / ISO 42001)."""

    id: str
    tenant_id: str
    kpi_key: str
    severity: Literal["info", "warning", "critical"]
    message: str
    created_at: datetime
    resolved_at: datetime | None = None
    alert_metadata: AIKpiAlertMetadata | None = None


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
    "datev_dms_prepared",  # Steuerberater/WP-Kanzlei, DATEV-/DMS-Ready
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


# Audit-Ready: Versionierung, Freigaben, Referenzen auf Export-Jobs (WP-/Prüfungsdokumentation)
AuditRecordStatus = Literal["draft", "final"]


class BoardReportAuditRecordCreate(BaseModel):
    """Request-Body für Anlage eines Board-Report-Audit-Records."""

    purpose: str = Field(..., min_length=1, max_length=200)
    status: AuditRecordStatus = "draft"
    linked_export_job_ids: list[str] = Field(default_factory=list, max_length=50)
    linked_kpi_export_job_ids: list[str] = Field(default_factory=list, max_length=50)


class BoardReportAuditRecord(BaseModel):
    """Audit-Trail-Eintrag für Board-Report (Versionierung, verknüpfte Export-Jobs)."""

    id: str
    tenant_id: str
    report_generated_at: datetime
    report_version: str
    created_at: datetime
    created_by: str
    purpose: str
    linked_export_job_ids: list[str]
    linked_kpi_export_job_ids: list[str] = Field(default_factory=list)
    status: AuditRecordStatus


class BoardReportAuditRecordWithJobs(BoardReportAuditRecord):
    """Audit-Record inkl. aufgelöster verknüpfter Export-Jobs (für GET by id)."""

    linked_export_jobs: list[BoardReportExportJob] = Field(default_factory=list)
    linked_kpi_export_jobs: list[BoardKpiExportJob] = Field(default_factory=list)


# Norm-Nachweise: Verknüpfung von Audit-Records/Reports mit Norm-Referenzen
NormFramework = Literal["EU_AI_ACT", "NIS2", "ISO_42001"]
EvidenceType = Literal["board_report", "export_job", "other"]


class NormEvidenceLinkCreate(BaseModel):
    """Request-Body für Anlage eines Norm-Nachweis-Links."""

    framework: NormFramework
    reference: str
    evidence_type: EvidenceType = "board_report"
    note: str | None = None


class NormEvidenceLink(BaseModel):
    """Norm-Nachweis-Link zwischen Audit-Record und Norm-Referenz."""

    id: str
    tenant_id: str
    audit_record_id: str
    framework: NormFramework
    reference: str
    evidence_type: EvidenceType
    note: str | None = None


class BoardKpiExportSystemRow(BaseModel):
    """Eine Zeile im Board-KPI-Export (DMS/DATEV/SAP-BTP-tauglich)."""

    ai_system_id: str
    name: str
    business_unit: str
    risk_level: str
    ai_act_category: str
    high_risk_scenario_profile_id: str | None = None
    nis2_kritis_incident_response_maturity_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    nis2_kritis_supplier_risk_coverage_percent: int | None = Field(default=None, ge=0, le=100)
    nis2_kritis_ot_it_segregation_percent: int | None = Field(default=None, ge=0, le=100)


class BoardKpiExportEnvelope(BaseModel):
    """JSON-Export-Envelope für Board-/NIS2-KPI-Daten."""

    format_version: str = "1.0"
    tenant_id: str
    generated_at: datetime
    systems: list[BoardKpiExportSystemRow]
    regulatory_scope: list[str] = Field(
        default_factory=lambda: ["EU_AI_ACT", "NIS2", "ISO_42001"],
        description="Normative Einordnung für DMS/DATEV-/SAP-BTP-Routing.",
    )
    generated_by: str = Field(
        default="board_kpi_export_v1",
        description="Export-Pipeline-Label für Downstream-Integrationen.",
    )


KpiExportTargetLabel = Literal["datev", "dms", "sap_btp_placeholder"]
BoardKpiExportJobStatus = Literal["completed", "failed"]


class BoardKpiExportJobCreate(BaseModel):
    """Audit-Trail: KPI-Export-Job anlegen (ohne externen Versand)."""

    target_system_label: KpiExportTargetLabel
    export_format: Literal["json", "csv"] = "json"
    metadata: dict[str, str] | None = None


class BoardKpiExportJob(BaseModel):
    """In-Memory-Metadaten zu einem KPI-Export (Tenant-isoliert)."""

    id: str
    tenant_id: str
    created_at: datetime
    completed_at: datetime | None = None
    status: BoardKpiExportJobStatus
    target_system_label: KpiExportTargetLabel
    export_format: Literal["json", "csv"]
    metadata: dict[str, str] | None = None
    error_message: str | None = None


class HighRiskScenarioProfile(BaseModel):
    """Read-only High-Risk-AI-Szenario mit empfohlenen Norm-Nachweisen (keine DB-Anlage)."""

    id: str
    label: str
    description: str
    recommended_evidence: list[NormEvidenceLinkCreate]
    recommended_incident_response_maturity_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    recommended_supplier_risk_coverage_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    recommended_ot_it_segregation_percent: int | None = Field(default=None, ge=0, le=100)
