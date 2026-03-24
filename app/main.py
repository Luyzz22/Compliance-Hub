from __future__ import annotations

import csv
import io
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai_governance_models import (
    AIBoardGovernanceReport,
    AIBoardKpiSummary,
    AIGovernanceKpiSummary,
    AIKpiAlert,
    AIKpiAlertExport,
    BoardReportAuditRecord,
    BoardReportAuditRecordCreate,
    BoardReportAuditRecordWithJobs,
    BoardReportExportJob,
    BoardReportExportJobCreate,
    HighRiskScenarioProfile,
    NormEvidenceLink,
    NormEvidenceLinkCreate,
    NormFramework,
)
from app.ai_system_models import (
    AISystem,
    AISystemComplianceReport,
    AISystemCreate,
    AISystemStatus,
    AISystemUpdate,
)
from app.audit_models import AuditEvent, AuditLog
from app.classification_models import (
    ClassificationOverrideRequest,
    ClassificationQuestionnaire,
    ClassificationSummary,
    RiskClassification,
)
from app.compliance_gap_models import (
    REQUIREMENTS,
    REQUIREMENTS_BY_ID,
    AIComplianceOverview,
    ComplianceDashboard,
    ComplianceRequirement,
    ComplianceStatusEntry,
    ComplianceStatusUpdate,
)
from app.db import engine, get_session
from app.incident_models import AIIncidentBySystemEntry, AIIncidentOverview
from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    DocumentType,
    EInvoiceFormat,
)
from app.models_db import Base
from app.nis2_kritis_models import (
    Nis2KritisKpi,
    Nis2KritisKpiListResponse,
    Nis2KritisKpiUpsertRequest,
)
from app.policy_models import Violation
from app.policy_service import evaluate_policies_for_ai_system
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository
from app.security import AuthContext, get_api_key_and_tenant, get_auth_context
from app.services.ai_board_alerts import compute_board_alerts
from app.services.ai_governance_incidents import (
    compute_ai_incident_overview,
    compute_ai_incidents_by_system,
)
from app.services.ai_governance_kpis import compute_ai_board_kpis, compute_ai_governance_kpis
from app.services.ai_governance_suppliers import (
    compute_ai_supplier_risk_by_system,
    compute_ai_supplier_risk_overview,
)
from app.services.board_report_audit_records import (
    create_audit_record,
    get_record,
    list_records,
)
from app.services.board_report_export_jobs import get_job, run_export_job
from app.services.board_report_markdown import render_board_report_markdown
from app.services.board_report_norm_evidence import (
    create_links,
    get_default_norm_evidence_suggestions,
    list_by_audit,
    query_by_norm,
)
from app.services.classification_engine import classify_ai_system
from app.services.compliance_dashboard import (
    compute_ai_compliance_overview,
    compute_compliance_dashboard,
)
from app.services.compliance_engine import build_audit_hash, derive_actions
from app.services.high_risk_scenarios import list_high_risk_scenarios
from app.services.nis2_kritis_kpis import recommended_kpis_for_ai_system
from app.services.tenant_compliance_overview import (
    TenantComplianceOverview,
    compute_tenant_compliance_overview,
)
from app.supplier_risk_models import (
    AISupplierRiskBySystemEntry,
    AISupplierRiskOverview,
)

APP_VERSION = os.getenv("COMPLIANCEHUB_VERSION", "0.1.0")
APP_ENVIRONMENT = os.getenv("COMPLIANCEHUB_ENV", "dev")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Enterprise lifespan context manager for ComplianceHub.

    Startup: Initialize database schema (ISO 27001/NIS2 compliant)
    Shutdown: Graceful connection cleanup, audit log flush
    """
    # Startup phase
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown phase


app = FastAPI(
    title="ComplianceHub API",
    version="0.1.0",
    lifespan=lifespan,
)


class DocumentIntakeRequest(BaseModel):
    tenant_id: str = Field(..., examples=["tenant-001"])
    document_id: str = Field(..., examples=["doc-001"])
    document_type: DocumentType
    supplier_name: str
    supplier_country: str
    contains_personal_data: bool = True
    e_invoice_format: EInvoiceFormat = EInvoiceFormat.unknown
    xml_valid_en16931: bool = False
    amount_eur: float = 0.0


class AISystemPolicyReportResponse(BaseModel):
    ai_system: AISystem
    violations: list[Violation]


class ComplianceActionModel(BaseModel):
    action: str
    module: str
    severity: str
    rationale: str

    @classmethod
    def from_domain(cls, action: ComplianceAction) -> ComplianceActionModel:
        return cls(
            action=action.action,
            module=action.module,
            severity=action.severity,
            rationale=action.rationale,
        )


class DocumentIntakeResponse(BaseModel):
    document_id: str
    accepted: bool
    timestamp_utc: datetime
    actions: list[ComplianceActionModel]
    audit_hash: str


def get_ai_system_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AISystemRepository:
    return AISystemRepository(session)


def get_audit_log_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditLogRepository:
    return AuditLogRepository(session)


def get_audit_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditRepository:
    return AuditRepository(session)


def get_policy_repository(
    session: Annotated[Session, Depends(get_session)],
) -> PolicyRepository:
    return PolicyRepository(session)


def get_violation_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ViolationRepository:
    return ViolationRepository(session)


def get_incident_repository(
    session: Annotated[Session, Depends(get_session)],
) -> IncidentRepository:
    return IncidentRepository(session)


def get_classification_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ClassificationRepository:
    return ClassificationRepository(session)


def get_compliance_gap_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ComplianceGapRepository:
    return ComplianceGapRepository(session)


def get_nis2_kritis_kpi_repository(
    session: Annotated[Session, Depends(get_session)],
) -> Nis2KritisKpiRepository:
    return Nis2KritisKpiRepository(session)


def _model_to_json(model: BaseModel) -> str:
    payload: dict[str, Any]
    if hasattr(model, "model_dump"):
        payload = model.model_dump(mode="json")  # type: ignore[assignment]
    else:
        payload = model.dict()  # type: ignore[assignment]
    return json.dumps(payload)


def _health_payload() -> dict[str, str]:
    return {
        "status": "ok",
        "product": "ComplianceHub",
        "region": "DACH",
    }


@app.get("/api/v1/health")
def health_v1() -> dict[str, str]:
    return _health_payload()


class NormEvidenceWithAudit(BaseModel):
    """Response-Objekt für Norm-Nachweise inkl. Audit-Record-Metadaten."""

    evidence: NormEvidenceLink
    audit_record_id: str
    report_generated_at: datetime
    purpose: str


@app.get("/health")
def health_root() -> dict[str, str]:
    return _health_payload()


@app.post("/api/v1/documents/intake", response_model=DocumentIntakeResponse)
def intake(payload: DocumentIntakeRequest) -> DocumentIntakeResponse:
    domain_payload = DocumentIngestRequest(
        tenant_id=payload.tenant_id,
        document_id=payload.document_id,
        document_type=payload.document_type,
        supplier_name=payload.supplier_name,
        supplier_country=payload.supplier_country,
        contains_personal_data=payload.contains_personal_data,
        e_invoice_format=payload.e_invoice_format,
        xml_valid_en16931=payload.xml_valid_en16931,
        amount_eur=payload.amount_eur,
    )

    actions = derive_actions(domain_payload)
    audit_hash = build_audit_hash(domain_payload)

    return DocumentIntakeResponse(
        document_id=payload.document_id,
        accepted=True,
        timestamp_utc=datetime.utcnow(),
        actions=[ComplianceActionModel.from_domain(action) for action in actions],
        audit_hash=audit_hash,
    )


@app.get("/api/v1/ai-systems", response_model=list[AISystem])
def list_ai_systems(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> list[AISystem]:
    return repository.list_for_tenant(tenant_id)


@app.post("/api/v1/ai-systems", response_model=AISystem)
def create_ai_system(
    payload: AISystemCreate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_event_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AISystem:
    tenant_id = auth_context.tenant_id
    created = repository.create(tenant_id, payload)

    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system",
        action="create_ai_system",
        entity_type="AISystem",
        entity_id=created.id,
        before=None,
        after=_model_to_json(created),
    )
    audit_event_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system",
        entity_id=created.id,
        action="created",
        metadata={"status": created.status.value},
    )
    evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=created,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_event_repo,
        actor_type="api_key",
        actor_id=auth_context.api_key,
    )
    return created


@app.patch("/api/v1/ai-systems/{aisystem_id}", response_model=AISystem)
def update_ai_system(
    aisystem_id: str,
    payload: AISystemUpdate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_event_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AISystem:
    tenant_id = auth_context.tenant_id
    existing = repository.get_by_id(tenant_id=tenant_id, aisystem_id=aisystem_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )

    updated = repository.update(tenant_id=tenant_id, aisystem_id=aisystem_id, payload=payload)
    audit_event_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system",
        entity_id=updated.id,
        action="updated",
        metadata={"status": updated.status.value},
    )
    evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=updated,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_event_repo,
        actor_type="api_key",
        actor_id=auth_context.api_key,
    )
    return updated


@app.patch("/api/v1/ai-systems/{aisystem_id}/status", response_model=AISystem)
def update_ai_system_status(
    aisystem_id: str,
    new_status: AISystemStatus,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_event_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AISystem:
    tenant_id = auth_context.tenant_id
    existing = repository.get_by_id(tenant_id=tenant_id, aisystem_id=aisystem_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )

    before_json = _model_to_json(existing)
    updated = repository.update_status(
        tenant_id=tenant_id,
        aisystem_id=aisystem_id,
        new_status=new_status,
    )
    after_json = _model_to_json(updated)

    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system",
        action="update_ai_system_status",
        entity_type="AISystem",
        entity_id=updated.id,
        before=before_json,
        after=after_json,
    )
    audit_event_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system",
        entity_id=updated.id,
        action="status_changed",
        metadata={"status": updated.status.value},
    )
    evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=updated,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_event_repo,
        actor_type="api_key",
        actor_id=auth_context.api_key,
    )

    return updated


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/nis2-kritis-kpis",
    response_model=Nis2KritisKpiListResponse,
)
def list_nis2_kritis_kpis(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> Nis2KritisKpiListResponse:
    tenant_id = auth_context.tenant_id
    system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )
    kpis = nis2_repo.list_for_ai_system(tenant_id, ai_system_id)
    recommended = recommended_kpis_for_ai_system(system)
    return Nis2KritisKpiListResponse(kpis=kpis, recommended=recommended)


@app.post(
    "/api/v1/ai-systems/{ai_system_id}/nis2-kritis-kpis",
    response_model=Nis2KritisKpi,
)
def upsert_nis2_kritis_kpi(
    ai_system_id: str,
    body: Nis2KritisKpiUpsertRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> Nis2KritisKpi:
    tenant_id = auth_context.tenant_id
    system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )
    return nis2_repo.upsert(
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        kpi_type=body.kpi_type,
        value_percent=body.value_percent,
        evidence_ref=body.evidence_ref,
        last_reviewed_at=body.last_reviewed_at,
    )


@app.get("/api/v1/audit-logs", response_model=list[AuditLog])
def list_audit_logs(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[AuditLog]:
    return audit_repo.list_for_tenant(tenant_id=tenant_id)


@app.get("/api/v1/audit-events", response_model=list[AuditEvent])
def list_audit_events(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEvent]:
    tenant_id = auth_context.tenant_id
    if entity_type is not None and entity_id is not None:
        return audit_repo.list_events_for_entity(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )
    return audit_repo.list_events_for_tenant(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/audit-events/ai-systems/{ai_system_id}", response_model=list[AuditEvent])
def list_ai_system_audit_events(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEvent]:
    return audit_repo.list_events_for_entity(
        tenant_id=auth_context.tenant_id,
        entity_type="ai_system",
        entity_id=ai_system_id,
        limit=limit,
        offset=offset,
    )


def _enterprise_status_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "product": "ComplianceHub",
        "region": "DACH",
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT,
        "features_enabled": [
            "document_intake",
            "ai_system_registry",
            "audit_logging",
        ],
        "compliance_profiles": [
            "EU_AI_ACT_FOUNDATION",
            "GDPR_MINIMAL",
        ],
    }


@app.get("/api/v1/enterprise/status")
def enterprise_status() -> dict[str, object]:
    return _enterprise_status_payload()


@app.get("/api/v1/compliance/reports/ai-systems", response_model=AISystemComplianceReport)
def get_aisystem_compliance_report(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> AISystemComplianceReport:
    summary = repository.compliance_summary_for_tenant(tenant_id)
    return AISystemComplianceReport(**summary)


@app.get("/api/v1/ai-governance/board-kpis", response_model=AIBoardKpiSummary)
def get_ai_governance_board_kpis(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    violation_repository: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIBoardKpiSummary:
    return compute_ai_board_kpis(
        tenant_id=auth_context.tenant_id,
        ai_system_repository=ai_repository,
        violation_repository=violation_repository,
        nis2_kritis_kpi_repository=nis2_repo,
    )


@app.get(
    "/api/v1/ai-governance/compliance/overview",
    response_model=AIComplianceOverview,
)
def get_ai_compliance_overview(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIComplianceOverview:
    """Board-fähiger EU AI Act / ISO 42001 Readiness-Überblick."""
    return compute_ai_compliance_overview(
        tenant_id=auth_context.tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )


@app.get(
    "/api/v1/ai-governance/alerts/board",
    response_model=list[AIKpiAlert],
)
def get_board_alerts(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> list[AIKpiAlert]:
    """Aktuelle Board-KPI-Alerts (NIS2 / EU AI Act / ISO 42001) für den Tenant."""
    tenant_id = auth_context.tenant_id
    board_kpis = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    compliance_overview = compute_ai_compliance_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    return compute_board_alerts(
        tenant_id=tenant_id,
        board_kpis=board_kpis,
        compliance_overview=compliance_overview,
    )


def _alerts_export_csv(tenant_id: str, alerts: list[AIKpiAlert], generated_at: datetime) -> str:
    """Eine Zeile pro Alert, CSV-konform (RFC 4180)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["id", "tenant_id", "kpi_key", "severity", "message", "created_at", "resolved_at"]
    )
    for a in alerts:
        writer.writerow(
            [
                a.id,
                a.tenant_id,
                a.kpi_key,
                a.severity,
                a.message,
                a.created_at.isoformat() if a.created_at else "",
                a.resolved_at.isoformat() if a.resolved_at else "",
            ]
        )
    return out.getvalue()


@app.get(
    "/api/v1/ai-governance/alerts/board/export",
    response_class=Response,
)
def get_board_alerts_export(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    format: Annotated[
        Literal["json", "csv"],
        Query(description="Export-Format: json (Standard) oder csv"),
    ] = "json",
) -> Response:
    """Board-Alerts als JSON oder CSV für Reporting / CISO / Vorstand (keine Personenbezogenen)."""
    from app.datetime_compat import UTC

    tenant_id = auth_context.tenant_id
    board_kpis = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    compliance_overview = compute_ai_compliance_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    alerts = compute_board_alerts(
        tenant_id=tenant_id,
        board_kpis=board_kpis,
        compliance_overview=compliance_overview,
    )
    generated_at = datetime.now(UTC)

    if format == "csv":
        csv_content = _alerts_export_csv(tenant_id, alerts, generated_at)
        filename = f"ai-governance-alerts-{tenant_id}-{generated_at.strftime('%Y%m%d')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    export_data = AIKpiAlertExport(
        tenant_id=tenant_id,
        generated_at=generated_at,
        format_version="1.0",
        alerts=alerts,
    )
    filename = f"ai-governance-alerts-{tenant_id}-{generated_at.strftime('%Y%m%d')}.json"
    return Response(
        content=export_data.model_dump_json(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get(
    "/api/v1/ai-governance/report/board",
    response_model=AIBoardGovernanceReport,
)
def get_board_governance_report(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIBoardGovernanceReport:
    """Vorstands-/Aufsichtsreport: alle AI-Governance-Kennzahlen gebündelt (nur JSON)."""
    return _build_board_report(
        tenant_id=auth_context.tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        incident_repo=incident_repo,
        nis2_repo=nis2_repo,
    )


@app.get(
    "/api/v1/ai-governance/report/board/markdown",
    response_class=Response,
)
def get_board_governance_report_markdown(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> Response:
    """Board-Report als Markdown (template-fähig, für PDF/Word-Weiterverarbeitung)."""
    report = _build_board_report(
        tenant_id=auth_context.tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        incident_repo=incident_repo,
        nis2_repo=nis2_repo,
    )
    markdown_content = render_board_report_markdown(report)
    filename = f"ai-board-report-{report.tenant_id}-{report.generated_at.strftime('%Y%m%d')}.md"
    return Response(
        content=markdown_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _build_board_report(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
    violation_repo: ViolationRepository,
    incident_repo: IncidentRepository,
    nis2_repo: Nis2KritisKpiRepository,
) -> AIBoardGovernanceReport:
    """Orchestriert alle Services und liefert AIBoardGovernanceReport."""
    from app.datetime_compat import UTC

    generated_at = datetime.now(UTC)
    kpis = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    compliance_overview = compute_ai_compliance_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    incidents_overview = compute_ai_incident_overview(
        tenant_id=tenant_id,
        incident_repository=incident_repo,
    )
    supplier_risk_overview = compute_ai_supplier_risk_overview(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
    )
    alerts = compute_board_alerts(
        tenant_id=tenant_id,
        board_kpis=kpis,
        compliance_overview=compliance_overview,
    )
    return AIBoardGovernanceReport(
        tenant_id=tenant_id,
        generated_at=generated_at,
        period="last_12_months",
        kpis=kpis,
        compliance_overview=compliance_overview,
        incidents_overview=incidents_overview,
        supplier_risk_overview=supplier_risk_overview,
        alerts=alerts,
    )


@app.post(
    "/api/v1/ai-governance/report/board/export-jobs",
    response_model=BoardReportExportJob,
    status_code=status.HTTP_201_CREATED,
)
def create_board_report_export_job(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    body: BoardReportExportJobCreate,
) -> BoardReportExportJob:
    """Erstellt Export-Job (Report + Markdown), optional Webhook-POST an callback_url."""
    if body.target_system == "generic_webhook" and not body.callback_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="callback_url required for target_system generic_webhook",
        )
    if body.target_system == "sap_btp_http" and not body.callback_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="callback_url required for target_system sap_btp_http",
        )
    if body.target_system == "datev_dms_prepared" and not body.callback_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="callback_url required for target_system datev_dms_prepared",
        )
    tenant_id = auth_context.tenant_id
    report = _build_board_report(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        incident_repo=incident_repo,
        nis2_repo=nis2_repo,
    )
    job = run_export_job(tenant_id=tenant_id, report=report, body=body)
    return job


@app.get(
    "/api/v1/ai-governance/report/board/export-jobs/{job_id}",
    response_model=BoardReportExportJob,
)
def get_board_report_export_job(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    job_id: str,
) -> BoardReportExportJob:
    """Liefert Export-Job-Status (Tenant-isoliert)."""
    job = get_job(job_id, auth_context.tenant_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )
    return job


# --- Board-Report Audit-Records (WP-/Prüfungsdokumentation, Audit-Ready) ---


@app.post(
    "/api/v1/ai-governance/report/board/audit-records",
    response_model=BoardReportAuditRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_board_report_audit_record(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    body: BoardReportAuditRecordCreate,
) -> BoardReportAuditRecord:
    """Legt einen Audit-Record für den aktuellen Board-Report an (Version = Hash)."""
    tenant_id = auth_context.tenant_id
    created_by = (auth_context.api_key[:8] + "…") if auth_context.api_key else "api"
    report = _build_board_report(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        incident_repo=incident_repo,
        nis2_repo=nis2_repo,
    )
    record = create_audit_record(
        tenant_id=tenant_id,
        report=report,
        body=body,
        created_by=created_by,
    )
    return record


@app.get(
    "/api/v1/ai-governance/report/board/audit-records",
    response_model=list[BoardReportAuditRecord],
)
def list_board_report_audit_records(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter nach status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BoardReportAuditRecord]:
    """Listet Audit-Records des Tenants (paginiert, optional nach status)."""
    return list_records(
        auth_context.tenant_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/v1/ai-governance/report/board/audit-records/{audit_id}",
    response_model=BoardReportAuditRecordWithJobs,
)
def get_board_report_audit_record(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_id: str,
) -> BoardReportAuditRecordWithJobs:
    """Details eines Audit-Records inkl. referenzierter Export-Jobs."""
    record = get_record(audit_id, auth_context.tenant_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found",
        )
    linked_jobs: list[BoardReportExportJob] = []
    for jid in record.linked_export_job_ids:
        job = get_job(jid, auth_context.tenant_id)
        if job is not None:
            linked_jobs.append(job)
    return BoardReportAuditRecordWithJobs(
        **record.model_dump(),
        linked_export_jobs=linked_jobs,
    )


@app.post(
    "/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
    response_model=list[NormEvidenceLink],
    status_code=status.HTTP_201_CREATED,
)
def create_norm_evidence_for_audit_record(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_id: str,
    body: NormEvidenceLinkCreate | list[NormEvidenceLinkCreate],
) -> list[NormEvidenceLink]:
    """Legt einen oder mehrere NormEvidenceLinks für einen Audit-Record an."""
    record = get_record(audit_id, auth_context.tenant_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found",
        )
    payloads = body if isinstance(body, list) else [body]
    return create_links(
        tenant_id=auth_context.tenant_id,
        audit_record_id=audit_id,
        payloads=payloads,
    )


@app.get(
    "/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
    response_model=list[NormEvidenceLink],
)
def list_norm_evidence_for_audit_record(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_id: str,
) -> list[NormEvidenceLink]:
    """Liefert alle Norm-Nachweise für einen Audit-Record (Tenant-isoliert)."""
    record = get_record(audit_id, auth_context.tenant_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit record not found",
        )
    return list_by_audit(auth_context.tenant_id, audit_id)


@app.get(
    "/api/v1/ai-governance/norm-evidence",
    response_model=list[NormEvidenceWithAudit],
)
def query_norm_evidence(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    framework: NormFramework | None = Query(default=None),
    reference: str | None = Query(default=None),
) -> list[NormEvidenceWithAudit]:
    """Liefert Norm-Nachweise nach Framework/Referenz mit Basis-Audit-Infos."""
    matches = query_by_norm(auth_context.tenant_id, framework, reference)
    results: list[NormEvidenceWithAudit] = []
    for ev in matches:
        record = get_record(ev.audit_record_id, auth_context.tenant_id)
        if record is None:
            continue
        results.append(
            NormEvidenceWithAudit(
                evidence=ev,
                audit_record_id=record.id,
                report_generated_at=record.report_generated_at,
                purpose=record.purpose,
            ),
        )
    return results


@app.get(
    "/api/v1/ai-governance/report/board/norm-evidence-defaults",
    response_model=list[NormEvidenceLinkCreate],
)
def get_norm_evidence_defaults(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> list[NormEvidenceLinkCreate]:
    """Liefert vordefinierte Norm-Nachweis-Vorschläge (nur Lesen, keine Anlage)."""
    _ = auth_context.tenant_id  # Auth/Tenant-Kontext erzwingen (keine Tenant-spezifischen Defaults)
    return get_default_norm_evidence_suggestions()


@app.get(
    "/api/v1/ai-governance/high-risk-scenarios",
    response_model=list[HighRiskScenarioProfile],
)
def get_high_risk_scenarios(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> list[HighRiskScenarioProfile]:
    """High-Risk-AI-Szenario-Profile mit empfohlenen Norm-Nachweisen (nur Lesen, keine Anlage)."""
    _ = auth_context.tenant_id
    return list_high_risk_scenarios()


# --- Beispiel-Payload-Endpoint (NUR DEV/DOCS – nicht für Produktion) ---
def _get_export_payload_example(target_system: str) -> dict:
    """Statisches Beispiel-Payload für sap_btp_http (1:1 in SAP Cloud Integration testbar)."""
    if target_system != "sap_btp_http":
        return {}
    example_md = (
        "# AI Governance Board Report – example-tenant-001\n\n"
        "*Berichtszeitraum: last_12_months*\n\n---\n\n"
        "## 1. Executive Summary\n\n"
        "- AI-Systeme gesamt: 0 (aktiv: 0).\n"
        "- High-Risk-Systeme: 0; davon ohne DPIA: 0.\n\n"
        "## 2. KPIs & Compliance\n\n"
        "(Beispiel – keine echten personenbezogenen Daten.)\n"
    )
    return {
        "_comment": "Beispiel-Payload (DEV/Docs only). Keine echten Daten.",
        "tenant_id": "example-tenant-001",
        "report_period": "last_12_months",
        "markdown": example_md,
        "report_metadata": {
            "job_id": "00000000-0000-0000-0000-000000000001",
            "generated_at": "2026-03-14T12:00:00+00:00",
            "period": "last_12_months",
        },
    }


@app.get(
    "/api/v1/ai-governance/report/board/export-payload-example",
    summary="[DEV/Docs only] Beispiel-Payload für Export-Integration",
)
def get_board_report_export_payload_example(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    target_system: Annotated[
        str, Query(description="target_system (z.B. sap_btp_http)")
    ] = "sap_btp_http",
) -> dict:
    """
    Beispiel-Payload-JSON für target_system (z.B. sap_btp_http).
    DEV/Docs only – erzeugt keinen Job. In Produktion deaktiviert.
    """
    if APP_ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export payload example not available in production",
        )
    payload = _get_export_payload_example(target_system)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Example not available for target_system={target_system}",
        )
    return payload


@app.get(
    "/api/v1/ai-governance/incidents/overview",
    response_model=AIIncidentOverview,
)
def get_ai_governance_incidents_overview(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    incident_repository: Annotated[IncidentRepository, Depends(get_incident_repository)],
) -> AIIncidentOverview:
    """NIS2 Art. 21/23, ISO 42001 Incident Management – Board-Drilldown."""
    return compute_ai_incident_overview(
        tenant_id=auth_context.tenant_id,
        incident_repository=incident_repository,
    )


@app.get(
    "/api/v1/ai-governance/incidents/by-system",
    response_model=list[AIIncidentBySystemEntry],
)
def get_ai_governance_incidents_by_system(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    incident_repository: Annotated[IncidentRepository, Depends(get_incident_repository)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> list[AIIncidentBySystemEntry]:
    """Incidents pro KI-System für Board-Drilldown (Top-Systeme)."""
    return compute_ai_incidents_by_system(
        tenant_id=auth_context.tenant_id,
        incident_repository=incident_repository,
        ai_system_repository=ai_repository,
    )


@app.get(
    "/api/v1/ai-governance/suppliers/overview",
    response_model=AISupplierRiskOverview,
)
def get_ai_governance_suppliers_overview(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> AISupplierRiskOverview:
    """NIS2 Art. 21/24 Supply-Chain-Risiko – Board-Drilldown."""
    return compute_ai_supplier_risk_overview(
        tenant_id=auth_context.tenant_id,
        ai_system_repository=ai_repository,
    )


@app.get(
    "/api/v1/ai-governance/suppliers/by-system",
    response_model=list[AISupplierRiskBySystemEntry],
)
def get_ai_governance_suppliers_by_system(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> list[AISupplierRiskBySystemEntry]:
    """Supplier-Risiko pro KI-System für Board-Drilldown."""
    return compute_ai_supplier_risk_by_system(
        tenant_id=auth_context.tenant_id,
        ai_system_repository=ai_repository,
    )


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-governance-kpis",
    response_model=AIGovernanceKpiSummary,
)
def get_ai_governance_kpis(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    policy_repository: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repository: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIGovernanceKpiSummary:
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    return compute_ai_governance_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repository,
        policy_repository=policy_repository,
        violation_repository=violation_repository,
        audit_repository=audit_repository,
        nis2_kritis_kpi_repository=nis2_repo,
    )


@app.get("/api/v1/tenant/compliance-overview", response_model=TenantComplianceOverview)
def get_tenant_compliance_overview(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> TenantComplianceOverview:
    return compute_tenant_compliance_overview(
        tenant_id=auth_context.tenant_id,
        session=session,
    )


@app.get("/api/v1/violations", response_model=list[Violation])
def list_violations(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
) -> list[Violation]:
    return violation_repo.list_violations_for_tenant(tenant_id=tenant_id)


@app.get("/api/v1/ai-systems/{ai_system_id}/violations", response_model=list[Violation])
def list_violations_for_ai_system(
    ai_system_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
) -> list[Violation]:
    return violation_repo.list_violations_for_ai_system(
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
    )


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/policy-report",
    response_model=AISystemPolicyReportResponse,
)
def get_ai_system_policy_report(
    ai_system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Session = Depends(get_session),
) -> AISystemPolicyReportResponse:
    tenant_id = auth.tenant_id

    ai_repo = AISystemRepository(session)
    policy_repo = PolicyRepository(session)
    violation_repo = ViolationRepository(session)
    audit_repo = AuditRepository(session)

    ai_system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if ai_system is None:
        raise HTTPException(status_code=404, detail="AI system not found")

    result = evaluate_policies_for_ai_system(
        tenant_id=tenant_id,
        ai_system=ai_system,
        policy_repository=policy_repo,
        violation_repository=violation_repo,
        audit_repository=audit_repo,
        actor_type="api_key",
        actor_id=auth.api_key,
    )

    # Optional: zusätzliche Actions aus Violations ableiten

    return AISystemPolicyReportResponse(
        ai_system=ai_system,
        violations=result.violations,
    )


# ─── EU AI Act Classification Endpoints ────────────────────────────────────────


@app.post("/api/v1/ai-systems/{ai_system_id}/classify", response_model=RiskClassification)
def classify_system(
    ai_system_id: str,
    questionnaire: ClassificationQuestionnaire,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> RiskClassification:
    tenant_id = auth_context.tenant_id
    ai_system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if ai_system is None:
        raise HTTPException(status_code=404, detail="AI system not found")

    result = classify_ai_system(ai_system_id, questionnaire)
    saved = cls_repo.save(tenant_id, result)

    # Auto-create compliance requirements for high-risk systems
    if saved.risk_level == "high_risk":
        gap_repo.ensure_requirements_exist(tenant_id, ai_system_id, "high_risk")

    audit_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system",
        entity_id=ai_system_id,
        action="classified",
        metadata={"risk_level": saved.risk_level, "path": saved.classification_path},
    )
    return saved


@app.get("/api/v1/ai-systems/{ai_system_id}/classification", response_model=RiskClassification)
def get_classification(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
) -> RiskClassification:
    result = cls_repo.get_for_system(auth_context.tenant_id, ai_system_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No classification found for this AI system")
    return result


@app.put("/api/v1/ai-systems/{ai_system_id}/classification", response_model=RiskClassification)
def override_classification(
    ai_system_id: str,
    override: ClassificationOverrideRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> RiskClassification:
    tenant_id = auth_context.tenant_id
    ai_system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if ai_system is None:
        raise HTTPException(status_code=404, detail="AI system not found")

    previous = cls_repo.get_for_system(tenant_id, ai_system_id)
    saved = cls_repo.save_override(tenant_id, ai_system_id, override, auth_context.api_key)

    if saved.risk_level == "high_risk":
        gap_repo.ensure_requirements_exist(tenant_id, ai_system_id, "high_risk")

    audit_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system",
        entity_id=ai_system_id,
        action="classification_overridden",
        metadata={
            "previous_risk_level": previous.risk_level if previous else None,
            "new_risk_level": saved.risk_level,
            "rationale": override.rationale,
        },
    )
    return saved


@app.get("/api/v1/classifications/summary", response_model=ClassificationSummary)
def get_classification_summary(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
) -> ClassificationSummary:
    return cls_repo.summary_for_tenant(auth_context.tenant_id)


# ─── Gap Analysis / Compliance Status Endpoints ────────────────────────────────


@app.get("/api/v1/ai-systems/{ai_system_id}/compliance", response_model=list[ComplianceStatusEntry])
def get_system_compliance(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
) -> list[ComplianceStatusEntry]:
    return gap_repo.list_for_system(auth_context.tenant_id, ai_system_id)


@app.put(
    "/api/v1/ai-systems/{ai_system_id}/compliance/{requirement_id}",
    response_model=ComplianceStatusEntry,
)
def update_compliance_status(
    ai_system_id: str,
    requirement_id: str,
    update: ComplianceStatusUpdate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> ComplianceStatusEntry:
    if requirement_id not in REQUIREMENTS_BY_ID:
        raise HTTPException(status_code=400, detail=f"Unknown requirement: {requirement_id}")

    result = gap_repo.update_status(
        auth_context.tenant_id, ai_system_id, requirement_id, update, auth_context.api_key
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Compliance status entry not found")

    audit_repo.log_event(
        tenant_id=auth_context.tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="compliance_status",
        entity_id=f"{ai_system_id}/{requirement_id}",
        action="compliance_updated",
        metadata={"status": update.status, "requirement": requirement_id},
    )
    return result


@app.get("/api/v1/compliance/requirements", response_model=list[ComplianceRequirement])
def list_compliance_requirements() -> list[ComplianceRequirement]:
    return REQUIREMENTS


@app.get("/api/v1/compliance/dashboard", response_model=ComplianceDashboard)
def get_compliance_dashboard(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
) -> ComplianceDashboard:
    return compute_compliance_dashboard(
        tenant_id=auth_context.tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
    )
