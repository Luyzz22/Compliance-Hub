from __future__ import annotations

import csv
import io
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import quote

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.advisor_models import AdvisorTenantReport
from app.advisor_portfolio_models import AdvisorPortfolioResponse
from app.ai_act_doc_models import (
    AIActDoc,
    AIActDocListResponse,
    AIActDocSectionKey,
    AIActDocUpsertRequest,
)
from app.ai_compliance_board_report_models import (
    AdvisorBoardReportsPortfolioResponse,
    AiComplianceBoardReportCreateBody,
    AiComplianceBoardReportCreateResponse,
    AiComplianceBoardReportDetailResponse,
    AiComplianceBoardReportListItem,
)
from app.ai_governance_action_models import (
    AIGovernanceActionCreate,
    AIGovernanceActionDraftRequest,
    AIGovernanceActionDraftResponse,
    AIGovernanceActionRead,
    AIGovernanceActionUpdate,
    GovernanceActionStatus,
)
from app.ai_governance_models import (
    AIBoardGovernanceReport,
    AIBoardKpiSummary,
    AIGovernanceKpiSummary,
    AIKpiAlert,
    AIKpiAlertExport,
    BoardKpiExportJob,
    BoardKpiExportJobCreate,
    BoardReportAuditRecord,
    BoardReportAuditRecordCreate,
    BoardReportAuditRecordWithJobs,
    BoardReportExportJob,
    BoardReportExportJobCreate,
    HighRiskScenarioProfile,
    NormEvidenceLink,
    NormEvidenceLinkCreate,
    NormFramework,
    WhatIfScenarioInput,
    WhatIfScenarioResult,
)
from app.ai_kpi_models import (
    AiKpiSummaryResponse,
    AiSystemKpisListResponse,
    AiSystemKpiUpsertBody,
    AiSystemKpiUpsertResponse,
)
from app.ai_system_models import (
    AIImportResult,
    AISystem,
    AISystemComplianceReport,
    AISystemCreate,
    AISystemRiskLevel,
    AISystemStatus,
    AISystemUpdate,
)
from app.audit_models import AuditEvent, AuditLog
from app.auth_dependencies import (
    get_api_key_and_tenant,
    get_auth_context,
    require_path_tenant_matches_auth,
)
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
from app.config.nis2_kritis_board_alert_thresholds import NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT
from app.cross_regulation_models import (
    AISystemRegulatoryHintOut,
    CrossRegLlmGapAssistantRequestBody,
    CrossRegLlmGapAssistantResponse,
    CrossRegulationSummaryResponse,
    RegulatoryControlOut,
    RegulatoryFrameworkOut,
    RegulatoryRequirementOut,
    RequirementControlsDetailResponse,
)
from app.db import engine, get_session
from app.demo_models import DemoSeedRequest, DemoSeedResponse
from app.demo_templates import DemoTenantTemplate, list_demo_tenant_templates
from app.eu_ai_act_readiness_models import EUAIActReadinessOverview
from app.evidence_models import EvidenceFile, EvidenceFileListResponse
from app.explain_models import ExplainRequest, ExplainResponse
from app.feature_flags import (
    FeatureFlag,
    create_feature_guard,
    is_feature_enabled,
    require_tenant_llm_features,
)
from app.incident_models import AIIncidentBySystemEntry, AIIncidentOverview
from app.llm_models import LLMTaskType
from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    DocumentType,
    EInvoiceFormat,
)
from app.models_db import Base, TenantApiKeyDB
from app.nis2_kritis_models import (
    Nis2KritisKpi,
    Nis2KritisKpiDrilldown,
    Nis2KritisKpiListResponse,
    Nis2KritisKpiSuggestionBody,
    Nis2KritisKpiSuggestionRequest,
    Nis2KritisKpiSuggestionResponse,
    Nis2KritisKpiUpsertRequest,
)
from app.policy_models import Violation
from app.policy_service import evaluate_policies_for_ai_system
from app.provisioning_models import (
    ProvisionTenantRequest,
    ProvisionTenantResponse,
    TenantApiKeyCreateBody,
    TenantApiKeyCreated,
    TenantApiKeyRead,
)
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_act_docs import AIActDocRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.evidence_files import EvidenceFileRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.tenant_ai_governance_setup import TenantAIGovernanceSetupRepository
from app.repositories.tenant_api_keys import TenantApiKeyRepository
from app.repositories.violations import ViolationRepository
from app.security import (
    AuthContext,
    delete_evidence_allowed_for_api_key,
    ensure_demo_tenant_seed_allowed,
    require_admin_provision_api_key,
    require_advisor_api_access,
    require_demo_seed_api_key,
)
from app.services import llm_client as llm_client_mod
from app.services import usage_event_logger as usage_event_logger
from app.services.advisor_board_reports import (
    get_board_report_detail_for_advisor,
    list_advisor_portfolio_board_reports,
)
from app.services.advisor_portfolio import (
    advisor_portfolio_to_csv,
    advisor_portfolio_to_json_bytes,
    build_advisor_portfolio,
)
from app.services.advisor_report_llm_enrichment import maybe_enrich_advisor_report_with_llm_summary
from app.services.advisor_tenant_report import build_advisor_tenant_report
from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown
from app.services.ai_act_docs import build_ai_act_doc_list_response, upsert_ai_act_doc
from app.services.ai_act_docs_ai_assist import generate_ai_act_doc_draft
from app.services.ai_act_docs_export import render_ai_act_documentation_markdown
from app.services.ai_action_drafts import generate_action_drafts
from app.services.ai_board_alerts import compute_board_alerts
from app.services.ai_compliance_board_report import (
    create_ai_compliance_board_report,
    get_ai_compliance_board_report_detail,
    list_ai_compliance_board_reports,
)
from app.services.ai_explain import explain_kpi_or_alert
from app.services.ai_governance_incidents import (
    compute_ai_incident_overview,
    compute_ai_incidents_by_system,
)
from app.services.ai_governance_kpis import compute_ai_board_kpis, compute_ai_governance_kpis
from app.services.ai_governance_suppliers import (
    compute_ai_supplier_risk_by_system,
    compute_ai_supplier_risk_overview,
)
from app.services.ai_kpi_seed import ensure_ai_kpi_definitions_seeded
from app.services.ai_kpi_service import (
    build_ai_kpi_summary,
    list_kpis_for_ai_system,
    upsert_kpi_value,
)
from app.services.ai_system_import import import_ai_systems_from_file
from app.services.board_kpi_export import board_kpi_export_csv, build_board_kpi_export_envelope
from app.services.board_kpi_export_jobs import get_kpi_job, register_kpi_export_job
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
from app.services.cross_regulation import (
    build_cross_regulation_summary,
    get_requirement_controls_detail,
    list_ai_system_regulatory_hints,
    list_regulatory_controls,
    list_regulatory_frameworks,
    list_regulatory_requirement_rows,
)
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps
from app.services.cross_regulation_llm_gap_assistant import (
    generate_cross_regulation_llm_gap_suggestions,
)
from app.services.cross_regulation_seed import ensure_cross_regulation_catalog_seeded
from app.services.demo_tenant_seeder import seed_demo_tenant
from app.services.eu_ai_act_readiness import compute_eu_ai_act_readiness_overview
from app.services.evidence_service import (
    delete_evidence as delete_evidence_file,
)
from app.services.evidence_service import (
    download_evidence,
)
from app.services.evidence_service import (
    list_evidence as list_evidence_files,
)
from app.services.evidence_service import (
    upload_evidence as upload_evidence_file,
)
from app.services.evidence_storage import get_evidence_storage
from app.services.high_risk_scenarios import list_high_risk_scenarios
from app.services.llm_router import LLMRouter
from app.services.nis2_kritis_ai_assist import generate_nis2_kpi_suggestions
from app.services.nis2_kritis_alert_signals import build_nis2_kritis_alert_signals
from app.services.nis2_kritis_drilldown import build_nis2_kritis_kpi_drilldown
from app.services.nis2_kritis_kpis import recommended_kpis_for_ai_system
from app.services.setup_status import compute_tenant_setup_status
from app.services.tenant_ai_governance_setup import (
    apply_setup_patch,
    build_setup_response,
    normalize_payload,
)
from app.services.tenant_compliance_overview import (
    TenantComplianceOverview,
    compute_tenant_compliance_overview,
)
from app.services.tenant_provisioning import provision_tenant
from app.services.tenant_usage_metrics import compute_tenant_usage_metrics
from app.services.what_if_simulator import simulate_board_impact
from app.setup_models import TenantSetupStatus
from app.supplier_risk_models import (
    AISupplierRiskBySystemEntry,
    AISupplierRiskOverview,
)
from app.tenant_ai_governance_setup_models import (
    TenantAIGovernanceSetupPatch,
    TenantAIGovernanceSetupResponse,
)
from app.usage_metrics_models import TenantUsageMetricsResponse

APP_VERSION = os.getenv("COMPLIANCEHUB_VERSION", "0.1.0")
APP_ENVIRONMENT = os.getenv("COMPLIANCEHUB_ENV", "dev")


class LLMInvokeRequest(BaseModel):
    task_type: LLMTaskType
    prompt: str = Field(..., min_length=1, max_length=48000)


class LLMInvokeResponse(BaseModel):
    text: str
    provider: str
    model_id: str
    input_tokens_est: int = Field(default=0, ge=0)
    output_tokens_est: int = Field(default=0, ge=0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Enterprise lifespan context manager for ComplianceHub.

    Startup: Initialize database schema (ISO 27001/NIS2 compliant)
    Shutdown: Graceful connection cleanup, audit log flush
    """
    # Startup phase
    Base.metadata.create_all(bind=engine)
    with Session(engine) as seed_session:
        ensure_cross_regulation_catalog_seeded(seed_session)
        ensure_ai_kpi_definitions_seeded(seed_session)
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


def get_ai_governance_action_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AIGovernanceActionRepository:
    return AIGovernanceActionRepository(session)


def get_evidence_file_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EvidenceFileRepository:
    return EvidenceFileRepository(session)


def get_ai_act_doc_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AIActDocRepository:
    return AIActDocRepository(session)


def _ensure_feature_ai_act_docs(tenant_id: str, session: Session) -> None:
    if not is_feature_enabled(FeatureFlag.ai_act_docs, tenant_id, session=session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI Act documentation feature is disabled for this tenant.",
        )


def _ensure_feature_what_if_simulator(tenant_id: str, session: Session) -> None:
    if not is_feature_enabled(FeatureFlag.what_if_simulator, tenant_id, session=session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="What-if simulator feature is disabled for this tenant.",
        )


def _require_high_risk_system(
    tenant_id: str,
    ai_repo: AISystemRepository,
    ai_system_id: str,
) -> AISystem:
    system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )
    if system.risk_level != AISystemRiskLevel.high:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EU AI Act documentation is only available for high-risk AI systems.",
        )
    return system


def get_advisor_tenant_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AdvisorTenantRepository:
    return AdvisorTenantRepository(session)


def get_tenant_api_key_repository(
    session: Annotated[Session, Depends(get_session)],
) -> TenantApiKeyRepository:
    return TenantApiKeyRepository(session)


def get_tenant_ai_governance_setup_repository(
    session: Annotated[Session, Depends(get_session)],
) -> TenantAIGovernanceSetupRepository:
    return TenantAIGovernanceSetupRepository(session)


def _ensure_tenant_path_matches_auth(tenant_id: str, auth: AuthContext) -> None:
    if auth.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID does not match authenticated tenant",
        )


def require_evidence_delete_capability(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    if not delete_evidence_allowed_for_api_key(auth_context.api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Evidence delete not permitted for this API key",
        )
    return auth_context


def _evidence_form_opt(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _evidence_content_disposition(filename: str) -> str:
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "")
    enc = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{enc}"


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
    policy_repo.ensure_default_policy_rules(tenant_id)

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


@app.post("/api/v1/ai-systems/import", response_model=AIImportResult)
async def import_ai_systems(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    audit_event_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    file: UploadFile = File(..., description="CSV- oder Excel-Datei (.xlsx)"),
) -> AIImportResult:
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty upload",
        )
    return import_ai_systems_from_file(
        tenant_id=auth_context.tenant_id,
        auth=auth_context,
        filename=file.filename or "import.csv",
        data=raw,
        repository=repository,
        audit_log_repo=audit_repo,
        audit_event_repo=audit_event_repo,
        policy_repo=policy_repo,
        violation_repo=violation_repo,
    )


@app.post(
    "/api/v1/evidence/uploads",
    response_model=EvidenceFile,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence_api(
    _ff_evidence: Annotated[None, Depends(create_feature_guard(FeatureFlag.evidence_uploads))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    file: UploadFile = File(...),
    ai_system_id: Annotated[str | None, Form()] = None,
    audit_record_id: Annotated[str | None, Form()] = None,
    action_id: Annotated[str | None, Form()] = None,
    norm_framework: Annotated[str | None, Form()] = None,
    norm_reference: Annotated[str | None, Form()] = None,
    x_uploaded_by: Annotated[str | None, Header(alias="x-uploaded-by")] = None,
) -> EvidenceFile:
    storage = get_evidence_storage()
    uploaded_by = (x_uploaded_by or "").strip()[:320] or "api_client"
    created = await upload_evidence_file(
        tenant_id=auth_context.tenant_id,
        uploaded_by=uploaded_by,
        file=file,
        ai_system_id=_evidence_form_opt(ai_system_id),
        audit_record_id=_evidence_form_opt(audit_record_id),
        action_id=_evidence_form_opt(action_id),
        norm_framework=_evidence_form_opt(norm_framework),
        norm_reference=_evidence_form_opt(norm_reference),
        evidence_repo=evidence_repo,
        storage=storage,
        ai_repo=ai_repo,
        action_repo=action_repo,
    )
    usage_event_logger.log_usage_event(
        session,
        auth_context.tenant_id,
        usage_event_logger.EVIDENCE_UPLOADED,
        {"evidence_id": created.id},
    )
    return created


@app.get("/api/v1/evidence", response_model=EvidenceFileListResponse)
def list_evidence_api(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
    ai_system_id: Annotated[str | None, Query()] = None,
    audit_record_id: Annotated[str | None, Query()] = None,
    action_id: Annotated[str | None, Query()] = None,
) -> EvidenceFileListResponse:
    items = list_evidence_files(
        auth_context.tenant_id,
        ai_system_id=_evidence_form_opt(ai_system_id),
        audit_record_id=_evidence_form_opt(audit_record_id),
        action_id=_evidence_form_opt(action_id),
        evidence_repo=evidence_repo,
    )
    return EvidenceFileListResponse(items=items)


@app.get("/api/v1/evidence/{evidence_id}/download")
def download_evidence_api(
    evidence_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> Response:
    storage = get_evidence_storage()
    blob, content_type, filename = download_evidence(
        auth_context.tenant_id,
        evidence_id,
        evidence_repo=evidence_repo,
        storage=storage,
    )
    return Response(
        content=blob,
        media_type=content_type,
        headers={"Content-Disposition": _evidence_content_disposition(filename)},
    )


@app.delete("/api/v1/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence_api(
    evidence_id: str,
    auth_context: Annotated[AuthContext, Depends(require_evidence_delete_capability)],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> Response:
    storage = get_evidence_storage()
    delete_evidence_file(
        auth_context.tenant_id,
        evidence_id,
        evidence_repo=evidence_repo,
        storage=storage,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@app.post(
    "/api/v1/ai-systems/{ai_system_id}/nis2-kritis-kpi-suggestions",
    response_model=Nis2KritisKpiSuggestionResponse,
    tags=["nis2-kritis"],
)
def post_nis2_kritis_kpi_suggestions(
    ai_system_id: str,
    body: Nis2KritisKpiSuggestionBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> Nis2KritisKpiSuggestionResponse:
    """KI-Vorschläge für NIS2-/KRITIS-KPIs aus Freitext (ohne Persistenz)."""
    tenant_id = auth_context.tenant_id
    require_tenant_llm_features(tenant_id, session, FeatureFlag.llm_kpi_suggestions)
    system = ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id)
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AISystem not found",
        )
    kpis = nis2_repo.list_for_ai_system(tenant_id, ai_system_id)
    existing = [{"kpi_type": k.kpi_type.value, "value_percent": k.value_percent} for k in kpis]
    req = Nis2KritisKpiSuggestionRequest(ai_system_id=ai_system_id, free_text=body.free_text)
    try:
        out = generate_nis2_kpi_suggestions(
            system,
            req,
            tenant_id,
            session=session,
            existing_kpis_summary=existing,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.LLM_KPI_SUGGESTION_REQUESTED,
        {"ai_system_id": ai_system_id},
    )
    return out


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs",
    response_model=AIActDocListResponse,
    tags=["ai-act-docs"],
)
def list_ai_act_docs_for_system(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
) -> AIActDocListResponse:
    tenant_id = auth_context.tenant_id
    _ensure_feature_ai_act_docs(tenant_id, session)
    _require_high_risk_system(tenant_id, ai_repo, ai_system_id)
    return build_ai_act_doc_list_response(ai_system_id, doc_repo, tenant_id)


@app.post(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs/{section_key}/draft",
    response_model=AIActDoc,
    tags=["ai-act-docs"],
)
def post_ai_act_doc_draft(
    ai_system_id: str,
    section_key: AIActDocSectionKey,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> AIActDoc:
    tenant_id = auth_context.tenant_id
    _ensure_feature_ai_act_docs(tenant_id, session)
    require_tenant_llm_features(
        tenant_id,
        session,
        FeatureFlag.llm_legal_reasoning,
        FeatureFlag.llm_report_assistant,
    )
    system = _require_high_risk_system(tenant_id, ai_repo, ai_system_id)
    classification = cls_repo.get_for_system(tenant_id, ai_system_id)
    kpis = nis2_repo.list_for_ai_system(tenant_id, ai_system_id)
    actions = [
        {"title": a.title, "status": a.status.value, "related_requirement": a.related_requirement}
        for a in action_repo.list_for_tenant(tenant_id, limit=200)
        if a.related_ai_system_id == ai_system_id
    ]
    ev = evidence_repo.list_for_tenant(tenant_id, ai_system_id=ai_system_id)
    try:
        draft = generate_ai_act_doc_draft(
            system,
            section_key,
            tenant_id,
            session=session,
            classification=classification,
            nis2_kpis=kpis,
            actions_brief=actions,
            evidence_file_count=len(ev),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.LLM_AI_ACT_DOC_DRAFT_REQUESTED,
        {"ai_system_id": ai_system_id, "section": section_key.value},
    )
    return draft


@app.post(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs/{section_key}",
    response_model=AIActDoc,
    tags=["ai-act-docs"],
)
def persist_ai_act_doc_section(
    ai_system_id: str,
    section_key: AIActDocSectionKey,
    body: AIActDocUpsertRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
) -> AIActDoc:
    tenant_id = auth_context.tenant_id
    _ensure_feature_ai_act_docs(tenant_id, session)
    _require_high_risk_system(tenant_id, ai_repo, ai_system_id)
    actor = "api_client"
    return upsert_ai_act_doc(doc_repo, tenant_id, ai_system_id, section_key, body, actor)


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs/export",
    tags=["ai-act-docs"],
)
def export_ai_act_docs_markdown(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
    format: Annotated[
        Literal["markdown"],
        Query(description="Nur markdown unterstützt; PDF später extern."),
    ] = "markdown",
) -> Response:
    tenant_id = auth_context.tenant_id
    _ensure_feature_ai_act_docs(tenant_id, session)
    system = _require_high_risk_system(tenant_id, ai_repo, ai_system_id)
    if format != "markdown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only format=markdown is supported.",
        )
    classification = cls_repo.get_for_system(tenant_id, ai_system_id)
    kpis = nis2_repo.list_for_ai_system(tenant_id, ai_system_id)
    actions = action_repo.list_for_tenant(tenant_id, limit=500)
    ev = evidence_repo.list_for_tenant(tenant_id, ai_system_id=ai_system_id)
    md = render_ai_act_documentation_markdown(
        system=system,
        classification=classification,
        nis2_kpis=kpis,
        actions=actions,
        evidence_count=len(ev),
        docs_repo=doc_repo,
        tenant_id=tenant_id,
    )
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="ai-act-documentation-{ai_system_id}.md"',
        },
    )


@app.post(
    "/api/v1/ai-governance/what-if/board-impact",
    response_model=WhatIfScenarioResult,
    tags=["ai-governance"],
)
def post_what_if_board_impact(
    body: WhatIfScenarioInput,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> WhatIfScenarioResult:
    tenant_id = auth_context.tenant_id
    _ensure_feature_what_if_simulator(tenant_id, session)
    return simulate_board_impact(
        body,
        tenant_id,
        session=session,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        nis2_repo=nis2_repo,
    )


@app.post(
    "/api/v1/ai-governance/explain",
    response_model=ExplainResponse,
    tags=["ai-governance"],
)
def post_ai_governance_explain(
    body: ExplainRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ExplainResponse:
    """Kurzerklärung zu Board-KPI oder Alert (LLM, nicht persistiert)."""
    tenant_id = auth_context.tenant_id
    require_tenant_llm_features(tenant_id, session, FeatureFlag.llm_explain)
    try:
        result = explain_kpi_or_alert(body, tenant_id, session=session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.LLM_EXPLAIN_REQUESTED,
        {"kpi_key": body.kpi_key},
    )
    return result


@app.post(
    "/api/v1/ai-governance/action-drafts",
    response_model=AIGovernanceActionDraftResponse,
    tags=["ai-governance"],
)
def post_ai_governance_action_drafts(
    body: AIGovernanceActionDraftRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> AIGovernanceActionDraftResponse:
    """Governance-Action-Entwürfe aus Lücken (LLM, ohne Persistenz)."""
    tenant_id = auth_context.tenant_id
    require_tenant_llm_features(tenant_id, session, FeatureFlag.llm_action_drafts)
    try:
        out = generate_action_drafts(body, tenant_id, session=session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.LLM_ACTION_DRAFT_REQUESTED,
        {"requirement_count": len(body.requirements)},
    )
    return out


@app.get(
    "/api/v1/nis2-kritis/kpi-drilldown",
    response_model=Nis2KritisKpiDrilldown,
    tags=["nis2-kritis"],
)
def get_nis2_kritis_kpi_drilldown(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    top_n: Annotated[
        int,
        Query(ge=1, le=50, description="Top-N schwächste Systeme je KPI-Typ"),
    ] = 5,
) -> Nis2KritisKpiDrilldown:
    """Histogramm + Worst-Offenders je NIS2-/KRITIS-KPI-Typ (mandantenisoliert)."""
    return build_nis2_kritis_kpi_drilldown(
        auth_context.tenant_id,
        nis2_repo,
        top_n=top_n,
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
    session: Annotated[Session, Depends(get_session)],
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    violation_repository: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIBoardKpiSummary:
    out = compute_ai_board_kpis(
        tenant_id=auth_context.tenant_id,
        ai_system_repository=ai_repository,
        violation_repository=violation_repository,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    usage_event_logger.log_usage_event(
        session,
        auth_context.tenant_id,
        usage_event_logger.BOARD_VIEW_OPENED,
        {"surface": "board_kpis"},
    )
    return out


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
    "/api/v1/ai-governance/readiness/eu-ai-act",
    response_model=EUAIActReadinessOverview,
)
def get_eu_ai_act_readiness(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
) -> EUAIActReadinessOverview:
    """Readiness bis Stichtag High-Risk inkl. Gaps, Vorschläge und offene Maßnahmen."""
    return compute_eu_ai_act_readiness_overview(
        tenant_id=auth_context.tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_repo=nis2_repo,
        action_repo=action_repo,
    )


@app.post(
    "/api/v1/ai-governance/actions",
    response_model=AIGovernanceActionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_governance_action(
    body: AIGovernanceActionCreate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> AIGovernanceActionRead:
    tenant_id = auth_context.tenant_id
    if body.related_ai_system_id:
        if ai_repo.get_by_id(tenant_id, body.related_ai_system_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AISystem not found",
            )
    created = action_repo.create(tenant_id, body)
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.GOVERNANCE_ACTION_CREATED,
        {"action_id": created.id},
    )
    return created


@app.get(
    "/api/v1/ai-governance/actions",
    response_model=list[AIGovernanceActionRead],
)
def list_ai_governance_actions(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    status_filter: Annotated[
        GovernanceActionStatus | None,
        Query(alias="status", description="Filter nach Status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AIGovernanceActionRead]:
    return action_repo.list_for_tenant(
        auth_context.tenant_id,
        status=status_filter,
        limit=limit,
    )


@app.get(
    "/api/v1/ai-governance/actions/{action_id}",
    response_model=AIGovernanceActionRead,
)
def get_ai_governance_action(
    action_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
) -> AIGovernanceActionRead:
    row = action_repo.get(auth_context.tenant_id, action_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Governance action not found",
        )
    return row


@app.patch(
    "/api/v1/ai-governance/actions/{action_id}",
    response_model=AIGovernanceActionRead,
)
def update_ai_governance_action(
    action_id: str,
    body: AIGovernanceActionUpdate,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> AIGovernanceActionRead:
    tenant_id = auth_context.tenant_id
    patch = body.model_dump(exclude_unset=True)
    if patch.get("related_ai_system_id"):
        if ai_repo.get_by_id(tenant_id, patch["related_ai_system_id"]) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AISystem not found",
            )
    updated = action_repo.update(tenant_id, action_id, body)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Governance action not found",
        )
    return updated


@app.delete(
    "/api/v1/ai-governance/actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_ai_governance_action(
    action_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
) -> Response:
    if not action_repo.delete(auth_context.tenant_id, action_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Governance action not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _nis2_kritis_board_alert_signals(
    tenant_id: str,
    nis2_repo: Nis2KritisKpiRepository,
):
    return build_nis2_kritis_alert_signals(
        tenant_id,
        nis2_repo,
        ot_it_threshold_percent=NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT,
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
        nis2_kritis_signals=_nis2_kritis_board_alert_signals(tenant_id, nis2_repo),
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
        nis2_kritis_signals=_nis2_kritis_board_alert_signals(tenant_id, nis2_repo),
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


@app.get(
    "/api/v1/ai-governance/report/board/kpi-export",
    response_class=Response,
)
def get_board_kpi_export(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    format: Annotated[
        Literal["json", "csv"],
        Query(description="Export-Format für DMS/DATEV/SAP-BTP-Integration"),
    ] = "json",
) -> Response:
    """Board-KPI- und NIS2-/KRITIS-Werte je KI-System als JSON oder CSV."""
    tenant_id = auth_context.tenant_id
    envelope = build_board_kpi_export_envelope(tenant_id, ai_repo, nis2_repo)
    gen = envelope.generated_at
    if format == "csv":
        csv_content = board_kpi_export_csv(envelope)
        filename = f"board-kpi-export-{tenant_id}-{gen.strftime('%Y%m%d')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    filename = f"board-kpi-export-{tenant_id}-{gen.strftime('%Y%m%d')}.json"
    return Response(
        content=envelope.model_dump_json(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post(
    "/api/v1/ai-governance/report/board/kpi-export/jobs",
    response_model=BoardKpiExportJob,
    status_code=status.HTTP_201_CREATED,
)
def create_board_kpi_export_job(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    body: BoardKpiExportJobCreate,
) -> BoardKpiExportJob:
    """Registriert einen KPI-Export für Audit-Verknüpfung (Zielsystem-Label, kein Versand)."""
    return register_kpi_export_job(auth_context.tenant_id, body)


@app.get(
    "/api/v1/ai-governance/report/board/kpi-export/jobs/{job_id}",
    response_model=BoardKpiExportJob,
)
def get_board_kpi_export_job(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    job_id: str,
) -> BoardKpiExportJob:
    job = get_kpi_job(job_id, auth_context.tenant_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPI export job not found",
        )
    return job


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
        nis2_kritis_signals=_nis2_kritis_board_alert_signals(tenant_id, nis2_repo),
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
    linked_kpi: list[BoardKpiExportJob] = []
    for kid in record.linked_kpi_export_job_ids:
        kj = get_kpi_job(kid, auth_context.tenant_id)
        if kj is not None:
            linked_kpi.append(kj)
    return BoardReportAuditRecordWithJobs(
        **record.model_dump(),
        linked_export_jobs=linked_jobs,
        linked_kpi_export_jobs=linked_kpi,
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


@app.get(
    "/api/v1/tenants/{tenant_id}/setup-status",
    response_model=TenantSetupStatus,
    tags=["tenants"],
)
def get_tenant_setup_status(
    tenant_id: str,
    _ff_setup: Annotated[None, Depends(create_feature_guard(FeatureFlag.guided_setup))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> TenantSetupStatus:
    """Aggregierter Guided-Setup-Status aus Mandantendaten (ohne eigene Setup-Tabelle)."""
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    status_obj = compute_tenant_setup_status(session, tenant_id)
    if status_obj.total_steps > 0 and status_obj.completed_steps >= status_obj.total_steps:
        usage_event_logger.log_usage_event(
            session,
            tenant_id,
            usage_event_logger.GUIDED_SETUP_COMPLETED,
            {"completed_steps": status_obj.completed_steps},
            dedupe_same_type_hours=24,
        )
    return status_obj


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-governance-setup",
    response_model=TenantAIGovernanceSetupResponse,
    tags=["tenants"],
)
def get_tenant_ai_governance_setup(
    tenant_id: str,
    _ff_wizard: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.ai_governance_setup_wizard)),
    ],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    setup_repo: Annotated[
        TenantAIGovernanceSetupRepository,
        Depends(get_tenant_ai_governance_setup_repository),
    ],
) -> TenantAIGovernanceSetupResponse:
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    raw = setup_repo.get_payload(tenant_id)
    payload = normalize_payload(raw)
    return build_setup_response(session, tenant_id, payload)


@app.put(
    "/api/v1/tenants/{tenant_id}/ai-governance-setup",
    response_model=TenantAIGovernanceSetupResponse,
    tags=["tenants"],
)
def put_tenant_ai_governance_setup(
    tenant_id: str,
    body: TenantAIGovernanceSetupPatch,
    _ff_wizard: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.ai_governance_setup_wizard)),
    ],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    setup_repo: Annotated[
        TenantAIGovernanceSetupRepository,
        Depends(get_tenant_ai_governance_setup_repository),
    ],
) -> TenantAIGovernanceSetupResponse:
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    raw = setup_repo.get_payload(tenant_id)
    current = normalize_payload(raw)
    merged = apply_setup_patch(current, body)
    setup_repo.upsert_payload(tenant_id, merged)
    return build_setup_response(session, tenant_id, merged)


@app.get(
    "/api/v1/tenants/{tenant_id}/usage-metrics",
    response_model=TenantUsageMetricsResponse,
    tags=["tenants"],
)
def get_tenant_usage_metrics_endpoint(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> TenantUsageMetricsResponse:
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return compute_tenant_usage_metrics(session, tenant_id)


@app.post(
    "/api/v1/llm/invoke",
    response_model=LLMInvokeResponse,
    tags=["llm"],
)
def post_llm_invoke(
    _ff_llm: Annotated[None, Depends(create_feature_guard(FeatureFlag.llm_enabled))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    body: LLMInvokeRequest,
) -> LLMInvokeResponse:
    """Mandanten-gebundener LLM-Aufruf über den Router (Task-Flags + Policy)."""
    router = LLMRouter(session=session)
    try:
        resp = router.route_and_call(body.task_type, body.prompt, auth_context.tenant_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return LLMInvokeResponse(
        text=resp.text,
        provider=resp.provider.value,
        model_id=resp.model_id,
        input_tokens_est=resp.input_tokens_est,
        output_tokens_est=resp.output_tokens_est,
    )


def _api_key_row_to_read(row: TenantApiKeyDB) -> TenantApiKeyRead:
    created = row.created_at_utc
    created_s = created.isoformat() if hasattr(created, "isoformat") else str(created)
    return TenantApiKeyRead(
        id=row.id,
        name=row.name,
        key_last4=row.key_last4,
        created_at=created_s,
        active=bool(row.active),
    )


@app.post(
    "/api/v1/tenants/provision",
    response_model=ProvisionTenantResponse,
    tags=["tenants"],
)
def post_provision_tenant(
    body: ProvisionTenantRequest,
    _admin: Annotated[str, Depends(require_admin_provision_api_key)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> ProvisionTenantResponse:
    """
    Internes Pilot-Onboarding: Mandant, Default-Feature-Flags, initialer API-Key.
    Schutz über COMPLIANCEHUB_ADMIN_API_KEYS (Header x-api-key).
    """
    try:
        result = provision_tenant(session, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    usage_event_logger.log_usage_event(
        session,
        result.tenant_id,
        usage_event_logger.TENANT_PROVISIONED,
        {
            "advisor_linked": result.advisor_linked,
            "demo_seed_requested": body.enable_demo_seed,
        },
    )

    if not body.enable_demo_seed:
        return result

    try:
        seed_demo_tenant(
            session,
            "kritis_energy",
            result.tenant_id,
            advisor_id=body.advisor_id.strip() if body.advisor_id else None,
            ai_repo=ai_repo,
            cls_repo=cls_repo,
            nis2_repo=nis2_repo,
            policy_repo=policy_repo,
            action_repo=action_repo,
            evidence_repo=evidence_repo,
        )
        usage_event_logger.log_usage_event(
            session,
            result.tenant_id,
            usage_event_logger.TENANT_SEEDED,
            {"template_key": "kritis_energy", "source": "provision"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return result.model_copy(update={"demo_seeded": True})


@app.get(
    "/api/v1/tenants/{tenant_id}/api-keys",
    response_model=list[TenantApiKeyRead],
    tags=["tenants"],
)
def list_tenant_api_keys(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    key_repo: Annotated[TenantApiKeyRepository, Depends(get_tenant_api_key_repository)],
) -> list[TenantApiKeyRead]:
    _ensure_tenant_path_matches_auth(tenant_id, auth_context)
    rows = key_repo.list_for_tenant(tenant_id)
    return [_api_key_row_to_read(r) for r in rows]


@app.post(
    "/api/v1/tenants/{tenant_id}/api-keys",
    response_model=TenantApiKeyCreated,
    tags=["tenants"],
)
def create_tenant_api_key(
    tenant_id: str,
    body: TenantApiKeyCreateBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    key_repo: Annotated[TenantApiKeyRepository, Depends(get_tenant_api_key_repository)],
) -> TenantApiKeyCreated:
    _ensure_tenant_path_matches_auth(tenant_id, auth_context)
    row, plain = key_repo.create_key(tenant_id=tenant_id, name=body.name)
    read = _api_key_row_to_read(row)
    return TenantApiKeyCreated(
        id=read.id,
        name=read.name,
        key_last4=read.key_last4,
        created_at=read.created_at,
        active=read.active,
        plain_key=plain,
    )


@app.delete(
    "/api/v1/tenants/{tenant_id}/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tenants"],
)
def revoke_tenant_api_key(
    tenant_id: str,
    key_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    key_repo: Annotated[TenantApiKeyRepository, Depends(get_tenant_api_key_repository)],
) -> Response:
    _ensure_tenant_path_matches_auth(tenant_id, auth_context)
    row = key_repo.revoke(tenant_id=tenant_id, key_id=key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/portfolio",
    response_model=AdvisorPortfolioResponse,
    tags=["advisors"],
)
def get_advisor_portfolio(
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
) -> AdvisorPortfolioResponse:
    """Berater-Portfolio: Kern-KPIs je zugeordnetem Mandant (keine Cross-Tenant-SQL)."""
    out = build_advisor_portfolio(
        session,
        advisor_id,
        advisor_repo,
        ai_repo,
        cls_repo,
        gap_repo,
        nis2_repo,
        policy_repo,
        violation_repo,
        audit_repo,
        action_repo,
    )
    for t in out.tenants:
        usage_event_logger.log_usage_event(
            session,
            t.tenant_id,
            usage_event_logger.ADVISOR_PORTFOLIO_VIEWED,
            {"advisor_id": advisor_id},
        )
    return out


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/portfolio-export",
    tags=["advisors"],
)
def export_advisor_portfolio(
    _ff_adve: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    export_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> Response:
    """Portfolio als JSON- oder CSV-Datei (Partnermeeting, interne Steuerung)."""
    portfolio = build_advisor_portfolio(
        session,
        advisor_id,
        advisor_repo,
        ai_repo,
        cls_repo,
        gap_repo,
        nis2_repo,
        policy_repo,
        violation_repo,
        audit_repo,
        action_repo,
    )
    for t in portfolio.tenants:
        usage_event_logger.log_usage_event(
            session,
            t.tenant_id,
            usage_event_logger.ADVISOR_PORTFOLIO_VIEWED,
            {"advisor_id": advisor_id, "export": True},
        )
    day = portfolio.generated_at_utc.strftime("%Y-%m-%d")
    if export_format == "csv":
        body = advisor_portfolio_to_csv(portfolio)
        fname = f"advisor-portfolio-{day}.csv"
        return Response(
            content=body.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _evidence_content_disposition(fname)},
        )
    raw = advisor_portfolio_to_json_bytes(portfolio)
    fname = f"advisor-portfolio-{day}.json"
    return Response(
        content=raw,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": _evidence_content_disposition(fname)},
    )


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/report",
    tags=["advisors"],
    response_model=None,
)
def get_advisor_tenant_report(
    _ff_adv_rep: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    export_format: Annotated[Literal["json", "markdown"], Query(alias="format")] = "json",
) -> AdvisorTenantReport | Response:
    """Mandanten-Steckbrief (JSON oder Markdown) nur bei Zuordnung in advisor_tenants."""
    link = advisor_repo.get_link(advisor_id, tenant_id)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    report = build_advisor_tenant_report(
        session,
        tenant_id,
        link=link,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_repo=nis2_repo,
        violation_repo=violation_repo,
        action_repo=action_repo,
    )
    report = maybe_enrich_advisor_report_with_llm_summary(session, tenant_id, report)
    if export_format == "markdown":
        md = render_tenant_report_markdown(report)
        fname = f"tenant-report-{tenant_id}.md"
        usage_event_logger.log_usage_event(
            session,
            tenant_id,
            usage_event_logger.ADVISOR_TENANT_REPORT_VIEWED,
            {"advisor_id": advisor_id, "format": "markdown"},
        )
        return Response(
            content=md.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": _evidence_content_disposition(fname)},
        )
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.ADVISOR_TENANT_REPORT_VIEWED,
        {"advisor_id": advisor_id, "format": "json"},
    )
    return report


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/usage-metrics",
    response_model=TenantUsageMetricsResponse,
    tags=["advisors"],
)
def get_advisor_tenant_usage_metrics(
    _ff_um: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
) -> TenantUsageMetricsResponse:
    if advisor_repo.get_link(advisor_id, tenant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    return compute_tenant_usage_metrics(session, tenant_id)


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/board-reports",
    response_model=AdvisorBoardReportsPortfolioResponse,
    tags=["advisors"],
)
def get_advisor_portfolio_board_reports_endpoint(
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    _ff_br: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report)),
    ],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    limit_per_tenant: Annotated[int, Query(ge=1, le=100)] = 30,
) -> AdvisorBoardReportsPortfolioResponse:
    """KI-Board-Reports aller verknüpften Mandanten (flache Liste, neueste zuerst)."""
    return list_advisor_portfolio_board_reports(
        session,
        advisor_id,
        advisor_repo,
        limit_per_tenant=limit_per_tenant,
    )


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/board/ai-compliance-reports/{report_id}",
    response_model=AiComplianceBoardReportDetailResponse,
    tags=["advisors"],
)
def get_advisor_accessible_board_report_detail(
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    _ff_br: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report)),
    ],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    report_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
) -> AiComplianceBoardReportDetailResponse:
    """Report-Detail nur bei advisor_tenants-Zuordnung (ohne Mandanten-API-Key-Wechsel)."""
    detail = get_board_report_detail_for_advisor(
        session,
        advisor_id,
        tenant_id,
        report_id,
        advisor_repo,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or tenant not linked to advisor",
        )
    return detail


@app.get(
    "/api/v1/demo/tenant-templates",
    response_model=list[DemoTenantTemplate],
    tags=["demo"],
)
def list_demo_tenant_template_definitions(
    _ff_demo: Annotated[None, Depends(create_feature_guard(FeatureFlag.demo_seeding))],
    _api_key: Annotated[str, Depends(require_demo_seed_api_key)],
) -> list[DemoTenantTemplate]:
    """Demo/Pilot: verfügbare Mandanten-Templates (geschützter API-Key)."""
    return list_demo_tenant_templates()


@app.post(
    "/api/v1/demo/tenants/seed",
    response_model=DemoSeedResponse,
    tags=["demo"],
)
def post_demo_tenant_seed(
    body: DemoSeedRequest,
    _ff_demos: Annotated[None, Depends(create_feature_guard(FeatureFlag.demo_seeding))],
    session: Annotated[Session, Depends(get_session)],
    _api_key: Annotated[str, Depends(require_demo_seed_api_key)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    policy_repo: Annotated[PolicyRepository, Depends(get_policy_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> DemoSeedResponse:
    """
    Demo/Pilot: leeren Mandanten aus Template befüllen.
    Nur für tenant_id in COMPLIANCEHUB_DEMO_SEED_TENANT_IDS und mit Demo-Seed-API-Key.
    """
    ensure_demo_tenant_seed_allowed(body.tenant_id)
    try:
        result = seed_demo_tenant(
            session,
            body.template_key,
            body.tenant_id,
            advisor_id=body.advisor_id,
            ai_repo=ai_repo,
            cls_repo=cls_repo,
            nis2_repo=nis2_repo,
            policy_repo=policy_repo,
            action_repo=action_repo,
            evidence_repo=evidence_repo,
        )
        usage_event_logger.log_usage_event(
            session,
            body.tenant_id,
            usage_event_logger.TENANT_SEEDED,
            {
                "template_key": body.template_key,
                "advisor_linked": result.advisor_linked,
            },
        )
        return result
    except ValueError as exc:
        msg = str(exc)
        if "already has AI systems" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


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


# ─── Cross-Regulation / Regelwerksgraph ───────────────────────────────────────


@app.get(
    "/api/v1/tenants/{tenant_id}/compliance/cross-regulation/summary",
    response_model=CrossRegulationSummaryResponse,
)
def cross_regulation_summary(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> CrossRegulationSummaryResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return build_cross_regulation_summary(session, tenant_id)


@app.get(
    "/api/v1/tenants/{tenant_id}/compliance/frameworks",
    response_model=list[RegulatoryFrameworkOut],
)
def cross_regulation_frameworks(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> list[RegulatoryFrameworkOut]:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return list_regulatory_frameworks(session)


@app.get(
    "/api/v1/tenants/{tenant_id}/compliance/regulatory-requirements",
    response_model=list[RegulatoryRequirementOut],
)
def cross_regulation_regulatory_requirements(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
    framework: Annotated[str | None, Query(description="Framework key, z. B. eu_ai_act")] = None,
) -> list[RegulatoryRequirementOut]:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return list_regulatory_requirement_rows(session, tenant_id, framework_key=framework)


@app.get(
    "/api/v1/tenants/{tenant_id}/compliance/regulatory-controls",
    response_model=list[RegulatoryControlOut],
)
def cross_regulation_regulatory_controls(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> list[RegulatoryControlOut]:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return list_regulatory_controls(session, tenant_id)


@app.get(
    "/api/v1/tenants/{tenant_id}/compliance/regulatory-requirements/{requirement_id}/controls",
    response_model=RequirementControlsDetailResponse,
)
def cross_regulation_requirement_controls(
    tenant_id: str,
    requirement_id: int,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> RequirementControlsDetailResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    detail = get_requirement_controls_detail(session, tenant_id, requirement_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    return detail


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/regulatory-context",
    response_model=list[AISystemRegulatoryHintOut],
)
def cross_regulation_ai_system_regulatory_context(
    tenant_id: str,
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> list[AISystemRegulatoryHintOut]:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return list_ai_system_regulatory_hints(session, tenant_id, ai_system_id)


@app.post(
    "/api/v1/tenants/{tenant_id}/compliance/cross-regulation/llm-gap-assistant",
    response_model=CrossRegLlmGapAssistantResponse,
)
def cross_regulation_llm_gap_assistant(
    tenant_id: str,
    body: CrossRegLlmGapAssistantRequestBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _ff_cr: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
    _ff_gap: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.cross_regulation_llm_assist)),
    ],
) -> CrossRegLlmGapAssistantResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    payload = compute_cross_regulation_gaps(
        session,
        tenant_id,
        focus_framework_keys=body.focus_frameworks,
    )
    try:
        out = generate_cross_regulation_llm_gap_suggestions(
            payload,
            tenant_id,
            session=session,
            max_suggestions=body.max_suggestions,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    audit_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=None,
        entity_type="cross_regulation_llm_gap_assist",
        entity_id=tenant_id,
        action="completed",
        metadata={
            "suggestion_count": len(out.suggestions),
            "gap_count_used": out.gap_count_used,
            "focus_framework_keys": body.focus_frameworks or [],
        },
    )
    return out


@app.post(
    "/api/v1/tenants/{tenant_id}/board/ai-compliance-report",
    response_model=AiComplianceBoardReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_ai_compliance_board_report(
    tenant_id: str,
    body: AiComplianceBoardReportCreateBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report))],
) -> AiComplianceBoardReportCreateResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    try:
        out = create_ai_compliance_board_report(
            session,
            tenant_id,
            body,
            created_by=None,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm_client_mod.LLMProviderHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    audit_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=None,
        entity_type="ai_compliance_board_report",
        entity_id=out.report_id,
        action="generated",
        metadata={
            "audience_type": body.audience_type,
            "report_id": out.report_id,
        },
    )
    return out


@app.get(
    "/api/v1/tenants/{tenant_id}/board/ai-compliance-reports",
    response_model=list[AiComplianceBoardReportListItem],
)
def get_ai_compliance_board_reports_list(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report))],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AiComplianceBoardReportListItem]:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return list_ai_compliance_board_reports(session, tenant_id, limit=limit)


@app.get(
    "/api/v1/tenants/{tenant_id}/board/ai-compliance-reports/{report_id}",
    response_model=AiComplianceBoardReportDetailResponse,
)
def get_ai_compliance_board_report_by_id(
    tenant_id: str,
    report_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report))],
) -> AiComplianceBoardReportDetailResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    detail = get_ai_compliance_board_report_detail(session, tenant_id, report_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return detail


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/kpis",
    response_model=AiSystemKpisListResponse,
    tags=["ai-kpis"],
)
def get_tenant_ai_system_kpis(
    tenant_id: str,
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_kpi_kri))],
) -> AiSystemKpisListResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    ai_repo = AISystemRepository(session)
    if ai_repo.get_by_id(tenant_id, ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AISystem not found")
    return list_kpis_for_ai_system(session, tenant_id, ai_system_id)


@app.post(
    "/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/kpis",
    response_model=AiSystemKpiUpsertResponse,
    tags=["ai-kpis"],
)
def post_tenant_ai_system_kpi(
    tenant_id: str,
    ai_system_id: str,
    body: AiSystemKpiUpsertBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_kpi_kri))],
) -> AiSystemKpiUpsertResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    ai_repo = AISystemRepository(session)
    if ai_repo.get_by_id(tenant_id, ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AISystem not found")
    try:
        return upsert_kpi_value(
            session,
            tenant_id,
            ai_system_id,
            kpi_definition_id=body.kpi_definition_id,
            period_start=body.period_start,
            period_end=body.period_end,
            value=body.value,
            source=body.source,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-kpis/summary",
    response_model=AiKpiSummaryResponse,
    tags=["ai-kpis"],
)
def get_tenant_ai_kpis_summary(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_kpi_kri))],
    framework_key: Annotated[
        str | None,
        Query(description="Filter: eu_ai_act, iso_42001, …"),
    ] = None,
    criticality: Annotated[
        str | None,
        Query(description="Kommagetrennt, z. B. high,very_high"),
    ] = None,
) -> AiKpiSummaryResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    return build_ai_kpi_summary(
        session,
        tenant_id,
        framework_key=framework_key,
        criticality=criticality,
    )
