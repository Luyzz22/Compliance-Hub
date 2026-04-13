from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import uuid
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
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.advisor.metrics import AdvisorMetricsResponse, aggregate_advisor_metrics
from app.advisor.preset_models import (
    AiActRiskPresetInput,
    Iso42001GapCheckPresetInput,
    Nis2ObligationsPresetInput,
    PresetResult,
)
from app.advisor.presets import FlowType
from app.advisor_client_snapshot_models import (
    AdvisorClientGovernanceSnapshotResponse,
    AdvisorGovernanceSnapshotMarkdownResponse,
)
from app.advisor_models import AdvisorTenantReport
from app.advisor_portfolio_models import AdvisorPortfolioResponse
from app.agents.langgraph.oami_explain_poc import run_oami_explain_poc_async
from app.ai_act_doc_models import (
    AIActDoc,
    AIActDocListResponse,
    AIActDocSectionKey,
    AIActDocUpsertRequest,
)
from app.ai_act_evidence_models import (
    AdvisorAgentEvidenceStoredEvent,
    RagEvidenceStatsResponse,
    RagEvidenceStoredEvent,
    RagRetrieveRequest,
    RagRetrieveResponse,
)
from app.ai_compliance_board_report_models import (
    AdvisorBoardReportsPortfolioResponse,
    AiComplianceBoardReportCreateBody,
    AiComplianceBoardReportCreateResponse,
    AiComplianceBoardReportDetailResponse,
    AiComplianceBoardReportListItem,
    BoardReportWorkflowStartBody,
    BoardReportWorkflowStartResponse,
    BoardReportWorkflowStatusResponse,
)
from app.ai_governance_action_models import (
    AIGovernanceActionCreate,
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
    BoardOperationalMonitoringSection,
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
from app.ai_inventory_models import (
    AISystemInventoryProfileRead,
    AISystemInventoryProfileUpsert,
    AuthorityExportResponse,
    AuthorityExportScope,
    KIRegisterEntryRead,
    KIRegisterEntryUpsert,
    KIRegisterPostureSummary,
    WizardDecisionRequest,
    WizardDecisionResponse,
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
    get_optional_opa_user_role_header,
    require_path_tenant_matches_auth,
)
from app.authority_audit_preparation_pack_models import (
    AuthorityAuditPreparationPackResponse,
    PreparationPackFocus,
)
from app.classification_models import (
    ClassificationOverrideRequest,
    ClassificationQuestionnaire,
    ClassificationSummary,
    RiskClassification,
)
from app.compliance_calendar_models import (
    ComplianceDeadlineCreate,
    ComplianceDeadlineResponse,
    ComplianceDeadlineUpdate,
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
from app.db_migrations import run_all_db_migrations
from app.demo_models import (
    DemoGovernanceMaturityLayerRequest,
    DemoGovernanceMaturityLayerResponse,
    DemoSeedRequest,
    DemoSeedResponse,
    TenantWorkspaceMetaResponse,
)
from app.demo_templates import DemoTenantTemplate, get_demo_template, list_demo_tenant_templates
from app.demo_tenant_guard import (
    compute_workspace_mode_ui,
    raise_if_demo_tenant_readonly,
    tenant_mutation_blocked_meta,
    workspace_mode_for_telemetry,
)
from app.enterprise_connector_candidate_models import EnterpriseConnectorCandidatesResponse
from app.enterprise_connector_runtime_models import (
    ConnectorHealthSnapshot,
    ConnectorManualSyncResponse,
    ConnectorRetrySyncBody,
    ConnectorRuntimeStatusResponse,
    ConnectorSyncHistoryResponse,
    ConnectorSyncResult,
)
from app.enterprise_control_center_models import EnterpriseControlCenterResponse
from app.enterprise_integration_blueprint_models import (
    EnterpriseIntegrationBlueprintResponse,
    EnterpriseIntegrationBlueprintUpsert,
)
from app.enterprise_onboarding_models import (
    EnterpriseOnboardingReadinessResponse,
    EnterpriseOnboardingReadinessUpsert,
)
from app.eu_ai_act_readiness_models import EUAIActReadinessOverview
from app.eu_ai_act_wizard_models import WizardQuestionnaireRequest, WizardResult
from app.evidence.models import AiEvidenceEventDetail, AiEvidenceEventListResponse
from app.evidence.queries import (
    EvidenceQueryParams,
    export_csv_chunks,
    export_json_bytes,
    get_ai_event_detail,
    list_ai_events,
    list_ai_events_for_export,
)
from app.evidence_models import EvidenceFile, EvidenceFileListResponse
from app.feature_flags import (
    FeatureFlag,
    create_feature_guard,
    is_feature_enabled,
    require_tenant_llm_features,
)
from app.governance_maturity_models import GovernanceMaturityResponse
from app.governance_maturity_summary_models import GovernanceMaturityBoardSummaryParseResult
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.incident_drilldown_models import TenantIncidentDrilldownOut
from app.incident_models import AIIncidentBySystemEntry, AIIncidentOverview
from app.ki_register_models import (
    BoardAggregation,
    KIRegisterListResponse,
    KIRegisterUpdateRequest,
)
from app.llm.context import LlmCallContext
from app.llm_models import LLMTaskType
from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    DocumentType,
    EInvoiceFormat,
)
from app.models_db import Base, TenantApiKeyDB
from app.nis2_incident_models import (
    NIS2IncidentCreate,
    NIS2IncidentDeadlinesOverride,
    NIS2IncidentResponse,
    NIS2IncidentTransition,
)
from app.nis2_kritis_models import (
    Nis2KritisKpi,
    Nis2KritisKpiDrilldown,
    Nis2KritisKpiListResponse,
    Nis2KritisKpiSuggestionBody,
    Nis2KritisKpiSuggestionRequest,
    Nis2KritisKpiSuggestionResponse,
    Nis2KritisKpiUpsertRequest,
)
from app.operational_monitoring_models import (
    OamiExplanationOut,
    RuntimeEventsBatchIn,
    RuntimeEventsIngestResult,
    SystemMonitoringIndexOut,
    TenantOperationalMonitoringIndexOut,
)
from app.policy.opa_client import evaluate_action_policy
from app.policy.policy_guard import enforce_action_policy
from app.policy.role_resolution import (
    ENV_ROLE_ADVISOR_RAG,
    ENV_ROLE_ADVISOR_TENANT_REPORT,
    ENV_ROLE_AI_EVIDENCE,
    ENV_ROLE_BOARD_REPORT,
    ENV_ROLE_LANGGRAPH_OAMI_POC,
    ENV_ROLE_READINESS_EXPLAIN,
    resolve_opa_role_for_policy,
)
from app.policy.user_context import UserPolicyContext
from app.policy_models import Violation
from app.policy_service import evaluate_policies_for_ai_system
from app.product.models import Capability
from app.provisioning_models import (
    ProvisionTenantRequest,
    ProvisionTenantResponse,
    TenantApiKeyCreateBody,
    TenantApiKeyCreated,
    TenantApiKeyRead,
)
from app.rag.models import EuAiActNis2RagRequest, EuAiActNis2RagResponse
from app.rag.service import run_advisor_eu_reg_rag
from app.rbac.dependencies import require_permission
from app.rbac.permissions import Permission
from app.rbac.roles import EnterpriseRole
from app.readiness_score_models import ReadinessScoreExplainResponse, ReadinessScoreResponse
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_act_docs import AIActDocRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_inventory import AISystemInventoryRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_deadlines import ComplianceDeadlineRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.enterprise_connector_runtime import EnterpriseConnectorRuntimeRepository
from app.repositories.enterprise_integration_blueprints import (
    EnterpriseIntegrationBlueprintRepository,
)
from app.repositories.enterprise_onboarding import EnterpriseOnboardingRepository
from app.repositories.evidence_files import EvidenceFileRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_incidents import NIS2IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.tenant_ai_governance_setup import TenantAIGovernanceSetupRepository
from app.repositories.tenant_api_keys import TenantApiKeyRepository
from app.repositories.tenant_registry import TenantRegistryRepository
from app.repositories.violations import ViolationRepository
from app.security import (
    AuthContext,
    delete_evidence_allowed_for_api_key,
    ensure_demo_tenant_seed_allowed,
    require_admin_provision_api_key,
    require_advisor_api_access,
    require_advisor_rag_headers,
    require_demo_seed_api_key,
)
from app.services import llm_client as llm_client_mod
from app.services import usage_event_logger as usage_event_logger
from app.services import workspace_telemetry
from app.services.advisor_board_reports import (
    get_board_report_detail_for_advisor,
    list_advisor_portfolio_board_reports,
)
from app.services.advisor_client_governance_snapshot import (
    build_client_governance_snapshot,
    generate_advisor_governance_snapshot_markdown,
)
from app.services.advisor_portfolio import (
    advisor_portfolio_to_csv,
    advisor_portfolio_to_json_bytes,
    build_advisor_portfolio,
)
from app.services.advisor_report_llm_enrichment import (
    enrich_advisor_tenant_report_with_governance_maturity_brief,
    maybe_enrich_advisor_report_with_llm_summary,
)
from app.services.advisor_tenant_report import build_advisor_tenant_report
from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown
from app.services.ai_act_docs import build_ai_act_doc_list_response, upsert_ai_act_doc
from app.services.ai_act_docs_export import render_ai_act_documentation_markdown
from app.services.ai_board_alerts import compute_board_alerts
from app.services.ai_compliance_board_report import (
    create_ai_compliance_board_report,
    get_ai_compliance_board_report_detail,
    list_ai_compliance_board_reports,
)
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
from app.services.audit_gobd_export import generate_gobd_xml
from app.services.audit_trail_service import AuditTrailService, NIS2AlertService
from app.services.audit_trail_types import (
    AuditAlertItem,
    AuditLogPage,
    ChainIntegrityResult,
    VVTExport,
)
from app.services.authority_ai_export import build_authority_export
from app.services.authority_audit_preparation_pack import (
    build_authority_audit_preparation_pack,
)
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
from app.services.compliance_calendar_ical import generate_ical
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
from app.services.demo_governance_maturity_seed import seed_demo_governance_maturity_layer
from app.services.demo_tenant_seeder import seed_demo_tenant
from app.services.enterprise_connector_candidate_scoring import (
    build_connector_candidates_response,
)
from app.services.enterprise_connector_runtime import (
    build_connector_runtime_status,
    get_connector_health_snapshot,
    get_latest_connector_failure,
    list_connector_sync_history,
    retry_connector_sync,
    run_manual_connector_sync,
)
from app.services.enterprise_control_center import build_enterprise_control_center
from app.services.enterprise_integration_blueprint import (
    build_enterprise_integration_blueprint_response,
)
from app.services.eu_ai_act_readiness import compute_eu_ai_act_readiness_overview
from app.services.eu_ai_act_wizard_decision import evaluate_wizard_decision
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
from app.services.governance_audit import (
    actor_id_from_request,
    client_ip_from_request,
    correlation_id_from_request,
    record_governance_audit,
    user_agent_from_request,
)
from app.services.governance_maturity_board_summary_llm import (
    maybe_build_governance_maturity_board_summary_result,
)
from app.services.governance_maturity_service import build_governance_maturity_response
from app.services.high_risk_scenarios import list_high_risk_scenarios
from app.services.llm_router import LLMRouter
from app.services.nis2_kritis_ai_assist import generate_nis2_kpi_suggestions
from app.services.nis2_kritis_alert_signals import build_nis2_kritis_alert_signals
from app.services.nis2_kritis_drilldown import build_nis2_kritis_kpi_drilldown
from app.services.nis2_kritis_kpis import recommended_kpis_for_ai_system
from app.services.oami_explanation import explain_tenant_oami_de
from app.services.oami_incident_subtype_profile_board import (
    build_oami_incident_subtype_profile_for_board,
)
from app.services.operational_monitoring_index import (
    compute_system_monitoring_index,
    compute_tenant_operational_monitoring_index,
)
from app.services.rag.confidence import should_decline_answer
from app.services.rag.config import RAGConfig
from app.services.rag.corpus_loader import load_advisor_corpus
from app.services.rag.evidence_store import (
    aggregate_rag_hybrid_stats,
    list_advisor_agent_events,
    list_rag_events,
)
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.logging import log_rag_query_event
from app.services.readiness_score_explain import explain_readiness_score
from app.services.readiness_score_service import compute_readiness_score
from app.services.runtime_events_demo_guard import (
    ensure_runtime_events_api_ingest_allowed,
)
from app.services.runtime_events_ingest import ingest_runtime_events
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
from app.services.tenant_incident_drilldown import (
    compute_tenant_incident_drilldown,
    tenant_incident_drilldown_to_csv,
)
from app.services.tenant_provisioning import provision_tenant
from app.services.tenant_usage_metrics import compute_tenant_usage_metrics
from app.services.what_if_simulator import simulate_board_impact
from app.setup_models import TenantSetupStatus
from app.supplier_risk_models import (
    AISupplierRiskBySystemEntry,
    AISupplierRiskOverview,
)
from app.telemetry.middleware import TelemetryMiddleware
from app.telemetry.tracing import (
    configure_telemetry,
    get_trace_context_for_log_fields,
    inject_trace_carrier,
    start_span,
)
from app.temporal_client import get_temporal_client
from app.tenant_ai_governance_setup_models import (
    TenantAIGovernanceSetupPatch,
    TenantAIGovernanceSetupResponse,
)
from app.usage_metrics_models import TenantUsageMetricsResponse
from app.workflows.board_report import (
    BoardReportWorkflow,
    BoardReportWorkflowInput,
    BoardReportWorkflowResult,
)
from app.workflows.config import temporal_task_queue

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
    run_all_db_migrations(engine)
    configure_telemetry()
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
app.add_middleware(TelemetryMiddleware)

logger = logging.getLogger(__name__)


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


def get_nis2_incident_repository(
    session: Annotated[Session, Depends(get_session)],
) -> NIS2IncidentRepository:
    return NIS2IncidentRepository(session)


def get_classification_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ClassificationRepository:
    return ClassificationRepository(session)


def get_compliance_gap_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ComplianceGapRepository:
    return ComplianceGapRepository(session)


def get_compliance_deadline_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ComplianceDeadlineRepository:
    return ComplianceDeadlineRepository(session)


def get_nis2_kritis_kpi_repository(
    session: Annotated[Session, Depends(get_session)],
) -> Nis2KritisKpiRepository:
    return Nis2KritisKpiRepository(session)


def get_ai_governance_action_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AIGovernanceActionRepository:
    return AIGovernanceActionRepository(session)


def get_ai_inventory_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AISystemInventoryRepository:
    return AISystemInventoryRepository(session)


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


def get_enterprise_onboarding_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EnterpriseOnboardingRepository:
    return EnterpriseOnboardingRepository(session)


def get_enterprise_integration_blueprint_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EnterpriseIntegrationBlueprintRepository:
    return EnterpriseIntegrationBlueprintRepository(session)


def get_enterprise_connector_runtime_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EnterpriseConnectorRuntimeRepository:
    return EnterpriseConnectorRuntimeRepository(session)


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


def _langgraph_poc_enabled() -> bool:
    v = os.getenv("ENABLE_LANGGRAPH_POC", "").strip().lower()
    return v in ("1", "true", "yes", "on")


class OamiExplainPocRequestBody(BaseModel):
    """Request body for the LangGraph OAMI explain PoC (tenant-scoped)."""

    ai_system_id: str = Field(min_length=1, max_length=256)
    window_days: int = Field(default=90, ge=1, le=365)


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
def intake(
    payload: DocumentIntakeRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentIntakeResponse:
    raise_if_demo_tenant_readonly(session, payload.tenant_id, request=request)
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
    "/api/v1/ai-systems/{ai_system_id}/runtime-events",
    response_model=RuntimeEventsIngestResult,
    tags=["ai-systems"],
)
def post_ai_system_runtime_events(
    ai_system_id: str,
    body: RuntimeEventsBatchIn,
    request: Request,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> RuntimeEventsIngestResult:
    """Batch-Ingest kanonisierter Laufzeit-Events (SAP AI Core u. a.), mandantenisoliert."""
    tenant_id = auth_context.tenant_id
    raise_if_demo_tenant_readonly(session, tenant_id, request=request)
    ensure_runtime_events_api_ingest_allowed(session, tenant_id)
    if ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    return ingest_runtime_events(
        session,
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        events=body.events,
    )


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/monitoring-index",
    response_model=SystemMonitoringIndexOut,
    tags=["ai-systems"],
)
def get_ai_system_monitoring_index(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    window_days: Annotated[int, Query(ge=1, le=366)] = 90,
) -> SystemMonitoringIndexOut:
    """System-Level OAMI (0–100) mit erklärbaren Teilscores im Fenster window_days."""
    tenant_id = auth_context.tenant_id
    if ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    return compute_system_monitoring_index(
        session,
        tenant_id,
        ai_system_id,
        window_days=window_days,
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


@app.post("/api/v1/ai-act/wizard/decision", response_model=WizardDecisionResponse)
def post_ai_act_wizard_decision(
    body: WizardDecisionRequest,
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_AI_SYSTEMS))],
) -> WizardDecisionResponse:
    return evaluate_wizard_decision(body.ai_system_id, body.questionnaire)


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/inventory-profile",
    response_model=AISystemInventoryProfileRead | None,
)
def get_ai_system_inventory_profile(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_AI_SYSTEMS))],
) -> AISystemInventoryProfileRead | None:
    if ai_repo.get_by_id(auth_context.tenant_id, ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    return inv_repo.get_profile(auth_context.tenant_id, ai_system_id)


@app.put(
    "/api/v1/ai-systems/{ai_system_id}/inventory-profile",
    response_model=AISystemInventoryProfileRead,
)
def put_ai_system_inventory_profile(
    ai_system_id: str,
    body: AISystemInventoryProfileUpsert,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.EDIT_AI_SYSTEMS))],
) -> AISystemInventoryProfileRead:
    if ai_repo.get_by_id(auth_context.tenant_id, ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    profile = inv_repo.upsert_profile(
        auth_context.tenant_id,
        ai_system_id,
        body,
        actor=auth_context.api_key,
    )
    audit_repo.log_event(
        tenant_id=auth_context.tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ai_system_inventory",
        entity_id=ai_system_id,
        action="upserted",
        metadata={"register_status": profile.register_status},
    )
    return profile


@app.get("/api/v1/ki-register/entries", response_model=list[KIRegisterEntryRead])
def list_ki_register_entries(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_RISK_REGISTER))],
) -> list[KIRegisterEntryRead]:
    return inv_repo.list_latest_register_entries(auth_context.tenant_id)


@app.get("/api/v1/ki-register/posture", response_model=KIRegisterPostureSummary)
def get_ki_register_posture(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_RISK_REGISTER))],
) -> KIRegisterPostureSummary:
    total = len(ai_repo.list_for_tenant(auth_context.tenant_id))
    return inv_repo.posture_summary(auth_context.tenant_id, total)


@app.put("/api/v1/ki-register/entries/{ai_system_id}", response_model=KIRegisterEntryRead)
def put_ki_register_entry(
    ai_system_id: str,
    body: KIRegisterEntryUpsert,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _rbac: Annotated[EnterpriseRole, Depends(require_permission(Permission.EDIT_RISK_REGISTER))],
) -> KIRegisterEntryRead:
    if ai_repo.get_by_id(auth_context.tenant_id, ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    row = inv_repo.upsert_register_entry(
        auth_context.tenant_id,
        ai_system_id,
        body,
        auth_context.api_key,
    )
    audit_repo.log_event(
        tenant_id=auth_context.tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type="ki_register_entry",
        entity_id=ai_system_id,
        action="versioned_upsert",
        metadata={"version": row.version, "status": row.status},
    )
    return row


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
    "/api/v1/ai-act-evidence/rag-events",
    response_model=list[RagEvidenceStoredEvent],
    tags=["ai-act-evidence"],
)
def list_ai_act_rag_evidence(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RagEvidenceStoredEvent]:
    raw = list_rag_events(auth_context.tenant_id, limit=limit)
    return [RagEvidenceStoredEvent.model_validate(row) for row in raw]


@app.get(
    "/api/v1/ai-act-evidence/advisor-agent-events",
    response_model=list[AdvisorAgentEvidenceStoredEvent],
    tags=["ai-act-evidence"],
)
def list_ai_act_advisor_agent_evidence(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AdvisorAgentEvidenceStoredEvent]:
    raw = list_advisor_agent_events(auth_context.tenant_id, limit=limit)
    return [AdvisorAgentEvidenceStoredEvent.model_validate(row) for row in raw]


@app.get(
    "/api/v1/ai-act-evidence/rag-stats",
    response_model=RagEvidenceStatsResponse,
    tags=["ai-act-evidence"],
)
def get_ai_act_rag_evidence_stats(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    limit: int = Query(default=500, ge=1, le=2000),
) -> RagEvidenceStatsResponse:
    agg = aggregate_rag_hybrid_stats(auth_context.tenant_id, limit=limit)
    return RagEvidenceStatsResponse.model_validate(agg)


@app.post(
    "/api/v1/advisor/rag-retrieve",
    response_model=RagRetrieveResponse,
    tags=["advisor"],
)
def advisor_rag_retrieve(
    body: RagRetrieveRequest,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
) -> RagRetrieveResponse:
    """Retrieval-only advisor call (no LLM).

    Records metadata-only RAG evidence (SHA-256 of query).
    """
    corpus = load_advisor_corpus()
    cfg = RAGConfig(retrieval_mode=body.retrieval_mode)
    response = HybridRetriever(corpus, cfg).retrieve(body.query.strip(), k=body.k)
    top_bm25 = response.results[0].bm25_score if response.results else None
    top_dense = response.results[0].dense_score if response.results else None
    decline, decline_reason = should_decline_answer(
        response.confidence_level,
        tenant_expects_guidance=body.tenant_expects_guidance,
        has_tenant_guidance=response.has_tenant_guidance,
        has_results=bool(response.results),
        top_bm25=top_bm25,
        top_dense=top_dense,
        bm25_floor=cfg.bm25_floor,
        dense_threshold=cfg.dense_score_threshold,
    )
    top_ids = [hit.doc.doc_id for hit in response.results[:10]]
    hybrid_differs = False
    if response.results:
        bm25_top_id = max(response.results, key=lambda h: h.bm25_score).doc.doc_id
        hybrid_differs = response.results[0].doc.doc_id != bm25_top_id
    scores_summary: dict[str, float] = {}
    if response.results:
        top = response.results[0]
        scores_summary = {
            "top_combined": round(top.score, 4),
            "top_bm25": round(top.bm25_score, 4),
            "top_dense": round(top.dense_score, 4),
        }
    log_rag_query_event(
        response,
        tenant_id=auth_context.tenant_id,
        query_text=body.query,
        decline_reason=decline_reason if decline else None,
        trace_id=body.trace_id,
        persist_evidence=True,
    )
    top_primary = "bm25"
    if response.retrieval_mode == "hybrid" and hybrid_differs:
        top_primary = "dense_rescue"
    qsha = hashlib.sha256(body.query.encode()).hexdigest()
    return RagRetrieveResponse(
        query_sha256=qsha,
        retrieval_mode=response.retrieval_mode,
        top_doc_ids=top_ids,
        top_doc_primary_source=top_primary,
        hybrid_alpha=response.alpha_used if response.retrieval_mode == "hybrid" else None,
        hybrid_differs_from_bm25_top=hybrid_differs,
        confidence_level=response.confidence_level,
        confidence_score=response.confidence_score,
        decline_answer=decline,
        decline_reason=decline_reason if decline else None,
        tenant_guidance_matched=response.has_tenant_guidance,
        scores_summary=scores_summary,
        citations=[{"doc_id": hit.doc.doc_id} for hit in response.results[:5]],
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
            "ai_act_evidence",
            "advisor_rag_retrieve",
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
    request: Request,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIComplianceOverview:
    """Board-fähiger EU AI Act / ISO 42001 Readiness-Überblick."""
    tid = auth_context.tenant_id
    workspace_telemetry.log_workspace_feature_used(
        session,
        tid,
        workspace_mode=workspace_mode_for_telemetry(session, tid),
        feature_name="ai_governance_playbook",
        request_path=request.url.path,
        route=workspace_telemetry.route_template_from_request(request),
        method=request.method,
    )
    return compute_ai_compliance_overview(
        tenant_id=tid,
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
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> AIBoardGovernanceReport:
    """Vorstands-/Aufsichtsreport: alle AI-Governance-Kennzahlen gebündelt (nur JSON)."""
    return _build_board_report(
        session,
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
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> Response:
    """Board-Report als Markdown (template-fähig, für PDF/Word-Weiterverarbeitung)."""
    report = _build_board_report(
        session,
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
    session: Session,
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
    inv_repo = AISystemInventoryRepository(session)
    kpis = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
        inventory_repository=inv_repo,
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
    operational_monitoring: BoardOperationalMonitoringSection | None = None
    try:
        to = compute_tenant_operational_monitoring_index(
            session,
            tenant_id,
            window_days=90,
            persist_snapshot=False,
        )
        ex = explain_tenant_oami_de(to)
        subtype_prof = build_oami_incident_subtype_profile_for_board(to)
        operational_monitoring = BoardOperationalMonitoringSection(
            index_value=to.operational_monitoring_index,
            level=str(to.level),
            window_days=90,
            has_data=to.has_any_runtime_data,
            systems_scored=to.systems_scored,
            summary_de=ex.summary_de,
            drivers_de=list(ex.drivers_de)[:8],
            oami_incident_subtype_profile=subtype_prof,
        )
    except Exception:
        logger.exception("board_report_operational_monitoring_failed tenant_id=%s", tenant_id)

    return AIBoardGovernanceReport(
        tenant_id=tenant_id,
        generated_at=generated_at,
        period="last_12_months",
        kpis=kpis,
        compliance_overview=compliance_overview,
        incidents_overview=incidents_overview,
        supplier_risk_overview=supplier_risk_overview,
        alerts=alerts,
        operational_monitoring=operational_monitoring,
    )


@app.post(
    "/api/v1/ai-governance/report/board/export-jobs",
    response_model=BoardReportExportJob,
    status_code=status.HTTP_201_CREATED,
)
def create_board_report_export_job(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
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
        session,
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
    session: Annotated[Session, Depends(get_session)],
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
        session,
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


# ── NIS2 Incident Response Workflow endpoints ──────────────────────────────────


@app.post(
    "/api/v1/nis2-incidents",
    response_model=NIS2IncidentResponse,
    status_code=201,
)
def create_nis2_incident(
    body: NIS2IncidentCreate,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_INCIDENTS))],
    repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> NIS2IncidentResponse:
    """Create a new NIS2 Art. 21 compliant incident."""
    actor = actor_id_from_request(request)
    result = repo.create(tenant_id=tenant_id, data=body, created_by=actor)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.NIS2_INCIDENT_CREATE.value,
        entity_type=GovernanceAuditEntity.NIS2_INCIDENT.value,
        entity_id=result.id,
        outcome="success",
        before=None,
        after=json.dumps({"workflow_status": result.workflow_status.value}),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={
            "incident_type": body.incident_type.value,
            "severity": body.severity,
        },
    )
    return result


@app.get(
    "/api/v1/nis2-incidents",
    response_model=list[NIS2IncidentResponse],
)
def list_nis2_incidents(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_INCIDENTS))],
    repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
) -> list[NIS2IncidentResponse]:
    """List NIS2 incidents for the authenticated tenant."""
    return repo.list_for_tenant(tenant_id=tenant_id)


@app.get(
    "/api/v1/nis2-incidents/{incident_id}",
    response_model=NIS2IncidentResponse,
)
def get_nis2_incident(
    incident_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_INCIDENTS))],
    repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
) -> NIS2IncidentResponse:
    """Get a single NIS2 incident by ID (tenant-isolated)."""
    result = repo.get(tenant_id=tenant_id, incident_id=incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="NIS2 incident not found")
    return result


@app.post(
    "/api/v1/nis2-incidents/{incident_id}/transition",
    response_model=NIS2IncidentResponse,
)
def transition_nis2_incident(
    incident_id: str,
    body: NIS2IncidentTransition,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_INCIDENTS))],
    repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> NIS2IncidentResponse:
    """Transition a NIS2 incident to the next workflow state."""
    prev = repo.get(tenant_id=tenant_id, incident_id=incident_id)
    if prev is None:
        raise HTTPException(status_code=404, detail="NIS2 incident not found")
    try:
        result = repo.transition(
            tenant_id=tenant_id,
            incident_id=incident_id,
            transition=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.NIS2_INCIDENT_TRANSITION.value,
        entity_type=GovernanceAuditEntity.NIS2_INCIDENT.value,
        entity_id=incident_id,
        outcome="success",
        before=json.dumps({"workflow_status": prev.workflow_status.value}),
        after=json.dumps(
            {
                "workflow_status": result.workflow_status.value,
                "target_status": body.target_status.value,
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"notes_present": body.notes is not None},
    )
    return result


@app.patch(
    "/api/v1/nis2-incidents/{incident_id}/deadlines",
    response_model=NIS2IncidentResponse,
)
def patch_nis2_incident_deadlines(
    incident_id: str,
    body: NIS2IncidentDeadlinesOverride,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_INCIDENTS))],
    repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> NIS2IncidentResponse:
    """Override regulatory deadlines (audited; requires documented reason)."""
    prev = repo.get(tenant_id=tenant_id, incident_id=incident_id)
    if prev is None:
        raise HTTPException(status_code=404, detail="NIS2 incident not found")
    before = json.dumps(
        {
            "bsi_notification_deadline": prev.bsi_notification_deadline.isoformat()
            if prev.bsi_notification_deadline
            else None,
            "bsi_report_deadline": prev.bsi_report_deadline.isoformat()
            if prev.bsi_report_deadline
            else None,
            "final_report_deadline": prev.final_report_deadline.isoformat()
            if prev.final_report_deadline
            else None,
        }
    )
    try:
        result = repo.override_deadlines(
            tenant_id=tenant_id,
            incident_id=incident_id,
            body=body,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="NIS2 incident not found") from None
    after = json.dumps(
        {
            "bsi_notification_deadline": result.bsi_notification_deadline.isoformat()
            if result.bsi_notification_deadline
            else None,
            "bsi_report_deadline": result.bsi_report_deadline.isoformat()
            if result.bsi_report_deadline
            else None,
            "final_report_deadline": result.final_report_deadline.isoformat()
            if result.final_report_deadline
            else None,
        }
    )
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.NIS2_INCIDENT_DEADLINE_OVERRIDE.value,
        entity_type=GovernanceAuditEntity.NIS2_INCIDENT.value,
        entity_id=incident_id,
        outcome="success",
        before=before,
        after=after,
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"reason": body.reason},
    )
    return result


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
    "/api/internal/enterprise/onboarding-readiness",
    response_model=EnterpriseOnboardingReadinessResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_onboarding_readiness(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    repo: Annotated[EnterpriseOnboardingRepository, Depends(get_enterprise_onboarding_repository)],
) -> EnterpriseOnboardingReadinessResponse:
    row = repo.get(auth.tenant_id)
    if row is not None:
        return row
    # Default baseline when tenant has not configured onboarding readiness yet.
    baseline = EnterpriseOnboardingReadinessUpsert()
    return repo.upsert(auth.tenant_id, baseline, actor="api_client")


@app.put(
    "/api/internal/enterprise/onboarding-readiness",
    response_model=EnterpriseOnboardingReadinessResponse,
    tags=["internal", "enterprise"],
)
def put_enterprise_onboarding_readiness(
    body: EnterpriseOnboardingReadinessUpsert,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_ONBOARDING_READINESS)),
    ],
    repo: Annotated[EnterpriseOnboardingRepository, Depends(get_enterprise_onboarding_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> EnterpriseOnboardingReadinessResponse:
    actor = actor_id_from_request(request)
    saved = repo.upsert(auth.tenant_id, body, actor=actor)
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_ONBOARDING_READINESS_UPSERT.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_ONBOARDING_READINESS.value,
        entity_id=auth.tenant_id,
        outcome="success",
        before=None,
        after=json.dumps(
            {
                "provider": saved.sso_readiness.provider_type.value,
                "sso_status": saved.sso_readiness.onboarding_status.value,
                "integration_targets": len(saved.integration_readiness),
                "blockers": len(saved.blockers),
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"advisor_visibility_enabled": saved.advisor_visibility_enabled},
    )
    return saved


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
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
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
        incident_repo,
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
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
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
        incident_repo,
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
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/governance-snapshot",
    response_model=AdvisorClientGovernanceSnapshotResponse,
    tags=["advisors"],
)
def get_advisor_client_governance_snapshot(
    _ff_snap: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_client_snapshot))],
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
) -> AdvisorClientGovernanceSnapshotResponse:
    """Strukturierter Governance-Snapshot für einen verknüpften Mandanten."""
    snap = build_client_governance_snapshot(session, advisor_id, tenant_id, advisor_repo)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    return snap


@app.post(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/governance-snapshot-report",
    response_model=AdvisorGovernanceSnapshotMarkdownResponse,
    tags=["advisors"],
)
def post_advisor_client_governance_snapshot_report(
    _ff_snap: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_client_snapshot))],
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    request: Request,
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
) -> AdvisorGovernanceSnapshotMarkdownResponse:
    """KI-Markdown-Snapshot (nur aggregierte Kennzahlen, keine PII)."""
    snap = build_client_governance_snapshot(session, advisor_id, tenant_id, advisor_repo)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    raise_if_demo_tenant_readonly(session, tenant_id, request=request)
    try:
        return generate_advisor_governance_snapshot_markdown(session, tenant_id, snap)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM snapshot generation failed",
        ) from exc


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/readiness-score",
    response_model=ReadinessScoreResponse,
    tags=["advisors"],
)
def get_advisor_tenant_readiness_score(
    _ff_rs: Annotated[None, Depends(create_feature_guard(FeatureFlag.readiness_score))],
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
) -> ReadinessScoreResponse:
    """Readiness-Score für verknüpften Mandanten (entspricht dem Tenant-Endpunkt)."""
    if advisor_repo.get_link(advisor_id, tenant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    return compute_readiness_score(session, tenant_id)


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/governance-maturity",
    response_model=GovernanceMaturityResponse,
    tags=["advisors"],
)
def get_advisor_tenant_governance_maturity(
    _ff_gm: Annotated[None, Depends(create_feature_guard(FeatureFlag.governance_maturity))],
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    window_days: Annotated[int, Query(ge=30, le=90)] = 90,
) -> GovernanceMaturityResponse:
    if advisor_repo.get_link(advisor_id, tenant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    return build_governance_maturity_response(session, tenant_id, window_days=window_days)


@app.get(
    "/api/v1/advisors/{advisor_id}/tenants/{tenant_id}/incident-drilldown",
    response_model=None,
    tags=["advisors"],
)
def get_advisor_tenant_incident_drilldown(
    _ff_gm: Annotated[None, Depends(create_feature_guard(FeatureFlag.governance_maturity))],
    _ff_adv: Annotated[None, Depends(create_feature_guard(FeatureFlag.advisor_workspace))],
    advisor_id: Annotated[str, Depends(require_advisor_api_access)],
    tenant_id: str,
    session: Annotated[Session, Depends(get_session)],
    advisor_repo: Annotated[AdvisorTenantRepository, Depends(get_advisor_tenant_repository)],
    window_days: Annotated[int, Query(ge=1, le=366)] = 90,
    export_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> TenantIncidentDrilldownOut | Response:
    """
    Incident-Drilldown je KI-System und dominanter Laufzeit-Quelle (Berater, verknüpfter Mandant).
    CSV für interne Auswertung; keine Roh-Events, nur Aggregationen.
    """
    if advisor_repo.get_link(advisor_id, tenant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not linked to this advisor",
        )
    data = compute_tenant_incident_drilldown(session, tenant_id, window_days=window_days)
    if export_format == "csv":
        body = tenant_incident_drilldown_to_csv(data)
        fname = f"incident-drilldown-{tenant_id}.csv"
        return Response(
            content=body.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _evidence_content_disposition(fname)},
        )
    return data


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
    incident_repo: Annotated[IncidentRepository, Depends(get_incident_repository)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    export_format: Annotated[Literal["json", "markdown"], Query(alias="format")] = "json",
) -> AdvisorTenantReport | Response:
    """Mandanten-Steckbrief (JSON oder Markdown) nur bei Zuordnung in advisor_tenants."""
    advisor_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_ADVISOR_TENANT_REPORT,
        default="advisor",
    )
    enforce_action_policy(
        "advisor_tenant_report",
        UserPolicyContext(tenant_id=tenant_id, user_role=advisor_role),
        risk_score=0.55,
    )
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
        incident_repo=incident_repo,
    )
    report = enrich_advisor_tenant_report_with_governance_maturity_brief(session, tenant_id, report)
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


@app.post(
    "/api/v1/advisor/rag/eu-ai-act-nis2-query",
    response_model=EuAiActNis2RagResponse,
    tags=["advisors", "rag"],
)
def post_advisor_eu_ai_act_nis2_rag_query(
    body: EuAiActNis2RagRequest,
    session: Annotated[Session, Depends(get_session)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _ff_rag: Annotated[
        None,
        Depends(create_feature_guard(FeatureFlag.compliance_rag_knowledge_hub)),
    ],
    advisor_id: Annotated[str, Depends(require_advisor_rag_headers)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> EuAiActNis2RagResponse:
    """
    Berater: RAG über den kuratierten EU AI Act / NIS2 / ISO 42001 Pilot-Korpus
    (BM25 oder optional Hybrid mit Embeddings).
    """
    rag_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_ADVISOR_RAG,
        default="advisor",
    )
    enforce_action_policy(
        "advisor_rag_eu_ai_act_nis2_query",
        UserPolicyContext(tenant_id=body.tenant_id, user_role=rag_role),
        risk_score=0.55,
    )
    try:
        out = run_advisor_eu_reg_rag(
            question_de=body.question_de,
            tenant_id=body.tenant_id,
            user_role=rag_role,
            advisor_id=advisor_id,
            session=session,
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

    trace_fields = get_trace_context_for_log_fields()
    tg_count = sum(1 for c in out.citations if c.is_tenant_specific)
    audit_repo.log_event(
        tenant_id=body.tenant_id,
        actor_type="advisor",
        actor_id=advisor_id,
        entity_type="advisor_regulatory_rag",
        entity_id=body.tenant_id,
        action="query",
        metadata={
            "citation_count": len(out.citations),
            "query_sha256": hashlib.sha256(body.question_de.strip().encode("utf-8")).hexdigest(),
            "confidence_level": out.confidence_level,
            "tenant_guidance_citation_count": tg_count,
            "citation_doc_ids": [c.doc_id for c in out.citations[:20]],
            "trace_id": trace_fields.get("trace_id"),
            "span_id": trace_fields.get("span_id"),
            "opa_user_role": rag_role,
            "retrieval_mode": out.retrieval_mode or "bm25",
            "retrieval_hit_audit": [
                h.model_dump(mode="json") for h in (out.retrieval_hit_audit or [])[:20]
            ],
        },
    )
    return out


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
    request: Request,
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
    workspace_telemetry.log_workspace_feature_used(
        session,
        tenant_id,
        workspace_mode=workspace_mode_for_telemetry(session, tenant_id),
        feature_name="board_report_detail",
        request_path=request.url.path,
        route=workspace_telemetry.route_template_from_request(request),
        method=request.method,
        extra={"report_id": report_id},
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
    reg = TenantRegistryRepository(session)
    if reg.get_by_id(body.tenant_id) is None:
        tmpl = get_demo_template(body.template_key)
        reg.create(
            tenant_id=body.tenant_id,
            display_name=(tmpl.name if tmpl else body.tenant_id)[:255],
            industry=(tmpl.industry if tmpl else "Demo")[:128],
            country=(tmpl.country if tmpl else "DE")[:64],
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
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
        layer = seed_demo_governance_maturity_layer(session, body.tenant_id)
        usage_event_logger.log_usage_event(
            session,
            body.tenant_id,
            usage_event_logger.TENANT_SEEDED,
            {
                "template_key": body.template_key,
                "advisor_linked": result.advisor_linked,
                "demo_governance_telemetry_events_inserted": layer.telemetry_events_inserted,
                "demo_governance_runtime_events_inserted": layer.runtime_events_inserted,
            },
        )
        return result.model_copy(
            update={
                "demo_governance_telemetry_events_inserted": layer.telemetry_events_inserted,
                "demo_governance_runtime_events_inserted": layer.runtime_events_inserted,
                "demo_oami_snapshot_refreshed": layer.oami_snapshot_persisted,
            },
        )
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


@app.post(
    "/api/v1/demo/tenants/governance-maturity-layer",
    response_model=DemoGovernanceMaturityLayerResponse,
    tags=["demo"],
)
def post_demo_governance_maturity_layer(
    body: DemoGovernanceMaturityLayerRequest,
    _ff_demos: Annotated[None, Depends(create_feature_guard(FeatureFlag.demo_seeding))],
    session: Annotated[Session, Depends(get_session)],
    _api_key: Annotated[str, Depends(require_demo_seed_api_key)],
) -> DemoGovernanceMaturityLayerResponse:
    """
    Demo/Pilot: GAI-Telemetrie (usage_events), synthetische Runtime-Events (OAMI),
    Snapshot-Refresh. Für Mandanten mit Kern-Demo-Daten (z. B. nach 409 auf vollen Seed).
    """
    ensure_demo_tenant_seed_allowed(body.tenant_id)
    try:
        layer = seed_demo_governance_maturity_layer(session, body.tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DemoGovernanceMaturityLayerResponse(
        tenant_id=body.tenant_id.strip(),
        telemetry_events_inserted=layer.telemetry_events_inserted,
        runtime_events_inserted=layer.runtime_events_inserted,
        oami_snapshot_persisted=layer.oami_snapshot_persisted,
        skipped_already_seeded=layer.skipped_already_seeded,
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


@app.get("/api/v1/workspace/tenant-meta", response_model=TenantWorkspaceMetaResponse)
def get_workspace_tenant_meta(
    request: Request,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> TenantWorkspaceMetaResponse:
    row = TenantRegistryRepository(session).get_by_id(auth_context.tenant_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not registered",
        )
    tid = auth_context.tenant_id
    mut_blocked = tenant_mutation_blocked_meta(session, tid)
    wm, mode_label, mode_hint = compute_workspace_mode_ui(
        is_demo=bool(row.is_demo),
        demo_playground=bool(row.demo_playground),
        mutation_blocked=mut_blocked,
    )
    workspace_telemetry.log_workspace_session_started(
        session,
        tid,
        workspace_mode=workspace_mode_for_telemetry(session, tid),
        request_path=request.url.path,
        dedupe_same_type_hours=24,
    )
    ev_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_AI_EVIDENCE,
        default="tenant_admin",
    )
    ai_evidence_ff = is_feature_enabled(FeatureFlag.ai_act_evidence_views, tid, session=session)
    evidence_decision = evaluate_action_policy(
        {
            "tenant_id": tid,
            "user_role": ev_role,
            "action": "view_ai_evidence",
            "risk_score": 0.4,
        },
    )
    from app.product.offerings import sku_for_tier
    from app.product.plan_store import get_tenant_plan

    plan = get_tenant_plan(tid)
    sku = sku_for_tier(plan.tier)
    return TenantWorkspaceMetaResponse(
        tenant_id=row.id,
        display_name=row.display_name,
        is_demo=bool(row.is_demo),
        demo_playground=bool(row.demo_playground),
        mutation_blocked=mut_blocked,
        workspace_mode=wm,
        mode_label=mode_label,
        mode_hint=mode_hint,
        demo_mode_feature_enabled=is_feature_enabled(FeatureFlag.demo_mode),
        feature_ai_act_evidence_views=ai_evidence_ff,
        can_view_ai_evidence=bool(evidence_decision.allowed),
        plan_tier=plan.tier.value,
        plan_display=plan.plan_display(),
        plan_capabilities=sorted(c.value for c in plan.capabilities()),
        sku_name_de=sku.name_de if sku else "",
        sku_tagline_de=sku.tagline_de if sku else "",
    )


@app.get("/api/v1/workspace/feature-used", tags=["workspace"])
@app.get("/api/v1/workspace/demo-feature-used", tags=["workspace"])
def log_workspace_feature_used(
    request: Request,
    feature_key: Annotated[str, Query(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_system_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    framework_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    route_name: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> dict[str, bool]:
    """workspace_feature_used (keine PII). GET; alle registrierten Mandanten."""
    row = TenantRegistryRepository(session).get_by_id(auth_context.tenant_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not registered",
        )
    extra: dict[str, str] = {}
    if ai_system_id is not None:
        extra["ai_system_id"] = ai_system_id
    if framework_key is not None:
        extra["framework_key"] = framework_key
    if route_name is not None:
        extra["route_name"] = route_name
    workspace_telemetry.log_workspace_feature_used(
        session,
        auth_context.tenant_id,
        workspace_mode=workspace_mode_for_telemetry(session, auth_context.tenant_id),
        feature_name=feature_key,
        request_path=request.url.path,
        route=workspace_telemetry.route_template_from_request(request),
        method=request.method,
        extra=extra or None,
    )
    return {"ok": True}


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
    request: Request,
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.cross_regulation_dashboard))],
) -> CrossRegulationSummaryResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    workspace_telemetry.log_workspace_feature_used(
        session,
        tenant_id,
        workspace_mode=workspace_mode_for_telemetry(session, tenant_id),
        feature_name="cross_regulation_dashboard",
        request_path=request.url.path,
        route=workspace_telemetry.route_template_from_request(request),
        method=request.method,
    )
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
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> AiComplianceBoardReportCreateResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    board_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_BOARD_REPORT,
        default="tenant_admin",
    )
    enforce_action_policy(
        "generate_board_report",
        UserPolicyContext(tenant_id=tenant_id, user_role=board_role),
        risk_score=0.75,
    )
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


def _sanitize_tenant_id_for_temporal_workflow_id(tenant_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", tenant_id).strip("-")
    return s[:64] if s else "tenant"


@app.post(
    "/api/v1/tenants/{tenant_id}/board-report/workflows/start",
    response_model=BoardReportWorkflowStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_start_board_report_workflow(
    tenant_id: str,
    body: BoardReportWorkflowStartBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report))],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> BoardReportWorkflowStartResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    wf_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_BOARD_REPORT,
        default="tenant_admin",
    )
    enforce_action_policy(
        "start_board_report_workflow",
        UserPolicyContext(tenant_id=tenant_id, user_role=wf_role),
        risk_score=0.75,
    )
    safe = _sanitize_tenant_id_for_temporal_workflow_id(tenant_id)
    workflow_id = f"board-report-{safe}-{uuid.uuid4()}"
    client = await get_temporal_client()
    otel_carrier: dict[str, str] = {}
    inject_trace_carrier(otel_carrier)
    with start_span(
        "temporal.board_report.enqueue",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    ):
        handle = await client.start_workflow(
            BoardReportWorkflow.run,
            BoardReportWorkflowInput(
                tenant_id=tenant_id,
                snapshot_reference=body.snapshot_reference,
                audience_type=body.audience_type,
                primary_ai_system_id=body.primary_ai_system_id,
                focus_frameworks=list(body.focus_frameworks or []),
                include_ai_act_only=body.include_ai_act_only,
                language=body.language,
                user_role_for_opa=wf_role,
                otel_trace_carrier=otel_carrier,
            ),
            id=workflow_id,
            task_queue=temporal_task_queue(),
        )
        desc = await handle.describe()
    audit_repo.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=None,
        entity_type="temporal_board_report_workflow",
        entity_id=workflow_id,
        action="started",
        metadata={
            "task_queue": temporal_task_queue(),
            "opa_user_role": wf_role,
        },
    )
    return BoardReportWorkflowStartResponse(workflow_id=workflow_id, run_id=desc.run_id)


@app.get(
    "/api/v1/tenants/{tenant_id}/board-report/workflows/{workflow_id}",
    response_model=BoardReportWorkflowStatusResponse,
)
async def get_board_report_workflow_status(
    tenant_id: str,
    workflow_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_compliance_board_report))],
) -> BoardReportWorkflowStatusResponse:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    safe = _sanitize_tenant_id_for_temporal_workflow_id(tenant_id)
    prefix = f"board-report-{safe}-"
    if not workflow_id.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    status_name = desc.status.name
    report_id: str | None = None
    if status_name == "COMPLETED":
        try:
            result = await handle.result()
            if isinstance(result, BoardReportWorkflowResult):
                report_id = result.report_id
            elif isinstance(result, dict):
                rid = result.get("report_id")
                report_id = str(rid) if rid else None
        except Exception:
            logger.exception("board_report_workflow_result_read_failed id=%s", workflow_id)
    return BoardReportWorkflowStatusResponse(
        workflow_id=workflow_id,
        status=status_name,
        report_id=report_id,
    )


_AI_EVIDENCE_EVENT_TYPES = frozenset(
    {
        "rag_query",
        "board_report_workflow_started",
        "board_report_completed",
        "llm_contract_violation",
        "llm_guardrail_block",
    },
)


def _parse_ai_evidence_event_types(raw: str | None) -> frozenset[str] | None:
    if raw is None or not str(raw).strip():
        return None
    parts = frozenset(p.strip() for p in raw.split(",") if p.strip())
    if not parts:
        return None
    unknown = parts - _AI_EVIDENCE_EVENT_TYPES
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown event_types: {', '.join(sorted(unknown))}",
        )
    return parts


@app.get(
    "/api/v1/evidence/ai-act/events",
    response_model=AiEvidenceEventListResponse,
    tags=["evidence", "ai-act"],
)
def get_ai_act_evidence_events(
    tenant_id: Annotated[str, Query(min_length=1)],
    session: Annotated[Session, Depends(get_session)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_act_evidence_views))],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    from_ts: Annotated[datetime | None, Query()] = None,
    to_ts: Annotated[datetime | None, Query()] = None,
    event_types: Annotated[str | None, Query()] = None,
    confidence_level: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AiEvidenceEventListResponse:
    """
    Read-only AI Act evidence index (metadata only; keine Prompts/Antworten).
    """
    require_path_tenant_matches_auth(tenant_id, auth_context)
    ev_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_AI_EVIDENCE,
        default="tenant_admin",
    )
    enforce_action_policy(
        "view_ai_evidence",
        UserPolicyContext(tenant_id=tenant_id, user_role=ev_role),
        risk_score=0.4,
    )
    et = _parse_ai_evidence_event_types(event_types)
    params = EvidenceQueryParams(
        tenant_id=tenant_id,
        from_ts=from_ts,
        to_ts=to_ts,
        event_types=et,
        confidence_level=confidence_level.lower() if confidence_level else None,
        limit=limit,
        offset=offset,
    )
    return list_ai_events(session, params)


@app.get(
    "/api/v1/evidence/ai-act/events/{event_id}",
    response_model=AiEvidenceEventDetail,
    tags=["evidence", "ai-act"],
)
def get_ai_act_evidence_event_detail(
    event_id: str,
    tenant_id: Annotated[str, Query(min_length=1)],
    session: Annotated[Session, Depends(get_session)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_act_evidence_views))],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> AiEvidenceEventDetail:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    ev_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_AI_EVIDENCE,
        default="tenant_admin",
    )
    enforce_action_policy(
        "view_ai_evidence",
        UserPolicyContext(tenant_id=tenant_id, user_role=ev_role),
        risk_score=0.4,
    )
    detail = get_ai_event_detail(session, tenant_id, event_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return detail


@app.get(
    "/api/v1/evidence/ai-act/export",
    tags=["evidence", "ai-act"],
)
def export_ai_act_evidence(
    tenant_id: Annotated[str, Query(min_length=1)],
    session: Annotated[Session, Depends(get_session)],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    _ff: Annotated[None, Depends(create_feature_guard(FeatureFlag.ai_act_evidence_views))],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    export_format: Annotated[Literal["csv", "json"], Query(alias="format")] = "csv",
    from_ts: Annotated[datetime | None, Query()] = None,
    to_ts: Annotated[datetime | None, Query()] = None,
    event_types: Annotated[str | None, Query()] = None,
    confidence_level: Annotated[str | None, Query()] = None,
) -> Response:
    require_path_tenant_matches_auth(tenant_id, auth_context)
    ev_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_AI_EVIDENCE,
        default="tenant_admin",
    )
    enforce_action_policy(
        "view_ai_evidence",
        UserPolicyContext(tenant_id=tenant_id, user_role=ev_role),
        risk_score=0.4,
    )
    et = _parse_ai_evidence_event_types(event_types)
    params = EvidenceQueryParams(
        tenant_id=tenant_id,
        from_ts=from_ts,
        to_ts=to_ts,
        event_types=et,
        confidence_level=confidence_level.lower() if confidence_level else None,
        limit=10_000,
        offset=0,
    )
    rows = list_ai_events_for_export(session, params)
    if export_format == "json":
        return Response(
            content=export_json_bytes(rows),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="ai_act_evidence.json"',
            },
        )
    return StreamingResponse(
        export_csv_chunks(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="ai_act_evidence.csv"',
        },
    )


@app.get("/api/v1/authority/ai-act/export", response_model=AuthorityExportResponse)
def export_authority_ai_act(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    audit_log_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    scope: Annotated[AuthorityExportScope, Query()] = AuthorityExportScope.initial,
    _rbac: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.EXPORT_AUDIT_LOG)),
    ] = EnterpriseRole.AUDITOR,
) -> AuthorityExportResponse:
    result = build_authority_export(
        tenant_id=auth_context.tenant_id,
        scope=scope,
        ai_repo=ai_repo,
        inventory_repo=inv_repo,
    )
    audit_repo.log_event(
        tenant_id=auth_context.tenant_id,
        actor_type="api_key",
        actor_id=auth_context.api_key,
        entity_type=GovernanceAuditEntity.AUTHORITY_EXPORT.value,
        entity_id=scope.value,
        action=GovernanceAuditAction.AUTHORITY_EXPORT_GENERATED.value,
        metadata={"systems": len(result.export.systems)},
    )
    audit_log_repo.record_event(
        tenant_id=auth_context.tenant_id,
        actor=auth_context.api_key,
        action=GovernanceAuditAction.AUTHORITY_EXPORT_API_ACTION.value,
        entity_type="AuthorityExport",
        entity_id=scope.value,
        before=None,
        after=_model_to_json(result),
    )
    return result


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
    request: Request,
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
    workspace_telemetry.log_workspace_feature_used(
        session,
        tenant_id,
        workspace_mode=workspace_mode_for_telemetry(session, tenant_id),
        feature_name="board_report_detail",
        request_path=request.url.path,
        route=workspace_telemetry.route_template_from_request(request),
        method=request.method,
        extra={"report_id": report_id},
    )
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


@app.post(
    "/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/runtime-events",
    response_model=RuntimeEventsIngestResult,
    tags=["ai-systems"],
)
def post_tenant_ai_system_runtime_events(
    tenant_id: str,
    ai_system_id: str,
    body: RuntimeEventsBatchIn,
    request: Request,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> RuntimeEventsIngestResult:
    """Alias zu POST /api/v1/ai-systems/{id}/runtime-events (expliziter Mandant im Pfad)."""
    require_path_tenant_matches_auth(tenant_id, auth_context)
    raise_if_demo_tenant_readonly(session, tenant_id, request=request)
    ensure_runtime_events_api_ingest_allowed(session, tenant_id)
    if ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    return ingest_runtime_events(
        session,
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        events=body.events,
    )


@app.get(
    "/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/monitoring-index",
    response_model=SystemMonitoringIndexOut,
    tags=["ai-systems"],
)
def get_tenant_ai_system_monitoring_index(
    tenant_id: str,
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    window_days: Annotated[int, Query(ge=1, le=366)] = 90,
) -> SystemMonitoringIndexOut:
    """Alias zu GET /api/v1/ai-systems/{id}/monitoring-index (expliziter Mandant im Pfad)."""
    require_path_tenant_matches_auth(tenant_id, auth_context)
    if ai_repo.get_by_id(tenant_id=tenant_id, aisystem_id=ai_system_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI system not found")
    return compute_system_monitoring_index(
        session,
        tenant_id,
        ai_system_id,
        window_days=window_days,
    )


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


@app.get(
    "/api/v1/tenants/{tenant_id}/readiness-score",
    response_model=ReadinessScoreResponse,
    tags=["tenants"],
)
def get_tenant_readiness_score(
    tenant_id: str,
    _ff_rs: Annotated[None, Depends(create_feature_guard(FeatureFlag.readiness_score))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> ReadinessScoreResponse:
    """AI & Compliance Readiness Score (0–100) aus Setup, Coverage, KPIs, Gaps, Reports."""
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return compute_readiness_score(session, tenant_id)


@app.get(
    "/api/v1/tenants/{tenant_id}/operational-monitoring-index",
    response_model=TenantOperationalMonitoringIndexOut,
    tags=["tenants"],
)
def get_tenant_operational_monitoring_index(
    tenant_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    window_days: Annotated[int, Query(ge=1, le=366)] = 90,
) -> TenantOperationalMonitoringIndexOut:
    """Tenant-Level OAMI: risikogewichteter Mittelwert über Systeme mit Laufzeitdaten im Fenster."""
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return compute_tenant_operational_monitoring_index(
        session,
        tenant_id,
        window_days=window_days,
        persist_snapshot=False,
    )


@app.get(
    "/api/v1/tenants/{tenant_id}/incident-drilldown",
    response_model=None,
    tags=["tenants"],
)
def get_tenant_incident_drilldown(
    tenant_id: str,
    _ff_gm: Annotated[None, Depends(create_feature_guard(FeatureFlag.governance_maturity))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    window_days: Annotated[int, Query(ge=1, le=366)] = 90,
    export_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> TenantIncidentDrilldownOut | Response:
    """
    Incident-Drilldown (Mandant, API-Key muss zu tenant_id passen). CSV optional.
    Nicht für anonyme Self-Service-Endnutzer gedacht.
    """
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    data = compute_tenant_incident_drilldown(session, tenant_id, window_days=window_days)
    if export_format == "csv":
        body = tenant_incident_drilldown_to_csv(data)
        fname = f"incident-drilldown-{tenant_id}.csv"
        return Response(
            content=body.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": _evidence_content_disposition(fname)},
        )
    return data


@app.get(
    "/api/v1/tenants/{tenant_id}/governance-maturity",
    response_model=GovernanceMaturityResponse,
    tags=["tenants"],
)
def get_tenant_governance_maturity(
    tenant_id: str,
    _ff_gm: Annotated[None, Depends(create_feature_guard(FeatureFlag.governance_maturity))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    window_days: Annotated[int, Query(ge=30, le=90)] = 90,
) -> GovernanceMaturityResponse:
    """Governance Maturity Lens: Readiness, GAI (Telemetrie), OAMI (Laufzeit)."""
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return build_governance_maturity_response(session, tenant_id, window_days=window_days)


@app.post(
    "/api/v1/tenants/{tenant_id}/governance-maturity/board-summary",
    response_model=GovernanceMaturityBoardSummaryParseResult,
    tags=["tenants"],
)
def post_tenant_governance_maturity_board_summary(
    tenant_id: str,
    _ff_gm: Annotated[None, Depends(create_feature_guard(FeatureFlag.governance_maturity))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> GovernanceMaturityBoardSummaryParseResult:
    """
    Strukturierte Governance-Reife-Zusammenfassung für Board/Executive (Readiness, GAI, OAMI).

    Nutzt LLM wenn aktiviert (gleicher Task wie Board-Report); sonst deterministische Fallbacks.
    """
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    result = maybe_build_governance_maturity_board_summary_result(session, tenant_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Governance maturity board summary unavailable",
        )
    return result


@app.post(
    "/api/v1/tenants/{tenant_id}/readiness-score/explain",
    response_model=ReadinessScoreExplainResponse,
    tags=["tenants"],
)
def post_tenant_readiness_score_explain(
    tenant_id: str,
    _ff_rs: Annotated[None, Depends(create_feature_guard(FeatureFlag.readiness_score))],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> ReadinessScoreExplainResponse:
    """KI-Erklärung zum Readiness Score (aggregierte Kennzahlen, LLM_EXPLAIN + LLM_ENABLED)."""
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    readiness_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_READINESS_EXPLAIN,
        default="tenant_user",
    )
    enforce_action_policy(
        "call_llm_explain_readiness",
        UserPolicyContext(tenant_id=tenant_id, user_role=readiness_role),
        risk_score=0.45,
    )
    snapshot = compute_readiness_score(session, tenant_id)
    llm_ctx = LlmCallContext(
        tenant_id=tenant_id,
        user_role=readiness_role,
        action_name="call_llm_explain_readiness",
    )
    try:
        return explain_readiness_score(
            session,
            tenant_id,
            snapshot,
            llm_call_context=llm_ctx,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Readiness score explanation failed",
        ) from exc


@app.post(
    "/api/v1/oami-explain-langgraph-poc",
    response_model=OamiExplanationOut,
    tags=["agents"],
)
async def post_oami_explain_langgraph_poc(
    body: OamiExplainPocRequestBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> OamiExplanationOut:
    """
    LangGraph PoC (tenant aus ``x-tenant-id``): OAMI-Erklärung, OPA + Guardrails.

    Gleicher Vertrag wie der mandantenspezifische Pfad unter ``/tenants/{id}/agents/...``.
    """
    if not _langgraph_poc_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    tenant_id = auth_context.tenant_id
    poc_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_LANGGRAPH_OAMI_POC,
        default="tenant_admin",
    )
    enforce_action_policy(
        "call_langgraph_oami_explain",
        UserPolicyContext(tenant_id=tenant_id, user_role=poc_role),
        risk_score=0.4,
    )
    try:
        return await run_oami_explain_poc_async(
            session,
            tenant_id=tenant_id,
            ai_system_id=body.ai_system_id,
            window_days=body.window_days,
            user_role=poc_role,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAMI explain PoC workflow failed",
        ) from exc


@app.post(
    "/api/v1/tenants/{tenant_id}/agents/oami-explain-poc",
    response_model=OamiExplanationOut,
    tags=["agents"],
)
async def post_tenant_oami_explain_langgraph_poc(
    tenant_id: str,
    body: OamiExplainPocRequestBody,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> OamiExplanationOut:
    """
    LangGraph PoC: OAMI-Kurzerklärung (gleiches JSON-Contract wie deterministische OAMI-Explain).

    Hinter `ENABLE_LANGGRAPH_POC`; außerhalb OPA-Policy `call_langgraph_oami_explain`.
    """
    if not _langgraph_poc_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    require_path_tenant_matches_auth(tenant_id, auth_context)
    poc_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name=ENV_ROLE_LANGGRAPH_OAMI_POC,
        default="tenant_admin",
    )
    enforce_action_policy(
        "call_langgraph_oami_explain",
        UserPolicyContext(tenant_id=tenant_id, user_role=poc_role),
        risk_score=0.4,
    )
    try:
        return await run_oami_explain_poc_async(
            session,
            tenant_id=tenant_id,
            ai_system_id=body.ai_system_id,
            window_days=body.window_days,
            user_role=poc_role,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OAMI explain PoC workflow failed",
        ) from exc


# ── Compliance Calendar + Deadline Management ──────────────────────────────────


@app.post(
    "/api/v1/compliance-calendar/deadlines",
    response_model=ComplianceDeadlineResponse,
    status_code=201,
)
def create_compliance_deadline(
    body: ComplianceDeadlineCreate,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_COMPLIANCE_CALENDAR))
    ],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> ComplianceDeadlineResponse:
    """Create a new regulatory compliance deadline."""
    result = repo.create(tenant_id=tenant_id, data=body)
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.COMPLIANCE_DEADLINE_CREATE.value,
        entity_type=GovernanceAuditEntity.COMPLIANCE_DEADLINE.value,
        entity_id=result.id,
        outcome="success",
        before=None,
        after=json.dumps(
            {
                "title": result.title,
                "due_date": str(result.due_date),
                "category": result.category.value,
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata=None,
    )
    return result


@app.get(
    "/api/v1/compliance-calendar/deadlines",
    response_model=list[ComplianceDeadlineResponse],
)
def list_compliance_deadlines(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_COMPLIANCE_CALENDAR))],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
) -> list[ComplianceDeadlineResponse]:
    """List compliance deadlines for the authenticated tenant."""
    return repo.list_for_tenant(tenant_id=tenant_id)


@app.get(
    "/api/v1/compliance-calendar/deadlines/upcoming",
    response_model=list[ComplianceDeadlineResponse],
)
def list_upcoming_compliance_deadlines(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_COMPLIANCE_CALENDAR))],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    days: int = 90,
) -> list[ComplianceDeadlineResponse]:
    """List upcoming compliance deadlines within a specified number of days."""
    return repo.list_upcoming(tenant_id=tenant_id, days=days)


@app.get(
    "/api/v1/compliance-calendar/deadlines/{deadline_id}",
    response_model=ComplianceDeadlineResponse,
)
def get_compliance_deadline(
    deadline_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_COMPLIANCE_CALENDAR))],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
) -> ComplianceDeadlineResponse:
    """Get a single compliance deadline by ID (tenant-isolated)."""
    result = repo.get(tenant_id=tenant_id, deadline_id=deadline_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Compliance deadline not found")
    return result


@app.patch(
    "/api/v1/compliance-calendar/deadlines/{deadline_id}",
    response_model=ComplianceDeadlineResponse,
)
def update_compliance_deadline(
    deadline_id: str,
    body: ComplianceDeadlineUpdate,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_COMPLIANCE_CALENDAR))
    ],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> ComplianceDeadlineResponse:
    """Partially update a compliance deadline."""
    if repo.is_system_deadline(deadline_id):
        raise HTTPException(status_code=403, detail="System deadlines cannot be modified")
    prev = repo.get(tenant_id=tenant_id, deadline_id=deadline_id)
    if prev is None:
        raise HTTPException(status_code=404, detail="Compliance deadline not found")
    before = json.dumps(
        {
            "title": prev.title,
            "due_date": str(prev.due_date),
            "category": prev.category.value,
        }
    )
    result = repo.update(tenant_id=tenant_id, deadline_id=deadline_id, data=body)
    if result is None:
        raise HTTPException(status_code=404, detail="Compliance deadline not found")
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.COMPLIANCE_DEADLINE_UPDATE.value,
        entity_type=GovernanceAuditEntity.COMPLIANCE_DEADLINE.value,
        entity_id=deadline_id,
        outcome="success",
        before=before,
        after=json.dumps(
            {
                "title": result.title,
                "due_date": str(result.due_date),
                "category": result.category.value,
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"patch_fields": list(body.model_dump(exclude_unset=True).keys())},
    )
    return result


@app.delete(
    "/api/v1/compliance-calendar/deadlines/{deadline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_compliance_deadline(
    deadline_id: str,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_COMPLIANCE_CALENDAR))
    ],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> Response:
    """Delete a compliance deadline."""
    if repo.is_system_deadline(deadline_id):
        raise HTTPException(status_code=403, detail="System deadlines cannot be deleted")
    prev = repo.get(tenant_id=tenant_id, deadline_id=deadline_id)
    if prev is None:
        raise HTTPException(status_code=404, detail="Compliance deadline not found")
    deleted = repo.delete(tenant_id=tenant_id, deadline_id=deadline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Compliance deadline not found")
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.COMPLIANCE_DEADLINE_DELETE.value,
        entity_type=GovernanceAuditEntity.COMPLIANCE_DEADLINE.value,
        entity_id=deadline_id,
        outcome="success",
        before=json.dumps(
            {"title": prev.title, "due_date": str(prev.due_date), "category": prev.category.value}
        ),
        after=None,
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata=None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/v1/compliance-calendar/seed-defaults",
    response_model=list[ComplianceDeadlineResponse],
)
def seed_compliance_defaults(
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_COMPLIANCE_CALENDAR))
    ],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[ComplianceDeadlineResponse]:
    """Pre-populate DACH-region regulatory deadlines for a tenant."""
    result = repo.seed_dach_defaults(tenant_id=tenant_id)
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.COMPLIANCE_CALENDAR_SEED_DEFAULTS.value,
        entity_type=GovernanceAuditEntity.COMPLIANCE_CALENDAR.value,
        entity_id=tenant_id,
        outcome="success",
        before=None,
        after=json.dumps({"deadline_count": len(result)}),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata=None,
    )
    return result


@app.get("/api/v1/compliance-calendar/export/ical")
def export_compliance_calendar_ical(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_COMPLIANCE_CALENDAR))],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
) -> Response:
    """Export all compliance deadlines as an iCal (.ics) calendar file."""
    deadlines = repo.list_for_tenant(tenant_id=tenant_id)
    ical_content = generate_ical(deadlines=deadlines, tenant_id=tenant_id)
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=compliance-calendar.ics"},
    )


@app.post(
    "/api/v1/compliance-calendar/seed-system-deadlines",
    response_model=list[ComplianceDeadlineResponse],
)
def seed_system_deadlines(
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_COMPLIANCE_CALENDAR))
    ],
    repo: Annotated[ComplianceDeadlineRepository, Depends(get_compliance_deadline_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[ComplianceDeadlineResponse]:
    """Idempotent: create global system deadlines (DACH region, visible to all tenants)."""
    result = repo.seed_system_deadlines()
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.COMPLIANCE_CALENDAR_SEED_DEFAULTS.value,
        entity_type=GovernanceAuditEntity.COMPLIANCE_CALENDAR.value,
        entity_id="system",
        outcome="success",
        before=None,
        after=json.dumps({"system_deadline_count": len(result)}),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"seed_type": "system_deadlines"},
    )
    return result


@app.get("/api/v1/audit-logs", response_model=list[AuditLog])
def list_audit_logs(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_AUDIT_LOG))],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[AuditLog]:
    return audit_repo.list_for_tenant(tenant_id=tenant_id)


@app.get("/api/v1/audit-logs/export/gobd-xml")
def export_audit_logs_gobd_xml(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> Response:
    """GoBD §14 compliant XML export of the audit trail."""
    entries = audit_repo.list_for_tenant(tenant_id=tenant_id, limit=10_000)
    xml = generate_gobd_xml(entries)
    return Response(
        content=xml,
        media_type="application/xml; charset=utf-8",
        headers={
            "Content-Disposition": (f'attachment; filename="audit-trail-{tenant_id}.xml"'),
        },
    )


# --- Phase 10 audit trail endpoints ---


@app.get("/api/v1/audit-logs/filtered", response_model=AuditLogPage)
def list_audit_logs_filtered(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
    page: int = 1,
    page_size: int = 50,
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> AuditLogPage:
    svc = AuditTrailService(session)
    return svc.list_filtered(
        tenant_id,
        page=page,
        page_size=page_size,
        actor=actor,
        action=action,
        resource_type=resource_type,
        from_date=from_date,
        to_date=to_date,
    )


@app.get("/api/v1/audit-logs/integrity")
def check_audit_log_integrity(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
) -> ChainIntegrityResult:
    svc = AuditTrailService(session)
    return svc.verify_integrity(tenant_id)


@app.get("/api/v1/audit-logs/export/csv")
def export_audit_logs_csv(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    svc = AuditTrailService(session)
    csv_content = svc.export_csv(tenant_id)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit-trail-{tenant_id}.csv"',
        },
    )


@app.get("/api/v1/audit-logs/export/json")
def export_audit_logs_json(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    svc = AuditTrailService(session)
    json_content = svc.export_json(tenant_id)
    return Response(
        content=json_content,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit-trail-{tenant_id}.json"',
        },
    )


@app.get("/api/v1/audit-logs/vvt-export", response_model=VVTExport)
def export_vvt(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
) -> VVTExport:
    """DSGVO Art. 30 Verarbeitungsverzeichnis export."""
    svc = AuditTrailService(session)
    return svc.generate_vvt_export(tenant_id)


@app.get("/api/v1/audit-alerts", response_model=list[AuditAlertItem])
def list_audit_alerts(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
    severity: str | None = None,
) -> list[AuditAlertItem]:
    svc = NIS2AlertService(session)
    return svc.list_alerts(tenant_id, severity=severity)


@app.post("/api/v1/audit-alerts/{alert_id}/resolve", response_model=AuditAlertItem)
def resolve_audit_alert(
    alert_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: Annotated[Session, Depends(get_session)],
) -> AuditAlertItem:
    svc = NIS2AlertService(session)
    result = svc.resolve_alert(tenant_id, alert_id, resolved_by="admin")
    if result is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


@app.get("/api/v1/audit-events", response_model=list[AuditEvent], tags=["audit"])
def list_audit_events(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> list[AuditEvent]:
    return audit_repo.list_events_for_tenant(auth.tenant_id)


@app.get(
    "/api/v1/audit-events/ai-systems/{ai_system_id}",
    response_model=list[AuditEvent],
    tags=["audit"],
)
def list_audit_events_for_ai_system(
    ai_system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> list[AuditEvent]:
    return audit_repo.list_events_for_entity(
        auth.tenant_id,
        entity_type="ai_system",
        entity_id=ai_system_id,
    )


# ---------------------------------------------------------------------------


# AI Act Documentation
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs",
    response_model=AIActDocListResponse,
    tags=["ai-act-docs"],
)
def get_ai_act_docs(
    ai_system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
) -> AIActDocListResponse:
    _ensure_feature_ai_act_docs(auth.tenant_id, session)
    _require_high_risk_system(auth.tenant_id, ai_repo, ai_system_id)
    return build_ai_act_doc_list_response(ai_system_id, doc_repo, auth.tenant_id)


@app.get(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs/export",
    tags=["ai-act-docs"],
)
def export_ai_act_docs(
    ai_system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
    evidence_repo: Annotated[EvidenceFileRepository, Depends(get_evidence_file_repository)],
) -> Response:
    _ensure_feature_ai_act_docs(auth.tenant_id, session)
    system = _require_high_risk_system(auth.tenant_id, ai_repo, ai_system_id)
    classification = cls_repo.get_for_system(auth.tenant_id, ai_system_id)
    nis2_kpis = nis2_repo.list_for_ai_system(auth.tenant_id, ai_system_id)
    actions = action_repo.list_for_tenant(auth.tenant_id)
    evidence_count = len(evidence_repo.list_for_tenant(auth.tenant_id))
    md = render_ai_act_documentation_markdown(
        system=system,
        classification=classification,
        nis2_kpis=nis2_kpis,
        actions=actions,
        evidence_count=evidence_count,
        docs_repo=doc_repo,
        tenant_id=auth.tenant_id,
    )
    return Response(content=md, media_type="text/markdown")


@app.post(
    "/api/v1/ai-systems/{ai_system_id}/ai-act-docs/{section_key}",
    response_model=AIActDoc,
    tags=["ai-act-docs"],
)
def upsert_ai_act_doc_section(
    ai_system_id: str,
    section_key: AIActDocSectionKey,
    body: AIActDocUpsertRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    doc_repo: Annotated[AIActDocRepository, Depends(get_ai_act_doc_repository)],
) -> AIActDoc:
    _ensure_feature_ai_act_docs(auth.tenant_id, session)
    _require_high_risk_system(auth.tenant_id, ai_repo, ai_system_id)
    return upsert_ai_act_doc(
        doc_repo,
        auth.tenant_id,
        ai_system_id,
        section_key,
        body,
        actor="api",
    )


# ---------------------------------------------------------------------------
# NIS2 KRITIS KPI Drilldown
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/nis2-kritis/kpi-drilldown",
    response_model=Nis2KritisKpiDrilldown,
    tags=["nis2-kritis"],
)
def get_nis2_kritis_kpi_drilldown(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
    top_n: int = 5,
) -> Nis2KritisKpiDrilldown:
    return build_nis2_kritis_kpi_drilldown(
        auth.tenant_id,
        nis2_repo,
        top_n=top_n,
    )


# ---------------------------------------------------------------------------
# What-If Board Impact Simulator
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/ai-governance/what-if/board-impact",
    response_model=WhatIfScenarioResult,
    tags=["ai-governance"],
)
def post_what_if_board_impact(
    body: WhatIfScenarioInput,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    gap_repo: Annotated[ComplianceGapRepository, Depends(get_compliance_gap_repository)],
    violation_repo: Annotated[ViolationRepository, Depends(get_violation_repository)],
    nis2_repo: Annotated[Nis2KritisKpiRepository, Depends(get_nis2_kritis_kpi_repository)],
) -> WhatIfScenarioResult:
    _ensure_feature_what_if_simulator(auth.tenant_id, session)
    return simulate_board_impact(
        body,
        auth.tenant_id,
        session=session,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        violation_repo=violation_repo,
        nis2_repo=nis2_repo,
    )


# ---------------------------------------------------------------------------
# Internal: Advisor Metrics (feature-flagged + OPA-guarded)
# ---------------------------------------------------------------------------

_advisor_metrics_guard = create_feature_guard(FeatureFlag.advisor_metrics_internal)


@app.get(
    "/api/internal/advisor/metrics",
    response_model=AdvisorMetricsResponse,
    tags=["internal"],
    dependencies=[Depends(_advisor_metrics_guard)],
)
def get_advisor_metrics(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
) -> AdvisorMetricsResponse:
    role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name="COMPLIANCEHUB_OPA_ROLE_ADVISOR_METRICS",
        default="platform_admin",
    )
    enforce_action_policy(
        "view_advisor_metrics",
        UserPolicyContext(tenant_id=auth.tenant_id, user_role=role),
        risk_score=0.2,
    )
    return aggregate_advisor_metrics(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
    )


@app.get(
    "/api/internal/enterprise/integration-blueprints",
    response_model=EnterpriseIntegrationBlueprintResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_integration_blueprints(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    onboarding_repo: Annotated[
        EnterpriseOnboardingRepository,
        Depends(get_enterprise_onboarding_repository),
    ],
    blueprint_repo: Annotated[
        EnterpriseIntegrationBlueprintRepository,
        Depends(get_enterprise_integration_blueprint_repository),
    ],
    include_markdown: bool = Query(False),
) -> EnterpriseIntegrationBlueprintResponse:
    onboarding = onboarding_repo.get(auth.tenant_id)
    return build_enterprise_integration_blueprint_response(
        tenant_id=auth.tenant_id,
        blueprint_rows=blueprint_repo.list_for_tenant(auth.tenant_id),
        onboarding=onboarding,
        include_markdown=include_markdown,
    )


@app.get(
    "/api/internal/enterprise/connector-candidates",
    response_model=EnterpriseConnectorCandidatesResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_candidates(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    session: Annotated[Session, Depends(get_session)],
    onboarding_repo: Annotated[
        EnterpriseOnboardingRepository,
        Depends(get_enterprise_onboarding_repository),
    ],
    blueprint_repo: Annotated[
        EnterpriseIntegrationBlueprintRepository,
        Depends(get_enterprise_integration_blueprint_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    incident_repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    deadline_repo: Annotated[
        ComplianceDeadlineRepository,
        Depends(get_compliance_deadline_repository),
    ],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    include_markdown: bool = Query(False),
) -> EnterpriseConnectorCandidatesResponse:
    onboarding = onboarding_repo.get(auth.tenant_id)
    blueprints = build_enterprise_integration_blueprint_response(
        tenant_id=auth.tenant_id,
        blueprint_rows=blueprint_repo.list_for_tenant(auth.tenant_id),
        onboarding=onboarding,
        include_markdown=False,
    ).blueprint_rows
    return build_connector_candidates_response(
        tenant_id=auth.tenant_id,
        session=session,
        onboarding=onboarding,
        blueprints=blueprints,
        audit_repo=audit_repo,
        incident_repo=incident_repo,
        deadline_repo=deadline_repo,
        ai_repo=ai_repo,
        include_markdown=include_markdown,
    )


@app.get(
    "/api/internal/enterprise/connector-runtime",
    response_model=ConnectorRuntimeStatusResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_runtime(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
) -> ConnectorRuntimeStatusResponse:
    return build_connector_runtime_status(
        auth.tenant_id,
        actor=actor_id_from_request(request),
        repo=runtime_repo,
    )


@app.get(
    "/api/internal/enterprise/connector-runtime/last-sync",
    response_model=ConnectorSyncResult | None,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_runtime_last_sync(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
) -> ConnectorSyncResult | None:
    return runtime_repo.get_last_sync_result(auth.tenant_id)


@app.get(
    "/api/internal/enterprise/connector-runtime/health",
    response_model=ConnectorHealthSnapshot,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_runtime_health(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
) -> ConnectorHealthSnapshot:
    return get_connector_health_snapshot(
        auth.tenant_id,
        actor=actor_id_from_request(request),
        repo=runtime_repo,
    )


@app.get(
    "/api/internal/enterprise/connector-runtime/sync-runs",
    response_model=ConnectorSyncHistoryResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_runtime_sync_runs(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
    limit: int = Query(30, ge=1, le=100),
) -> ConnectorSyncHistoryResponse:
    return list_connector_sync_history(
        auth.tenant_id,
        actor=actor_id_from_request(request),
        repo=runtime_repo,
        limit=limit,
    )


@app.get(
    "/api/internal/enterprise/connector-runtime/latest-failure",
    response_model=ConnectorSyncResult | None,
    tags=["internal", "enterprise"],
)
def get_enterprise_connector_runtime_latest_failure(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
) -> ConnectorSyncResult | None:
    return get_latest_connector_failure(
        auth.tenant_id,
        actor=actor_id_from_request(request),
        repo=runtime_repo,
    )


@app.post(
    "/api/internal/enterprise/connector-runtime/manual-sync",
    response_model=ConnectorManualSyncResponse,
    tags=["internal", "enterprise"],
)
def post_enterprise_connector_runtime_manual_sync(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_ONBOARDING_READINESS)),
    ],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> ConnectorManualSyncResponse:
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_CONNECTOR_SYNC_TRIGGERED.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_CONNECTOR_RUNTIME.value,
        entity_id=auth.tenant_id,
        outcome="success",
        before=None,
        after=json.dumps({"manual_sync": True}),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"source_system_type": "generic_api"},
    )
    result = run_manual_connector_sync(auth.tenant_id, actor=actor, repo=runtime_repo)
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_CONNECTOR_SYNC_COMPLETED.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_CONNECTOR_RUNTIME.value,
        entity_id=result.sync_result.sync_run_id,
        outcome=result.sync_result.sync_status.value,
        before=None,
        after=json.dumps(
            {
                "records_ingested": result.sync_result.records_ingested,
                "status": result.sync_result.sync_status.value,
                "domains": [d.value for d in result.connector_instance.enabled_evidence_domains],
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"summary": result.sync_result.summary_de},
    )
    return result


@app.post(
    "/api/internal/enterprise/connector-runtime/retry-sync",
    response_model=ConnectorManualSyncResponse,
    tags=["internal", "enterprise"],
)
def post_enterprise_connector_runtime_retry_sync(
    body: ConnectorRetrySyncBody,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_ONBOARDING_READINESS)),
    ],
    runtime_repo: Annotated[
        EnterpriseConnectorRuntimeRepository,
        Depends(get_enterprise_connector_runtime_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> ConnectorManualSyncResponse:
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_CONNECTOR_SYNC_RETRY_TRIGGERED.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_CONNECTOR_RUNTIME.value,
        entity_id=body.sync_run_id or auth.tenant_id,
        outcome="success",
        before=None,
        after=json.dumps({"retry_sync": True, "sync_run_id": body.sync_run_id}),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"source_system_type": "generic_api"},
    )
    result = retry_connector_sync(
        auth.tenant_id,
        actor=actor,
        repo=runtime_repo,
        sync_run_id=body.sync_run_id,
    )
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_CONNECTOR_SYNC_COMPLETED.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_CONNECTOR_RUNTIME.value,
        entity_id=result.sync_result.sync_run_id,
        outcome=result.sync_result.sync_status.value,
        before=None,
        after=json.dumps(
            {
                "records_ingested": result.sync_result.records_ingested,
                "status": result.sync_result.sync_status.value,
                "retry_of_sync_run_id": result.sync_result.retry_of_sync_run_id,
                "failure_category": (
                    result.sync_result.failure_category.value
                    if result.sync_result.failure_category
                    else None
                ),
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"summary": result.sync_result.summary_de, "retry": True},
    )
    return result


@app.put(
    "/api/internal/enterprise/integration-blueprints",
    response_model=EnterpriseIntegrationBlueprintResponse,
    tags=["internal", "enterprise"],
)
def put_enterprise_integration_blueprints(
    body: EnterpriseIntegrationBlueprintUpsert,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_ONBOARDING_READINESS)),
    ],
    onboarding_repo: Annotated[
        EnterpriseOnboardingRepository,
        Depends(get_enterprise_onboarding_repository),
    ],
    blueprint_repo: Annotated[
        EnterpriseIntegrationBlueprintRepository,
        Depends(get_enterprise_integration_blueprint_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> EnterpriseIntegrationBlueprintResponse:
    actor = actor_id_from_request(request)
    saved = blueprint_repo.upsert(auth.tenant_id, body, actor=actor)
    onboarding = onboarding_repo.get(auth.tenant_id)
    response = build_enterprise_integration_blueprint_response(
        tenant_id=auth.tenant_id,
        blueprint_rows=blueprint_repo.list_for_tenant(auth.tenant_id),
        onboarding=onboarding,
        include_markdown=False,
    )
    record_governance_audit(
        audit_repo,
        tenant_id=auth.tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.ENTERPRISE_INTEGRATION_BLUEPRINT_UPSERT.value,
        entity_type=GovernanceAuditEntity.ENTERPRISE_INTEGRATION_BLUEPRINT.value,
        entity_id=saved.blueprint_id,
        outcome="success",
        before=None,
        after=json.dumps(
            {
                "source_system_type": saved.source_system_type.value,
                "integration_status": saved.integration_status.value,
                "domains": [d.value for d in saved.evidence_domains],
                "blockers": len(saved.blockers),
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"security_prerequisites": len(saved.security_prerequisites)},
    )
    return response


@app.get(
    "/api/internal/enterprise/control-center",
    response_model=EnterpriseControlCenterResponse,
    tags=["internal", "enterprise"],
)
def get_enterprise_control_center(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    _: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    session: Annotated[Session, Depends(get_session)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    incident_repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    deadline_repo: Annotated[
        ComplianceDeadlineRepository,
        Depends(get_compliance_deadline_repository),
    ],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    include_markdown: bool = Query(False),
) -> EnterpriseControlCenterResponse:
    return build_enterprise_control_center(
        tenant_id=auth.tenant_id,
        session=session,
        audit_repo=audit_repo,
        incident_repo=incident_repo,
        deadline_repo=deadline_repo,
        ai_repo=ai_repo,
        include_markdown=include_markdown,
        connector_runtime_repo=EnterpriseConnectorRuntimeRepository(session),
    )


@app.get(
    "/api/internal/enterprise/authority-audit-pack",
    response_model=AuthorityAuditPreparationPackResponse,
    tags=["internal", "enterprise"],
)
def get_authority_audit_preparation_pack(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    session: Annotated[Session, Depends(get_session)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    incident_repo: Annotated[NIS2IncidentRepository, Depends(get_nis2_incident_repository)],
    deadline_repo: Annotated[
        ComplianceDeadlineRepository,
        Depends(get_compliance_deadline_repository),
    ],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    inv_repo: Annotated[AISystemInventoryRepository, Depends(get_ai_inventory_repository)],
    onboarding_repo: Annotated[
        EnterpriseOnboardingRepository,
        Depends(get_enterprise_onboarding_repository),
    ],
    blueprint_repo: Annotated[
        EnterpriseIntegrationBlueprintRepository,
        Depends(get_enterprise_integration_blueprint_repository),
    ],
    focus: Annotated[PreparationPackFocus, Query()] = PreparationPackFocus.mixed,
    client_tenant_id: str | None = Query(default=None),
) -> AuthorityAuditPreparationPackResponse:
    effective_tenant_id = client_tenant_id or auth.tenant_id
    if effective_tenant_id != auth.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    pack = build_authority_audit_preparation_pack(
        tenant_id=effective_tenant_id,
        session=session,
        focus=focus,
        audit_repo=audit_repo,
        incident_repo=incident_repo,
        deadline_repo=deadline_repo,
        ai_repo=ai_repo,
        inventory_repo=inv_repo,
        onboarding_repo=onboarding_repo,
        blueprint_repo=blueprint_repo,
    )
    actor = actor_id_from_request(request)
    record_governance_audit(
        audit_repo,
        tenant_id=effective_tenant_id,
        actor_id=actor,
        actor_role=role,
        action=GovernanceAuditAction.AUTHORITY_AUDIT_PACK_GENERATED.value,
        entity_type=GovernanceAuditEntity.AUTHORITY_AUDIT_PREPARATION_PACK.value,
        entity_id=focus.value,
        outcome="success",
        before=None,
        after=json.dumps(
            {
                "focus": focus.value,
                "critical": pack.section_a_executive_posture.summary_de,
                "source_sections": pack.source_sections,
            }
        ),
        correlation_id=correlation_id_from_request(request),
        ip_address=client_ip_from_request(request),
        user_agent=user_agent_from_request(request),
        metadata={"top_urgent_items": len(pack.top_urgent_items)},
    )
    return pack


# ---------------------------------------------------------------------------
# Advisor Preset Micro-Flows (Wave 9 / 9.1 enterprise)
# ---------------------------------------------------------------------------


def _enforce_preset_opa(
    flow_type: FlowType,
    tenant_id: str,
    auth: AuthContext,
    opa_role_header: str | None,
) -> None:
    opa_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name="COMPLIANCEHUB_OPA_ROLE_ADVISOR_PRESET",
        default="advisor_user",
    )
    enforce_action_policy(
        f"advisor_preset_{flow_type.value}",
        UserPolicyContext(
            tenant_id=tenant_id or auth.tenant_id,
            user_role=opa_role,
        ),
        risk_score=0.6,
    )


@app.post(
    "/api/v1/advisor/presets/eu-ai-act-risk-assessment",
    response_model=PresetResult,
    tags=["advisor", "presets"],
)
def preset_eu_ai_act_risk_assessment(
    body: AiActRiskPresetInput,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> PresetResult:
    """Preset: EU AI Act high-risk classification assessment."""
    from app.advisor.preset_service import run_eu_ai_act_risk_preset

    _enforce_preset_opa(
        FlowType.eu_ai_act_risk_assessment,
        body.effective_tenant_id(),
        auth,
        opa_role_header,
    )
    if not body.context.tenant_id and not body.tenant_id:
        body.context.tenant_id = auth.tenant_id
    return run_eu_ai_act_risk_preset(body)


@app.post(
    "/api/v1/advisor/presets/nis2-obligations",
    response_model=PresetResult,
    tags=["advisor", "presets"],
)
def preset_nis2_obligations(
    body: Nis2ObligationsPresetInput,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> PresetResult:
    """Preset: NIS2 obligation mapping for a given entity role."""
    from app.advisor.preset_service import run_nis2_obligations_preset

    _enforce_preset_opa(
        FlowType.nis2_obligations,
        body.effective_tenant_id(),
        auth,
        opa_role_header,
    )
    if not body.context.tenant_id and not body.tenant_id:
        body.context.tenant_id = auth.tenant_id
    return run_nis2_obligations_preset(body)


@app.post(
    "/api/v1/advisor/presets/iso42001-gap-check",
    response_model=PresetResult,
    tags=["advisor", "presets"],
)
def preset_iso42001_gap_check(
    body: Iso42001GapCheckPresetInput,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> PresetResult:
    """Preset: ISO 42001 gap analysis for current governance measures."""
    from app.advisor.preset_service import run_iso42001_gap_preset

    _enforce_preset_opa(
        FlowType.iso42001_gap_check,
        body.effective_tenant_id(),
        auth,
        opa_role_header,
    )
    if not body.context.tenant_id and not body.tenant_id:
        body.context.tenant_id = auth.tenant_id
    return run_iso42001_gap_preset(body)


# ---------------------------------------------------------------------------
# GRC Read-Only APIs (Wave 10)
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/grc/ai-risks",
    tags=["grc"],
)
def list_grc_ai_risks(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    client_id: str | None = None,
    system_id: str | None = None,
) -> list[dict[str, Any]]:
    """List AI risk assessment records (read-only)."""
    from app.grc.store import list_risks
    from app.product.plan_store import require_capability

    _enforce_grc_opa("view_grc_records", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.grc_records)
    tid = tenant_id or auth.tenant_id
    records = list_risks(tenant_id=tid, client_id=client_id, system_id=system_id)
    return [r.model_dump() for r in records]


@app.get(
    "/api/v1/grc/nis2-obligations",
    tags=["grc"],
)
def list_grc_nis2_obligations(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    client_id: str | None = None,
    entity_type: str | None = None,
) -> list[dict[str, Any]]:
    """List NIS2 obligation records (read-only)."""
    from app.grc.store import list_nis2_obligations
    from app.product.plan_store import require_capability

    _enforce_grc_opa("view_grc_records", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.grc_records)
    tid = tenant_id or auth.tenant_id
    records = list_nis2_obligations(
        tenant_id=tid,
        client_id=client_id,
        entity_type=entity_type,
    )
    return [r.model_dump() for r in records]


@app.get(
    "/api/v1/grc/iso42001-gaps",
    tags=["grc"],
)
def list_grc_iso42001_gaps(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    client_id: str | None = None,
    control_family: str | None = None,
) -> list[dict[str, Any]]:
    """List ISO 42001 gap records (read-only)."""
    from app.grc.store import list_iso42001_gaps
    from app.product.plan_store import require_capability

    _enforce_grc_opa("view_grc_records", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.grc_records)
    tid = tenant_id or auth.tenant_id
    records = list_iso42001_gaps(
        tenant_id=tid,
        client_id=client_id,
        control_family=control_family,
    )
    return [r.model_dump() for r in records]


def _enforce_grc_opa(
    action: str,
    auth: AuthContext,
    opa_role_header: str | None,
) -> None:
    opa_role = resolve_opa_role_for_policy(
        header_value=opa_role_header,
        env_var_name="COMPLIANCEHUB_OPA_ROLE_GRC",
        default="platform_admin",
    )
    enforce_action_policy(
        action,
        UserPolicyContext(tenant_id=auth.tenant_id, user_role=opa_role),
        risk_score=0.3,
    )


# ---------------------------------------------------------------------------
# AI System Inventory APIs (Wave 11)
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/ai-systems",
    tags=["ai-systems"],
)
def list_ai_systems_endpoint(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    client_id: str | None = None,
    classification: str | None = None,
    nis2_relevant: bool | None = None,
) -> list[dict[str, Any]]:
    """List AI systems registered for a tenant."""
    from app.grc.store import list_ai_systems
    from app.product.plan_store import require_capability

    _enforce_grc_opa("view_ai_systems", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.ai_system_inventory)
    tid = tenant_id or auth.tenant_id
    systems = list_ai_systems(
        tenant_id=tid,
        client_id=client_id,
        classification=classification,
        nis2_relevant=nis2_relevant,
    )
    return [s.model_dump() for s in systems]


@app.get(
    "/api/v1/ai-systems/{system_id}/overview",
    tags=["ai-systems"],
)
def get_ai_system_overview(
    system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """AI-system-centric overview: metadata, GRC records, framework hints."""
    from app.grc.framework_mapping import build_system_overview_hints
    from app.grc.store import (
        get_ai_system,
        list_iso42001_gaps,
        list_nis2_obligations,
        list_risks,
    )

    _enforce_grc_opa("view_ai_systems", auth, opa_role_header)
    tid = tenant_id or auth.tenant_id

    ai_sys = get_ai_system(tenant_id=tid, system_id=system_id)
    if ai_sys is None:
        raise HTTPException(
            status_code=404,
            detail=f"AI system '{system_id}' not found for tenant.",
        )

    risks = list_risks(tenant_id=tid, system_id=system_id)
    nis2 = list_nis2_obligations(tenant_id=tid, client_id=None)
    nis2_for_sys = [r for r in nis2 if r.system_id == system_id]
    gaps = list_iso42001_gaps(tenant_id=tid, client_id=None)
    gaps_for_sys = [g for g in gaps if g.system_id == system_id]

    framework_hints = build_system_overview_hints(
        risks=risks,
        nis2_records=nis2_for_sys,
        gap_records=gaps_for_sys,
    )

    return {
        "system": ai_sys.model_dump(),
        "risk_assessments": [r.model_dump() for r in risks],
        "nis2_obligations": [r.model_dump() for r in nis2_for_sys],
        "iso42001_gaps": [g.model_dump() for g in gaps_for_sys],
        "framework_coverage": framework_hints,
    }


@app.get(
    "/api/v1/ai-systems/{system_id}/readiness",
    tags=["ai-systems"],
)
def get_ai_system_readiness(
    system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Release-gate readiness check for an AI system (advisory only)."""
    from app.grc.ai_system_readiness import evaluate_and_update

    _enforce_grc_opa("view_ai_systems", auth, opa_role_header)
    tid = tenant_id or auth.tenant_id
    result = evaluate_and_update(
        tenant_id=tid,
        system_id=system_id,
        trace_id=trace_id or "",
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Deployment Check API (Wave 14)
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/ai-systems/{system_id}/deployment-check",
    tags=["ai-systems"],
)
def get_deployment_check(
    system_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    caller_type: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Deployment readiness check for CI/Temporal (advisory only)."""
    from app.grc.ai_system_readiness import deployment_check

    _enforce_grc_opa("view_ai_systems", auth, opa_role_header)
    tid = tenant_id or auth.tenant_id
    result = deployment_check(
        tenant_id=tid,
        system_id=system_id,
        caller_type=caller_type or "manual",
        trace_id=trace_id or "",
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Client/Mandant Board Report APIs (Wave 13)
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/clients/{client_id}/ai-board-report/workflows/start",
    tags=["client-board-reports"],
    status_code=202,
)
def start_client_board_report(
    client_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    reporting_period: str | None = None,
    system_filter: str | None = None,
) -> dict[str, Any]:
    """Start a Mandant-level AI compliance board report workflow."""
    from app.grc.client_board_report_service import run_client_board_report
    from app.product.plan_store import require_capability

    _enforce_grc_opa("start_client_board_report", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.kanzlei_reports)
    tid = auth.tenant_id

    sf = [s.strip() for s in system_filter.split(",") if s.strip()] if system_filter else None

    result = run_client_board_report(
        tenant_id=tid,
        client_id=client_id,
        reporting_period=reporting_period or "",
        system_filter=sf,
    )
    return result


@app.get(
    "/api/v1/clients/{client_id}/ai-board-report/workflows/{workflow_id}",
    tags=["client-board-reports"],
)
def get_client_board_report_workflow(
    client_id: str,
    workflow_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Get status/result of a client board report workflow."""
    from app.grc.client_board_report_service import (
        get_report,
        get_workflow_status,
    )

    _enforce_grc_opa("view_client_board_report", auth, opa_role_header)

    wf = get_workflow_status(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.get("client_id") != client_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    report_data: dict[str, Any] | None = None
    if wf.get("report_id"):
        rpt = get_report(wf["report_id"])
        if rpt:
            report_data = {
                "report_id": rpt.id,
                "report_markdown": rpt.report_markdown,
                "highlights": rpt.highlights,
                "systems_included": rpt.systems_included,
                "system_ids": rpt.system_ids,
                "created_at": rpt.created_at,
            }

    return {
        "workflow_id": workflow_id,
        "status": wf.get("status", "UNKNOWN"),
        "tenant_id": wf.get("tenant_id"),
        "client_id": client_id,
        "reporting_period": wf.get("reporting_period"),
        "report": report_data,
    }


@app.get(
    "/api/v1/clients/{client_id}/ai-board-reports",
    tags=["client-board-reports"],
)
def list_client_board_reports(
    client_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> list[dict[str, Any]]:
    """List past AI board reports for a Mandant."""
    from app.grc.client_board_report_service import list_reports

    _enforce_grc_opa("view_client_board_report", auth, opa_role_header)
    reports = list_reports(tenant_id=auth.tenant_id, client_id=client_id)
    return [
        {
            "report_id": r.id,
            "reporting_period": r.reporting_period,
            "systems_included": r.systems_included,
            "highlights": r.highlights,
            "created_at": r.created_at,
        }
        for r in reports
    ]


# ---------------------------------------------------------------------------
# Integration Jobs — Internal APIs (Wave 15 / 15.1)
# ---------------------------------------------------------------------------


@app.get(
    "/api/internal/integrations/jobs",
    tags=["integrations"],
)
def list_integration_jobs(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    tenant_id: str | None = None,
    client_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    target: str | None = None,
    payload_type: str | None = None,
) -> list[dict[str, Any]]:
    """List outbox integration jobs (internal/admin)."""
    from app.integrations.store import list_jobs
    from app.product.plan_store import require_capability

    _enforce_grc_opa("view_integration_jobs", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.enterprise_integrations)
    tid = tenant_id or auth.tenant_id
    jobs = list_jobs(
        tenant_id=tid,
        client_id=client_id,
        status=status_filter,
        target=target,
        payload_type=payload_type,
    )
    return [j.model_dump() for j in jobs]


class CreateIntegrationJobRequest(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target: str = "generic_partner_api"
    client_id: str = ""
    system_id: str = ""
    trace_id: str = ""
    priority: int = 0


@app.post(
    "/api/internal/integrations/jobs",
    tags=["integrations"],
    status_code=201,
)
def create_integration_job(
    body: CreateIntegrationJobRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Manually enqueue an integration job for a source entity."""
    from app.integrations.models import IntegrationTarget
    from app.integrations.outbox import enqueue_for_entity
    from app.product.plan_store import require_capability

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.enterprise_integrations)
    try:
        tgt = IntegrationTarget(body.target)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target: {body.target}",
        )
    job = enqueue_for_entity(
        entity_type=body.source_entity_type,
        entity_id=body.source_entity_id,
        tenant_id=auth.tenant_id,
        client_id=body.client_id,
        system_id=body.system_id,
        target=tgt,
        trace_id=body.trace_id,
    )
    if job is None:
        raise HTTPException(
            status_code=422,
            detail=("Entity type not mappable or payload type not enabled"),
        )
    if body.priority:
        job.priority = body.priority
    return job.model_dump()


@app.post(
    "/api/internal/integrations/jobs/{job_id}/retry",
    tags=["integrations"],
)
def retry_integration_job(
    job_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Retry a failed / dead-lettered integration job."""
    from app.integrations.store import mark_for_retry

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    job = mark_for_retry(job_id, tenant_id=auth.tenant_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not in a retryable state",
        )
    return job.model_dump()


@app.get(
    "/api/internal/integrations/jobs/{job_id}",
    tags=["integrations"],
)
def get_integration_job(
    job_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Get integration job detail including dispatch result."""
    from app.integrations.store import get_job

    _enforce_grc_opa("view_integration_jobs", auth, opa_role_header)
    job = get_job(job_id, tenant_id=auth.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@app.post(
    "/api/internal/integrations/dispatch",
    tags=["integrations"],
)
def trigger_integration_dispatch(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Trigger dispatch of all pending integration jobs."""
    from app.integrations.dispatcher import dispatch_pending

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    return dispatch_pending()


# ---------------------------------------------------------------------------
# Mandant-Dossier Export API (Wave 16)
# ---------------------------------------------------------------------------


class MandantExportRequest(BaseModel):
    client_id: str
    period: str = ""
    export_version: int = 1
    mandant_kurzname: str = ""
    branche: str = ""
    trace_id: str = ""


@app.post(
    "/api/internal/integrations/mandant-export",
    tags=["integrations"],
    status_code=201,
)
def create_mandant_export(
    body: MandantExportRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Enqueue a Mandanten-Compliance-Dossier export job."""
    from app.integrations.outbox import enqueue_mandant_dossier
    from app.product.plan_store import require_capability

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    require_capability(auth.tenant_id, Capability.kanzlei_reports)
    job = enqueue_mandant_dossier(
        tenant_id=auth.tenant_id,
        client_id=body.client_id,
        period=body.period,
        export_version=body.export_version,
        trace_id=body.trace_id,
        mandant_kurzname=body.mandant_kurzname,
        branche=body.branche,
    )
    if job is None:
        raise HTTPException(
            status_code=422,
            detail="Dossier export payload type not enabled or duplicate",
        )
    return job.model_dump()


# ---------------------------------------------------------------------------
# SAP S/4 + BTP Inbound Endpoint (Wave 16 — reference flow)
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/integrations/sap/ai-system-event",
    tags=["integrations"],
    status_code=202,
)
def receive_sap_ai_system_event(
    body: dict[str, Any],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, Any]:
    """Receive a CloudEvents envelope from SAP S/4/BTP Event Mesh.

    Validates mandatory fields, maps to an AiSystem stub, and emits
    evidence.  Designed for future BTP Integration Suite wiring.
    """
    from app.integrations.sap_inbound import (
        process_sap_ai_system_event,
        validate_sap_envelope,
    )
    from app.product.plan_store import require_capability

    require_capability(auth.tenant_id, Capability.enterprise_integrations)

    if not body.get("tenantid"):
        body["tenantid"] = auth.tenant_id

    errors = validate_sap_envelope(body)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"validation_errors": errors},
        )
    result = process_sap_ai_system_event(body)
    return result


# ---------------------------------------------------------------------------
# Product Packaging APIs (Wave 17)
# ---------------------------------------------------------------------------


@app.get(
    "/api/internal/product/plan",
    tags=["product"],
)
def get_tenant_plan_api(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, Any]:
    """Return the product plan for the authenticated tenant."""
    from app.product.plan_store import get_tenant_plan

    plan = get_tenant_plan(auth.tenant_id)
    return {
        "tenant_id": auth.tenant_id,
        "tier": plan.tier.value,
        "bundles": sorted(b.value for b in plan.effective_bundles()),
        "capabilities": sorted(c.value for c in plan.capabilities()),
        "plan_display": plan.plan_display(),
        "label": plan.label,
    }


class SetTenantPlanRequest(BaseModel):
    tier: str = "starter"
    bundles: list[str] = []
    label: str = ""


@app.put(
    "/api/internal/product/plan/{tenant_id}",
    tags=["product"],
)
def set_tenant_plan_api(
    tenant_id: str,
    body: SetTenantPlanRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
) -> dict[str, Any]:
    """Set the product plan for a tenant (admin-only)."""
    from app.product.models import ProductTier, TenantPlanConfig
    from app.product.plan_store import set_tenant_plan

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    try:
        tier = ProductTier(body.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {body.tier}")
    plan = TenantPlanConfig(
        tenant_id=tenant_id,
        tier=tier,
        bundles=set(body.bundles),
        label=body.label,
    )
    saved = set_tenant_plan(plan)
    return {
        "tenant_id": tenant_id,
        "tier": saved.tier.value,
        "bundles": sorted(b.value for b in saved.effective_bundles()),
        "capabilities": sorted(c.value for c in saved.capabilities()),
        "plan_display": saved.plan_display(),
    }


@app.post(
    "/api/internal/product/demo-seed/{tenant_id}",
    tags=["product"],
)
def seed_demo_plan_api(
    tenant_id: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    opa_role_header: Annotated[str | None, Depends(get_optional_opa_user_role_header)],
    profile: str = Query(
        ...,
        description=(
            "Demo profile: industrie_mittelstand_demo, kanzlei_demo, sap_enterprise_demo, sme_demo"
        ),
    ),
    seed_data: bool = Query(
        default=True,
        description="Also seed sample AiSystems, GRC records, etc.",
    ),
) -> dict[str, Any]:
    """Apply a demo plan profile to a tenant and optionally seed sample data."""
    from app.product.demo_plans import seed_demo_data, seed_demo_plan

    _enforce_grc_opa("manage_integrations", auth, opa_role_header)
    plan = seed_demo_plan(tenant_id, profile)
    if plan is None:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {profile}")
    result: dict[str, Any] = {
        "tenant_id": tenant_id,
        "profile": profile,
        "tier": plan.tier.value,
        "bundles": sorted(b.value for b in plan.effective_bundles()),
        "capabilities": sorted(c.value for c in plan.capabilities()),
    }
    if seed_data:
        result["seeded_data"] = seed_demo_data(tenant_id, profile)
    return result


# ---------------------------------------------------------------------------
# GTM: Offerings, Value Hints & Telemetry (Wave 18)
# ---------------------------------------------------------------------------


@app.get(
    "/api/internal/product/offerings",
    tags=["product"],
)
def list_offerings_api(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, Any]:
    """List all defined SKU offerings (internal)."""
    from app.product.offerings import list_skus

    return {"offerings": [s.model_dump() for s in list_skus()]}


@app.get(
    "/api/internal/product/value-hints",
    tags=["product"],
)
def get_value_hints_api(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, Any]:
    """Return German value hints keyed by screen/feature, filtered by plan."""
    from app.product.copy_de import VALUE_HINTS_DE
    from app.product.plan_store import get_tenant_plan

    plan = get_tenant_plan(auth.tenant_id)
    caps = plan.capabilities()

    from app.product.models import Capability

    cap_to_hints = {
        Capability.ai_advisor_basic: ["ai_advisor"],
        Capability.ai_evidence_basic: ["evidence_views"],
        Capability.grc_records: ["grc_records"],
        Capability.ai_system_inventory: ["ai_system_inventory"],
        Capability.kanzlei_reports: ["kanzlei_reports", "kanzlei_dossier"],
        Capability.enterprise_integrations: ["enterprise_integrations"],
    }
    enabled_hints: dict[str, str] = {}
    for cap, hint_keys in cap_to_hints.items():
        if cap in caps:
            for key in hint_keys:
                if key in VALUE_HINTS_DE:
                    enabled_hints[key] = VALUE_HINTS_DE[key]
    return {
        "tenant_id": auth.tenant_id,
        "plan_tier": plan.tier.value,
        "hints": enabled_hints,
    }


@app.post(
    "/api/internal/product/telemetry/screen-view",
    tags=["product"],
)
def record_screen_view_api(
    body: dict[str, Any],
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> dict[str, str]:
    """Record a screen view event for GTM analytics (no PII)."""
    from app.product.plan_store import get_tenant_plan as _get_plan
    from app.services.rag.evidence_store import record_event as _record_ev

    plan = _get_plan(auth.tenant_id)
    _record_ev(
        {
            "event_type": "gtm_screen_view",
            "tenant_id": auth.tenant_id,
            "screen": body.get("screen", "unknown"),
            "demo_profile": body.get("demo_profile", ""),
            "plan_tier": plan.tier.value,
        }
    )
    return {"status": "recorded"}


# ─── EU AI Act Wizard ───────────────────────────────────────────────────────────


@app.post(
    "/api/v1/eu-ai-act/wizard",
    tags=["eu-ai-act-wizard"],
    summary="EU AI Act Wizard: Klassifikation + Pflichten-Mapping",
)
def run_eu_ai_act_wizard(
    body: WizardQuestionnaireRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> WizardResult:
    """Entscheidungsbaum entlang Anhang III + Art. 6/9/10/13/29 mit Rollen-Mapping."""
    from app.eu_ai_act_wizard_engine import run_wizard

    return run_wizard(body)


# ─── KI-Register ────────────────────────────────────────────────────────────────


@app.get(
    "/api/v1/ki-register",
    tags=["ki-register"],
    summary="KI-Register: Alle KI-Systeme eines Mandanten",
)
def list_ki_register_endpoint(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
) -> KIRegisterListResponse:
    from app.services.ki_register_service import list_ki_register

    return list_ki_register(auth.tenant_id, ai_repo, cls_repo)


@app.patch(
    "/api/v1/ki-register/{ai_system_id}",
    tags=["ki-register"],
    summary="KI-Register: Pflichtfelder aktualisieren",
)
def update_ki_register_entry(
    ai_system_id: str,
    body: KIRegisterUpdateRequest,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
) -> dict[str, str]:
    from app.ai_system_models import AISystemUpdate

    system = ai_repo.get_by_id(auth.tenant_id, ai_system_id)
    if system is None:
        raise HTTPException(status_code=404, detail="AI system not found")
    update_data = body.model_dump(exclude_unset=True)
    if update_data:
        ai_repo.update(auth.tenant_id, ai_system_id, AISystemUpdate(**update_data))
    return {"status": "updated", "ai_system_id": ai_system_id}


# ─── Authority Export (JSON + XML) ──────────────────────────────────────────────


@app.get(
    "/api/v1/ki-register/export",
    tags=["ki-register"],
    summary="KI-Register-Export für nationale Aufsichtsbehörden (JSON oder XML)",
)
def export_ki_register(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    fmt: str = Query(default="json", description="Export-Format: json | xml"),
) -> Response:
    from app.services.ki_register_service import authority_export_xml, build_authority_export

    export = build_authority_export(auth.tenant_id, ai_repo, cls_repo, fmt=fmt)
    if fmt == "xml":
        xml_str = authority_export_xml(export)
        return Response(content=xml_str, media_type="application/xml")
    return Response(
        content=export.model_dump_json(indent=2),
        media_type="application/json",
    )


# ─── Board Aggregation ──────────────────────────────────────────────────────────


@app.get(
    "/api/v1/ki-register/board-aggregation",
    tags=["ki-register"],
    summary="Board-Reporting: High-Risk nach Use-Case, Rollen-Verteilung, offene Maßnahmen",
)
def get_ki_register_board_aggregation(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    ai_repo: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    cls_repo: Annotated[ClassificationRepository, Depends(get_classification_repository)],
    action_repo: Annotated[
        AIGovernanceActionRepository,
        Depends(get_ai_governance_action_repository),
    ],
) -> BoardAggregation:
    from app.services.ki_register_service import build_board_aggregation

    return build_board_aggregation(auth.tenant_id, ai_repo, cls_repo, action_repo)


# ─── EU AI Act Seed ─────────────────────────────────────────────────────────────


@app.post(
    "/api/internal/eu-ai-act/seed-demo",
    tags=["eu-ai-act-wizard"],
    summary="Seed: Beispiel-Tenant mit 2-3 KI-Systemen (idempotent)",
)
def seed_eu_ai_act_demo_endpoint(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, int]:
    from app.services.eu_ai_act_seed import seed_eu_ai_act_demo

    return seed_eu_ai_act_demo(session)


# ── Identity & Auth Endpoints ─────────────────────────────────────────────────

from app.repositories.users import UserRepository  # noqa: E402
from app.services.enterprise_governance_service import (  # noqa: E402
    ApprovalWorkflowService,
    MFAService,
    PrivilegedActionService,
    SoDService,
)
from app.services.enterprise_iam_service import (  # noqa: E402
    AccessReviewService,
    IdentityProviderService,
    SCIMProvisioningService,
    SSOCallbackService,
    UserLifecycleService,
)
from app.services.identity_service import IdentityService  # noqa: E402


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None
    company: str | None = None
    language: str = "de"
    timezone: str = "Europe/Berlin"


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    company: str | None = None
    language: str | None = None
    timezone: str | None = None


class RoleAssignRequest(BaseModel):
    user_id: str
    tenant_id: str
    role: str


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED, tags=["identity"])
def register_user(
    body: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.register(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        company=body.company,
        language=body.language,
        timezone_str=body.timezone,
    )
    if "error" in result:
        code = (
            status.HTTP_409_CONFLICT
            if result["error"] == "email_taken"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result["detail"])
    # Audit log for registration
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id="system",
        actor=result["email"],
        action="user.registered",
        entity_type="user",
        entity_id=result["user_id"],
        before=None,
        after=result["email"],
    )
    return result


@app.post("/api/v1/auth/verify-email", tags=["identity"])
def verify_email(
    token: str = Query(...),
    session: Session = Depends(get_session),
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.verify_email(token)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"])
    # Audit log
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id="system",
        actor=result["email"],
        action="user.email_verified",
        entity_type="user",
        entity_id=result["user_id"],
        before=None,
        after="verified",
    )
    return result


@app.post("/api/v1/auth/login", tags=["identity"])
def login_user(
    body: LoginRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.login(email=body.email, password=body.password)
    if "error" in result:
        code_map = {
            "invalid_credentials": status.HTTP_401_UNAUTHORIZED,
            "account_disabled": status.HTTP_403_FORBIDDEN,
            "account_locked": status.HTTP_429_TOO_MANY_REQUESTS,
        }
        raise HTTPException(
            status_code=code_map.get(result["error"], status.HTTP_400_BAD_REQUEST),
            detail=result["detail"],
        )
    # Audit log
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id="system",
        actor=result["email"],
        action="user.login",
        entity_type="user",
        entity_id=result["user_id"],
        before=None,
        after=None,
    )
    return result


@app.post("/api/v1/auth/password-reset/request", tags=["identity"])
def request_password_reset(
    body: PasswordResetRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.request_password_reset(email=body.email)
    # Audit log (does not leak whether email exists)
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id="system",
        actor=body.email,
        action="user.password_reset_requested",
        entity_type="user",
        entity_id="",
        before=None,
        after=None,
    )
    return {"message": result["message"]}


@app.post("/api/v1/auth/password-reset/confirm", tags=["identity"])
def confirm_password_reset(
    body: PasswordResetConfirm,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.reset_password(token=body.token, new_password=body.new_password)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"])
    # Audit log
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id="system",
        actor=result.get("user_id", ""),
        action="user.password_reset",
        entity_type="user",
        entity_id=result.get("user_id", ""),
        before=None,
        after=None,
    )
    return {"message": result["message"]}


@app.get("/api/v1/auth/profile/{user_id}", tags=["identity"])
def get_user_profile(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    profile = svc.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return profile


@app.put("/api/v1/auth/profile/{user_id}", tags=["identity"])
def update_user_profile(
    user_id: str,
    body: ProfileUpdateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    profile = svc.update_profile(
        user_id,
        display_name=body.display_name,
        company=body.company,
        language=body.language,
        timezone_str=body.timezone,
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Audit log
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor=user_id,
        action="user.profile_updated",
        entity_type="user",
        entity_id=user_id,
        before=None,
        after=str(body.model_dump(exclude_none=True)),
    )
    return profile


@app.post("/api/v1/auth/roles/assign", tags=["identity"])
def assign_user_role(
    body: RoleAssignRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> dict:
    repo = UserRepository(session)
    svc = IdentityService(repo)
    result = svc.assign_role(
        user_id=body.user_id,
        tenant_id=body.tenant_id,
        role=body.role,
        assigned_by=None,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["detail"])
    # Audit log
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="user.role_assigned",
        entity_type="user_tenant_role",
        entity_id=body.user_id,
        before=None,
        after=f"role={body.role} tenant={body.tenant_id}",
    )
    return result


@app.get("/api/v1/auth/users", tags=["identity"])
def list_tenant_users(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> list[dict]:
    repo = UserRepository(session)
    role_assignments = repo.list_users_for_tenant(tenant_id)
    result = []
    for ra in role_assignments:
        user = repo.get_by_id(ra.user_id)
        if user:
            result.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": ra.role,
                    "tenant_id": ra.tenant_id,
                }
            )
    return result


# ── Enterprise IAM: Identity Providers ──────────────────────────────────────


class IdPCreateRequest(BaseModel):
    slug: str
    display_name: str
    protocol: str  # "saml" | "oidc"
    issuer_url: str | None = None
    metadata_url: str | None = None
    client_id: str | None = None
    attribute_mapping: dict | None = None
    default_role: str = "viewer"


class IdPUpdateRequest(BaseModel):
    display_name: str | None = None
    issuer_url: str | None = None
    metadata_url: str | None = None
    client_id: str | None = None
    attribute_mapping: dict | None = None
    default_role: str | None = None
    enabled: bool | None = None


@app.post(
    "/api/v1/enterprise/identity-providers",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-iam"],
)
def create_identity_provider(
    body: IdPCreateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_IDENTITY_PROVIDERS))
    ],
) -> dict:
    svc = IdentityProviderService(session)
    result = svc.create_provider(
        tenant_id=tenant_id,
        slug=body.slug,
        display_name=body.display_name,
        protocol=body.protocol,
        issuer_url=body.issuer_url,
        metadata_url=body.metadata_url,
        client_id=body.client_id,
        attribute_mapping=body.attribute_mapping,
        default_role=body.default_role,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"])
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="idp.created",
        entity_type="identity_provider",
        entity_id=result["id"],
        before=None,
        after=result["slug"],
    )
    return result


@app.get("/api/v1/enterprise/identity-providers", tags=["enterprise-iam"])
def list_identity_providers(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_IDENTITY_PROVIDERS))
    ],
) -> list[dict]:
    svc = IdentityProviderService(session)
    return svc.list_providers(tenant_id)


@app.get("/api/v1/enterprise/identity-providers/{provider_id}", tags=["enterprise-iam"])
def get_identity_provider(
    provider_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_IDENTITY_PROVIDERS))
    ],
) -> dict:
    svc = IdentityProviderService(session)
    result = svc.get_provider(tenant_id, provider_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity provider not found"
        )
    return result


@app.put("/api/v1/enterprise/identity-providers/{provider_id}", tags=["enterprise-iam"])
def update_identity_provider(
    provider_id: str,
    body: IdPUpdateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_IDENTITY_PROVIDERS))
    ],
) -> dict:
    svc = IdentityProviderService(session)
    result = svc.update_provider(tenant_id, provider_id, **body.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity provider not found"
        )
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="idp.updated",
        entity_type="identity_provider",
        entity_id=provider_id,
        before=None,
        after=str(body.model_dump(exclude_none=True)),
    )
    return result


@app.delete(
    "/api/v1/enterprise/identity-providers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["enterprise-iam"],
)
def delete_identity_provider(
    provider_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_IDENTITY_PROVIDERS))
    ],
) -> None:
    svc = IdentityProviderService(session)
    deleted = svc.delete_provider(tenant_id, provider_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity provider not found"
        )
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="idp.deleted",
        entity_type="identity_provider",
        entity_id=provider_id,
        before=None,
        after=None,
    )


# ── Enterprise IAM: SSO Callback ────────────────────────────────────────────


class SSOCallbackRequest(BaseModel):
    provider_id: str
    external_subject: str
    external_email: str
    external_attributes: dict | None = None


@app.post("/api/v1/enterprise/sso/callback", tags=["enterprise-iam"])
def sso_callback(
    body: SSOCallbackRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    svc = SSOCallbackService(session)
    result = svc.process_sso_login(
        provider_id=body.provider_id,
        tenant_id=tenant_id,
        external_subject=body.external_subject,
        external_email=body.external_email,
        external_attributes=body.external_attributes,
    )
    if "error" in result:
        code_map = {
            "provider_not_found": status.HTTP_404_NOT_FOUND,
            "account_disabled": status.HTTP_403_FORBIDDEN,
            "user_not_found": status.HTTP_404_NOT_FOUND,
        }
        raise HTTPException(
            status_code=code_map.get(result["error"], status.HTTP_400_BAD_REQUEST),
            detail=result["detail"],
        )
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor=result["email"],
        action="sso.login",
        entity_type="user",
        entity_id=result["user_id"],
        before=None,
        after=f"provider={result['sso_provider']}",
    )
    return result


# ── Enterprise IAM: SCIM 2.0 Provisioning ───────────────────────────────────


class SCIMProvisionRequest(BaseModel):
    email: str
    display_name: str | None = None
    scim_external_id: str | None = None
    role: str = "viewer"
    sync_source: str | None = None


class SCIMUpdateRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    scim_external_id: str | None = None


@app.post(
    "/api/v1/enterprise/scim/users",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-iam"],
)
def scim_provision_user(
    body: SCIMProvisionRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SCIM))],
) -> dict:
    svc = SCIMProvisioningService(session)
    result = svc.provision_user(
        tenant_id=tenant_id,
        email=body.email,
        display_name=body.display_name,
        scim_external_id=body.scim_external_id,
        role=body.role,
        sync_source=body.sync_source,
    )
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system:scim",
        action="scim.user_provisioned",
        entity_type="user",
        entity_id=result["user_id"],
        before=None,
        after=result["email"],
    )
    return result


@app.put("/api/v1/enterprise/scim/users/{user_id}", tags=["enterprise-iam"])
def scim_update_user(
    user_id: str,
    body: SCIMUpdateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SCIM))],
) -> dict:
    svc = SCIMProvisioningService(session)
    result = svc.update_user(
        tenant_id=tenant_id,
        user_id=user_id,
        display_name=body.display_name,
        role=body.role,
        scim_external_id=body.scim_external_id,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system:scim",
        action="scim.user_updated",
        entity_type="user",
        entity_id=user_id,
        before=None,
        after=str(body.model_dump(exclude_none=True)),
    )
    return result


@app.post("/api/v1/enterprise/scim/users/{user_id}/disable", tags=["enterprise-iam"])
def scim_disable_user(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SCIM))],
) -> dict:
    svc = SCIMProvisioningService(session)
    result = svc.disable_user(tenant_id, user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system:scim",
        action="scim.user_disabled",
        entity_type="user",
        entity_id=user_id,
        before=None,
        after="disabled",
    )
    return result


@app.post("/api/v1/enterprise/scim/users/{user_id}/deprovision", tags=["enterprise-iam"])
def scim_deprovision_user(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SCIM))],
) -> dict:
    svc = SCIMProvisioningService(session)
    result = svc.deprovision_user(tenant_id, user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="system:scim",
        action="scim.user_deprovisioned",
        entity_type="user",
        entity_id=user_id,
        before=None,
        after="deprovisioned",
    )
    return result


@app.get("/api/v1/enterprise/scim/users/{user_id}/sync-state", tags=["enterprise-iam"])
def scim_get_sync_state(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SCIM))],
) -> dict:
    svc = SCIMProvisioningService(session)
    result = svc.get_sync_state(tenant_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SCIM sync state not found"
        )
    return result


# ── Enterprise IAM: Access Reviews ──────────────────────────────────────────


class AccessReviewCreateRequest(BaseModel):
    target_user_id: str
    target_role: str
    reviewer_user_id: str | None = None
    deadline_days: int = 90


class AccessReviewDecisionRequest(BaseModel):
    decision: str  # approved | revoked | escalated
    reviewer_user_id: str
    decision_note: str | None = None


class AccessReviewBulkCreateRequest(BaseModel):
    reviewer_user_id: str | None = None
    deadline_days: int = 90


@app.post(
    "/api/v1/enterprise/access-reviews",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-iam"],
)
def create_access_review(
    body: AccessReviewCreateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
) -> dict:
    svc = AccessReviewService(session)
    result = svc.create_review(
        tenant_id=tenant_id,
        target_user_id=body.target_user_id,
        target_role=body.target_role,
        reviewer_user_id=body.reviewer_user_id,
        deadline_days=body.deadline_days,
    )
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="access_review.created",
        entity_type="access_review",
        entity_id=result["id"],
        before=None,
        after=f"role={body.target_role} user={body.target_user_id}",
    )
    return result


@app.get("/api/v1/enterprise/access-reviews", tags=["enterprise-iam"])
def list_access_reviews(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
    status_filter: str | None = Query(None, alias="status"),
) -> list[dict]:
    svc = AccessReviewService(session)
    return svc.list_reviews(tenant_id, status_filter=status_filter)


@app.get("/api/v1/enterprise/access-reviews/overdue", tags=["enterprise-iam"])
def list_overdue_access_reviews(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
) -> list[dict]:
    svc = AccessReviewService(session)
    return svc.list_overdue_reviews(tenant_id)


@app.get("/api/v1/enterprise/access-reviews/{review_id}", tags=["enterprise-iam"])
def get_access_review(
    review_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
) -> dict:
    svc = AccessReviewService(session)
    result = svc.get_review(tenant_id, review_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access review not found")
    return result


@app.post("/api/v1/enterprise/access-reviews/{review_id}/decide", tags=["enterprise-iam"])
def decide_access_review(
    review_id: str,
    body: AccessReviewDecisionRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
) -> dict:
    svc = AccessReviewService(session)
    result = svc.decide_review(
        tenant_id=tenant_id,
        review_id=review_id,
        decision=body.decision,
        reviewer_user_id=body.reviewer_user_id,
        decision_note=body.decision_note,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access review not found")
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"])
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor=body.reviewer_user_id,
        action=f"access_review.{body.decision}",
        entity_type="access_review",
        entity_id=review_id,
        before=None,
        after=f"decision={body.decision}",
    )
    return result


@app.post(
    "/api/v1/enterprise/access-reviews/bulk-create",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-iam"],
)
def bulk_create_access_reviews(
    body: AccessReviewBulkCreateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_ACCESS_REVIEWS))],
) -> list[dict]:
    svc = AccessReviewService(session)
    results = svc.create_reviews_for_privileged_roles(
        tenant_id=tenant_id,
        reviewer_user_id=body.reviewer_user_id,
        deadline_days=body.deadline_days,
    )
    audit_repo = AuditLogRepository(session)
    for r in results:
        audit_repo.record_event(
            tenant_id=tenant_id,
            actor="admin",
            action="access_review.bulk_created",
            entity_type="access_review",
            entity_id=r["id"],
            before=None,
            after=f"role={r['target_role']} user={r['target_user_id']}",
        )
    return results


# ── Enterprise IAM: User Lifecycle ──────────────────────────────────────────


class LifecycleJoinerRequest(BaseModel):
    user_id: str
    role: str = "viewer"


class LifecycleMoverRequest(BaseModel):
    user_id: str
    new_role: str


class LifecycleLeaverRequest(BaseModel):
    user_id: str


@app.post("/api/v1/enterprise/lifecycle/joiner", tags=["enterprise-iam"])
def lifecycle_joiner(
    body: LifecycleJoinerRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> dict:
    svc = UserLifecycleService(session)
    result = svc.joiner(tenant_id, body.user_id, role=body.role)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="lifecycle.joiner",
        entity_type="user",
        entity_id=body.user_id,
        before=None,
        after=f"role={body.role}",
    )
    return result


@app.post("/api/v1/enterprise/lifecycle/mover", tags=["enterprise-iam"])
def lifecycle_mover(
    body: LifecycleMoverRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> dict:
    svc = UserLifecycleService(session)
    result = svc.mover(tenant_id, body.user_id, new_role=body.new_role)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="lifecycle.mover",
        entity_type="user",
        entity_id=body.user_id,
        before=result.get("old_role"),
        after=f"role={body.new_role}",
    )
    return result


@app.post("/api/v1/enterprise/lifecycle/leaver", tags=["enterprise-iam"])
def lifecycle_leaver(
    body: LifecycleLeaverRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> dict:
    svc = UserLifecycleService(session)
    result = svc.leaver(tenant_id, body.user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    audit_repo = AuditLogRepository(session)
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor="admin",
        action="lifecycle.leaver",
        entity_type="user",
        entity_id=body.user_id,
        before=result.get("old_role"),
        after="disabled",
    )
    return result


@app.get("/api/v1/enterprise/lifecycle/status/{user_id}", tags=["enterprise-iam"])
def get_user_lifecycle_status(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_USERS))],
) -> dict:
    svc = UserLifecycleService(session)
    result = svc.get_user_status(tenant_id, user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


# ── Enterprise Governance: SoD, MFA, Approvals, Privileged Actions ──────────


class SoDPolicyCreateRequest(BaseModel):
    role_a: str
    role_b: str
    description: str | None = None
    severity: str = "block"


class MFAVerifyRequest(BaseModel):
    token: str


class StepUpRequest(BaseModel):
    token: str
    action: str


class ApprovalCreateRequest(BaseModel):
    request_type: str
    target_user_id: str | None = None
    payload: dict | None = None


class ApprovalDecisionRequest(BaseModel):
    decision: str
    decision_note: str | None = None


# ── SoD Endpoints ────────────────────────────────────────────────────────────


@app.post(
    "/api/v1/enterprise/governance/sod-policies",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-governance"],
)
def create_sod_policy(
    body: SoDPolicyCreateRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SOD_POLICIES))],
) -> dict:
    svc = SoDService(session)
    result = svc.create_policy(
        tenant_id, body.role_a, body.role_b, description=body.description, severity=body.severity
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["detail"])
    return result


@app.get("/api/v1/enterprise/governance/sod-policies", tags=["enterprise-governance"])
def list_sod_policies(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SOD_POLICIES))],
) -> list[dict]:
    return SoDService(session).list_policies(tenant_id)


@app.delete(
    "/api/v1/enterprise/governance/sod-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["enterprise-governance"],
)
def delete_sod_policy(
    policy_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SOD_POLICIES))],
) -> None:
    if not SoDService(session).delete_policy(tenant_id, policy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")


@app.post("/api/v1/enterprise/governance/sod-check", tags=["enterprise-governance"])
def check_sod_conflicts(
    user_id: str,
    proposed_role: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_SOD_POLICIES))],
) -> dict:
    conflicts = SoDService(session).check_conflicts(tenant_id, user_id, proposed_role)
    has_blocking = any(c["severity"] == "block" for c in conflicts)
    return {"conflicts": conflicts, "has_blocking": has_blocking}


# ── MFA Endpoints ────────────────────────────────────────────────────────────


@app.post(
    "/api/v1/enterprise/governance/mfa/enroll",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-governance"],
)
def enroll_mfa(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    result = MFAService(session).enroll_totp(user_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["detail"])
    return result


@app.post("/api/v1/enterprise/governance/mfa/verify-enrollment", tags=["enterprise-governance"])
def verify_mfa_enrollment(
    user_id: str,
    body: MFAVerifyRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    result = MFAService(session).verify_totp_enrollment(user_id, body.token)
    if "error" in result:
        sc = status.HTTP_400_BAD_REQUEST
        if result["error"] == "invalid_token":
            sc = status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=sc, detail=result["detail"])
    return result


@app.get("/api/v1/enterprise/governance/mfa/status/{user_id}", tags=["enterprise-governance"])
def get_mfa_status(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    return MFAService(session).get_mfa_status(user_id)


@app.post(
    "/api/v1/enterprise/governance/mfa/backup-codes",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-governance"],
)
def generate_backup_codes(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    return MFAService(session).generate_backup_codes(user_id)


@app.post("/api/v1/enterprise/governance/mfa/step-up", tags=["enterprise-governance"])
def mfa_step_up(
    body: StepUpRequest,
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    result = MFAService(session).step_up_challenge(user_id, body.token)
    if not result.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Step-up verification failed"
        )
    # Record privileged action
    PrivilegedActionService(session).record(tenant_id, user_id, body.action, step_up_verified=True)
    return result


@app.post(
    "/api/v1/enterprise/governance/mfa/reset",
    tags=["enterprise-governance"],
)
def reset_mfa(
    user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_MFA))],
) -> dict:
    return MFAService(session).reset_mfa(user_id)


# ── Approval Workflow Endpoints ──────────────────────────────────────────────


@app.post(
    "/api/v1/enterprise/governance/approvals",
    status_code=status.HTTP_201_CREATED,
    tags=["enterprise-governance"],
)
def create_approval_request(
    body: ApprovalCreateRequest,
    requester_user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_APPROVAL_WORKFLOWS))
    ],
) -> dict:
    return ApprovalWorkflowService(session).create_request(
        tenant_id,
        body.request_type,
        requester_user_id,
        target_user_id=body.target_user_id,
        payload=body.payload,
    )


@app.get("/api/v1/enterprise/governance/approvals", tags=["enterprise-governance"])
def list_approval_requests(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_APPROVAL_WORKFLOWS))
    ],
    status_filter: str | None = None,
) -> list[dict]:
    return ApprovalWorkflowService(session).list_all(tenant_id, status_filter=status_filter)


@app.get("/api/v1/enterprise/governance/approvals/pending", tags=["enterprise-governance"])
def list_pending_approvals(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_APPROVAL_WORKFLOWS))
    ],
) -> list[dict]:
    return ApprovalWorkflowService(session).list_pending(tenant_id)


@app.get(
    "/api/v1/enterprise/governance/approvals/{request_id}",
    tags=["enterprise-governance"],
)
def get_approval_request(
    request_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_APPROVAL_WORKFLOWS))
    ],
) -> dict:
    result = ApprovalWorkflowService(session).get_request(tenant_id, request_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return result


@app.post(
    "/api/v1/enterprise/governance/approvals/{request_id}/decide",
    tags=["enterprise-governance"],
)
def decide_approval_request(
    request_id: str,
    body: ApprovalDecisionRequest,
    approver_user_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_APPROVAL_WORKFLOWS))
    ],
) -> dict:
    result = ApprovalWorkflowService(session).decide(
        tenant_id, request_id, approver_user_id, body.decision, decision_note=body.decision_note
    )
    if "error" in result:
        sc = status.HTTP_400_BAD_REQUEST
        if result["error"] == "self_approval":
            sc = status.HTTP_403_FORBIDDEN
        elif result["error"] == "not_found":
            sc = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=sc, detail=result["detail"])
    return result


# ── Privileged Action Events ─────────────────────────────────────────────────


@app.get("/api/v1/enterprise/governance/privileged-events", tags=["enterprise-governance"])
def list_privileged_events(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.VIEW_PRIVILEGED_EVENTS))
    ],
    actor_user_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    return PrivilegedActionService(session).list_events(
        tenant_id, actor_user_id=actor_user_id, limit=limit
    )


# ── Phase 3: Board KPI, DATEV EXTF Export, Gap Analysis ───────────────────


@app.get(
    "/api/v1/enterprise/board/kpi-report",
    tags=["enterprise-board"],
)
def get_board_kpi_report(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.VIEW_EXECUTIVE_DASHBOARD))
    ],
) -> dict:
    """Board-level KPI report with compliance score, incidents, trends, deadlines."""
    from app.services.board_kpi_aggregation import build_board_kpi_report

    return build_board_kpi_report(session, tenant_id)


@app.post(
    "/api/v1/enterprise/datev/export",
    tags=["enterprise-datev"],
)
def create_datev_extf_export(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_DATEV))],
    period_from: str = Query(..., description="Start date YYYY-MM-DD"),
    period_to: str = Query(..., description="End date YYYY-MM-DD"),
    skr: str = Query("SKR03", description="SKR03 or SKR04"),
) -> Response:
    """Generate DATEV EXTF ASCII export. Requires EXPORT_DATEV permission."""
    import uuid as _uuid
    from datetime import UTC
    from datetime import datetime as _dt

    from app.models_db import DatevExportLogDB
    from app.services.datev_extf_export import (
        DatevBookingRecord,
        compute_checksum,
        render_extf_export,
        validate_records,
    )

    # In production, records come from the booking entries in the DB.
    # For now, return an empty but valid EXTF export.
    records: list[DatevBookingRecord] = []

    errors = validate_records(records)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    content = render_extf_export(
        records,
        datum_von=period_from.replace("-", ""),
        datum_bis=period_to.replace("-", ""),
    )
    checksum = compute_checksum(content)

    log_entry = DatevExportLogDB(
        id=str(_uuid.uuid4()),
        tenant_id=tenant_id,
        export_type="extf_buchungen",
        period_from=period_from,
        period_to=period_to,
        record_count=len(records),
        checksum=checksum,
        step_up_verified=False,
        created_at_utc=_dt.now(UTC),
    )
    session.add(log_entry)
    session.commit()

    return Response(
        content=content,
        media_type="text/plain; charset=cp1252",
        headers={
            "Content-Disposition": (
                f'attachment; filename="EXTF_export_{period_from}_{period_to}.csv"'
            ),
            "X-Checksum-SHA256": checksum,
        },
    )


@app.post(
    "/api/v1/enterprise/gap-analysis/run",
    tags=["enterprise-gap-analysis"],
)
def trigger_gap_analysis(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.RUN_GAP_ANALYSIS))],
    norms: str = Query("eu_ai_act,iso_42001,nis2,dsgvo", description="Comma-separated norms"),
) -> dict:
    """Trigger RAG-powered gap analysis for the tenant."""
    from app.services.gap_analysis_agent import run_gap_analysis

    norm_list = [n.strip() for n in norms.split(",") if n.strip()]
    report = run_gap_analysis(session, tenant_id=tenant_id, norms=norm_list)
    session.commit()
    return {
        "report_id": report.id,
        "status": report.status,
        "norm_scope": report.norm_scope,
    }


@app.get(
    "/api/v1/enterprise/gap-analysis/reports",
    tags=["enterprise-gap-analysis"],
)
def list_gap_analysis_reports(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_GAP_REPORTS))],
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """List gap analysis reports for the tenant."""
    from app.services.gap_analysis_agent import list_gap_reports

    return list_gap_reports(session, tenant_id, limit=limit)


@app.get(
    "/api/v1/enterprise/gap-analysis/reports/{report_id}",
    tags=["enterprise-gap-analysis"],
)
def get_gap_analysis_report(
    report_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_GAP_REPORTS))],
) -> dict:
    """Get a specific gap analysis report."""
    from app.services.gap_analysis_agent import get_gap_report

    result = get_gap_report(session, tenant_id, report_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap report not found")
    return result


@app.post(
    "/api/v1/enterprise/rag/ingest",
    tags=["enterprise-rag"],
)
def ingest_norm_text(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_TENANT_SETTINGS))
    ],
    norm: str = Query(..., description="Norm identifier, e.g. eu_ai_act"),
    article_ref: str = Query(..., description="Article reference, e.g. Art. 9 Abs. 2"),
    text_content: str = Query(..., description="Full article/paragraph text"),
    valid_from: str | None = Query(None, description="Validity start YYYY-MM-DD"),
) -> dict:
    """Ingest regulatory text for RAG-based gap analysis."""
    from app.services.rag_norm_ingestion import ingest_norm_chunks

    rows = ingest_norm_chunks(
        session,
        norm=norm,
        article_ref=article_ref,
        text_content=text_content,
        valid_from=valid_from,
    )
    session.commit()
    return {"ingested_chunks": len(rows), "norm": norm, "article_ref": article_ref}


# ── Phase 4: PDF/A-3 Report, XRechnung 3.0, n8n Webhooks ─────────────────


class XRechnungLineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    tax_percent: float = 19.0


class XRechnungExportRequest(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    issue_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    seller_name: str
    seller_tax_id: str
    seller_address: str
    buyer_name: str
    buyer_reference: str  # Leitweg-ID
    buyer_address: str = ""
    line_items: list[XRechnungLineItem]
    currency: str = "EUR"
    note: str | None = None


class N8nWebhookRequest(BaseModel):
    event_type: str
    data: dict = Field(default_factory=dict)


@app.get(
    "/api/v1/enterprise/board/pdf-report",
    tags=["enterprise-board"],
)
def get_board_pdf_report(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.GENERATE_PDF_REPORT))],
) -> Response:
    """Generate PDF/A-3 board report from KPI data. GoBD-konform, archivierungssicher."""
    import uuid as _uuid
    from datetime import UTC
    from datetime import datetime as _dt

    from app.models_db import ReportExportDB
    from app.services.board_kpi_aggregation import build_board_kpi_report
    from app.services.pdf_report_generator import generate_board_pdf_report

    kpi_raw = build_board_kpi_report(session, tenant_id)

    # Map KPI endpoint data to PDF generator input
    kpi_data = {
        "tenant_name": kpi_raw.get("tenant_id", tenant_id),
        "reporting_period": _dt.now(UTC).strftime("%Y-%m"),
        "overall_score": kpi_raw.get("compliance_score", {}).get("overall_score", 0.0),
        "norm_scores": [],
        "critical_findings": [
            {
                "title": f.get("event_type", "Finding"),
                "norm": f.get("detail", ""),
                "open_measures": [],
            }
            for f in kpi_raw.get("top_findings", [])[:5]
        ],
        "incidents": {
            "nis2": kpi_raw.get("incident_statistics", {}),
            "dsgvo": kpi_raw.get("incident_statistics", {}),
        },
        "deadlines": [
            {
                "regulation": d.get("norm", ""),
                "deadline": d.get("deadline", ""),
                "description": d.get("description", ""),
            }
            for d in kpi_raw.get("upcoming_deadlines", [])
        ],
    }

    html_bytes = generate_board_pdf_report(kpi_data, tenant_id)
    checksum = hashlib.sha256(html_bytes).hexdigest()

    # Audit log
    log_entry = ReportExportDB(
        id=str(_uuid.uuid4()),
        tenant_id=tenant_id,
        report_type="pdf_board_report",
        format="html_pdfa3",
        file_size_bytes=len(html_bytes),
        checksum=checksum,
        created_at_utc=_dt.now(UTC),
    )
    session.add(log_entry)
    session.commit()

    return Response(
        content=html_bytes,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="board-report-'
                + quote(re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id), safe="")
                + '.html"'
            ),
            "X-Checksum-SHA256": checksum,
            "X-PDFA-Version": "3",
            "X-PDFA-Conformance": "B",
        },
    )


@app.post(
    "/api/v1/enterprise/xrechnung/export",
    tags=["enterprise-xrechnung"],
)
def create_xrechnung_export(
    body: XRechnungExportRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.EXPORT_XRECHNUNG))],
) -> Response:
    """Generate XRechnung 3.0 / EN-16931 UBL 2.1 XML invoice."""
    import uuid as _uuid
    from datetime import UTC
    from datetime import date as _date
    from datetime import datetime as _dt

    from app.models_db import XRechnungExportDB
    from app.services.xrechnung_export import (
        XRechnungInvoice,
        generate_xrechnung_xml,
        validate_xrechnung,
    )

    invoice = XRechnungInvoice(
        invoice_id=body.invoice_id,
        issue_date=_date.fromisoformat(body.issue_date),
        due_date=_date.fromisoformat(body.due_date),
        seller_name=body.seller_name,
        seller_tax_id=body.seller_tax_id,
        seller_address=body.seller_address,
        buyer_name=body.buyer_name,
        buyer_reference=body.buyer_reference,
        buyer_address=body.buyer_address,
        line_items=[item.model_dump() for item in body.line_items],
        currency=body.currency,
        note=body.note,
    )

    xml_content = generate_xrechnung_xml(invoice)
    errors = validate_xrechnung(xml_content)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    # Compute total for audit log
    total_gross = sum(
        item.quantity * item.unit_price * (1 + item.tax_percent / 100) for item in body.line_items
    )

    log_entry = XRechnungExportDB(
        id=str(_uuid.uuid4()),
        tenant_id=tenant_id,
        invoice_id=body.invoice_id,
        buyer_reference=body.buyer_reference,
        total_gross=round(total_gross, 2),
        currency=body.currency,
        validation_errors=len(errors),
        created_at_utc=_dt.now(UTC),
    )
    session.add(log_entry)
    session.commit()

    safe_invoice_id = quote(re.sub(r"[^a-zA-Z0-9_-]", "_", body.invoice_id), safe="")
    return Response(
        content=xml_content,
        media_type="application/xml; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="XRechnung_{safe_invoice_id}.xml"',
        },
    )


@app.post(
    "/api/v1/enterprise/n8n/webhook",
    tags=["enterprise-n8n"],
)
def receive_n8n_webhook(
    body: N8nWebhookRequest,
    request: Request,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_N8N_WEBHOOKS))],
) -> dict:
    """Receive and validate n8n webhook calls (HMAC-authenticated)."""
    from app.services.n8n_webhook_service import (
        build_webhook_payload,
        verify_hmac_signature,
    )

    secret = os.environ.get("COMPLIANCEHUB_N8N_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Webhook secret not configured",
        )

    signature = request.headers.get("X-Hub-Signature-256", "").strip()
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HMAC signature",
        )

    raw_body = json.dumps(body.model_dump(), default=str).encode("utf-8")
    sig_value = signature.removeprefix("sha256=")
    if not verify_hmac_signature(raw_body, secret, sig_value):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature",
        )

    payload = build_webhook_payload(body.event_type, tenant_id, body.data)
    logger.info(
        "n8n_webhook_received tenant=%s event=%s correlation=%s",
        tenant_id,
        body.event_type,
        payload.get("correlation_id"),
    )
    return {"status": "accepted", "correlation_id": payload.get("correlation_id")}


@app.post(
    "/api/v1/enterprise/n8n/trigger",
    tags=["enterprise-n8n"],
)
def trigger_n8n_workflow(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_N8N_WEBHOOKS))],
    workflow_type: str = Query(..., description="Workflow type to trigger"),
    webhook_url: str = Query(..., description="n8n webhook URL"),
) -> dict:
    """Trigger an n8n workflow via webhook."""
    from urllib.parse import urlparse

    from app.services.n8n_webhook_service import (
        N8nWorkflowType,
        build_webhook_payload,
        trigger_n8n_webhook,
    )

    # Validate webhook URL — must use https (or http for localhost dev)
    parsed = urlparse(webhook_url)
    if parsed.scheme not in ("https", "http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="webhook_url must use https:// or http://",
        )

    # Restrict to configured allowed hosts if env var is set
    allowed_hosts_raw = os.environ.get("COMPLIANCEHUB_N8N_ALLOWED_HOSTS", "")
    if allowed_hosts_raw:
        allowed = {h.strip().lower() for h in allowed_hosts_raw.split(",") if h.strip()}
        if parsed.hostname and parsed.hostname.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url host not in allowed list",
            )

    # Validate workflow type
    valid_types = [t.value for t in N8nWorkflowType]
    if workflow_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow_type. Must be one of: {valid_types}",
        )

    payload = build_webhook_payload(workflow_type, tenant_id, {"triggered_by": "api"})
    secret = os.environ.get("COMPLIANCEHUB_N8N_WEBHOOK_SECRET")
    result = trigger_n8n_webhook(webhook_url, payload, secret)
    # Sanitize result — don't expose raw error details
    sanitized = {"status_code": result.get("status_code")}
    if "error" in result:
        sanitized["error"] = "webhook_delivery_failed"
    return {"workflow_type": workflow_type, "result": sanitized}


# ── Phase 5: Tenant Onboarding Wizard ────────────────────────────────────────


@app.get(
    "/api/v1/enterprise/onboarding/status",
    tags=["enterprise-onboarding"],
)
def get_onboarding_status_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_TENANT_SETTINGS))
    ],
) -> dict:
    """Get onboarding wizard status for the current tenant."""
    from app.services.tenant_onboarding_wizard import get_onboarding_status

    session = next(get_session())
    try:
        result = get_onboarding_status(session, tenant_id)
        if result is None:
            return {"status": "not_started", "tenant_id": tenant_id}
        return result
    finally:
        session.close()


@app.put(
    "/api/v1/enterprise/onboarding/step/{step}",
    tags=["enterprise-onboarding"],
)
def update_onboarding_step_endpoint(
    step: int,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_TENANT_SETTINGS))
    ],
    request_body: dict | None = None,
) -> dict:
    """Update onboarding wizard step for the current tenant."""
    from app.services.tenant_onboarding_wizard import update_onboarding_step

    if step < 1 or step > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step must be between 1 and 6",
        )
    session = next(get_session())
    try:
        step_data = request_body or {}
        return update_onboarding_step(session, tenant_id, step, step_data)
    finally:
        session.close()


@app.post(
    "/api/v1/enterprise/onboarding/complete",
    tags=["enterprise-onboarding"],
)
def complete_onboarding_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.MANAGE_TENANT_SETTINGS))
    ],
) -> dict:
    """Mark onboarding as complete for the current tenant."""
    from app.services.tenant_onboarding_wizard import complete_onboarding

    session = next(get_session())
    try:
        return complete_onboarding(session, tenant_id)
    finally:
        session.close()


@app.get(
    "/api/v1/enterprise/onboarding/templates",
    tags=["enterprise-onboarding"],
)
def get_onboarding_templates(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
) -> dict:
    """Get industry templates for onboarding wizard."""
    from app.services.tenant_onboarding_wizard import INDUSTRY_TEMPLATES

    return {"templates": INDUSTRY_TEMPLATES}


# ── Phase 5: Subscription & Billing (Stripe) ─────────────────────────────────


@app.get(
    "/api/v1/enterprise/billing/plans",
    tags=["enterprise-billing"],
)
def list_billing_plans(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
) -> dict:
    """List available subscription plans."""
    from app.services.stripe_billing_service import get_plans

    return {"plans": get_plans()}


@app.get(
    "/api/v1/enterprise/billing/subscription",
    tags=["enterprise-billing"],
)
def get_billing_subscription(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_BILLING))],
) -> dict:
    """Get current subscription for the tenant."""
    from app.services.stripe_billing_service import get_tenant_subscription

    session = next(get_session())
    try:
        result = get_tenant_subscription(session, tenant_id)
        if result is None:
            return {"subscription": None, "tenant_id": tenant_id}
        return {"subscription": result}
    finally:
        session.close()


@app.post(
    "/api/v1/enterprise/billing/subscribe",
    tags=["enterprise-billing"],
)
def start_trial_subscription(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_BILLING))],
    plan_name: str = Query(..., description="Plan name: starter, professional, or enterprise"),
) -> dict:
    """Start a trial subscription for the tenant."""
    from app.services.stripe_billing_service import create_trial_subscription

    session = next(get_session())
    try:
        result = create_trial_subscription(session, tenant_id, plan_name)
        return {"subscription": result}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        session.close()


@app.post(
    "/api/v1/enterprise/billing/stripe-webhook",
    tags=["enterprise-billing"],
)
async def stripe_webhook(request: Request) -> dict:
    """Receive and validate Stripe webhook calls (HMAC-authenticated)."""
    from app.services.stripe_billing_service import (
        handle_stripe_webhook_event,
        verify_stripe_signature,
    )

    secret = os.environ.get("COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe webhook secret not configured",
        )

    signature = request.headers.get("Stripe-Signature", "").strip()
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Stripe signature",
        )

    raw_body = await request.body()
    if not verify_stripe_signature(raw_body, signature, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Stripe signature",
        )

    body = json.loads(raw_body)
    event_type = body.get("type", "unknown")
    event_data = body.get("data", {})

    session = next(get_session())
    try:
        result = handle_stripe_webhook_event(session, event_type, event_data)
        return result
    finally:
        session.close()


# ── Phase 6: Feature-Gating, Customer Portal & Trial ────────────────────────


@app.get(
    "/api/v1/enterprise/billing/trial-status",
    tags=["enterprise-billing"],
)
def get_trial_banner_status(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
) -> dict:
    """Return trial status for the in-app trial banner."""
    from app.services.stripe_billing_service import get_trial_status

    session = next(get_session())
    try:
        return get_trial_status(session, tenant_id)
    finally:
        session.close()


@app.post(
    "/api/v1/enterprise/billing/portal-session",
    tags=["enterprise-billing"],
)
def create_billing_portal_session(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_BILLING))],
    return_url: str = Query(
        default="https://app.compliancehub.de/billing",
        description="URL to redirect to after portal session",
    ),
) -> dict:
    """Create a Stripe Customer Portal session for self-service management."""
    from app.services.stripe_billing_service import (
        create_customer_portal_session,
        get_tenant_subscription,
    )

    session = next(get_session())
    try:
        sub = get_tenant_subscription(session, tenant_id)
        if sub is None or not sub.get("stripe_customer_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer found for this tenant",
            )
        return create_customer_portal_session(
            tenant_id=tenant_id,
            stripe_customer_id=sub["stripe_customer_id"],
            return_url=return_url,
        )
    finally:
        session.close()


@app.get(
    "/api/v1/enterprise/billing/feature-check",
    tags=["enterprise-billing"],
)
def check_feature_gate_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_DASHBOARD))],
    feature: str = Query(..., description="Feature key to check, e.g. datev_export"),
) -> dict:
    """Check if a specific feature is accessible under the tenant's current plan.

    Returns HTTP 402 if the feature requires a higher plan.
    """
    from app.services.feature_gating import check_feature_gate

    session = next(get_session())
    try:
        check_feature_gate(session, tenant_id, feature)
        return {"feature": feature, "accessible": True}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Trust Center & Assurance Portal endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/trust-center/public",
    tags=["trust-center"],
)
def get_trust_center_public() -> dict:
    """Public trust center content – no authentication required."""
    from app.services.trust_center_service import get_public_trust_center_content

    return get_public_trust_center_content()


@app.get(
    "/api/v1/trust-center/assets",
    tags=["trust-center"],
)
def list_trust_center_assets_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_TRUST_CENTER))],
    request: Request,
) -> dict:
    """List published trust center assets for the tenant (gated)."""
    from app.services.trust_center_service import (
        list_trust_center_assets,
        log_trust_center_access,
        max_sensitivity_for_role,
    )

    max_sens = max_sensitivity_for_role(_role.value)

    session = next(get_session())
    try:
        log_trust_center_access(
            session,
            tenant_id=tenant_id,
            actor=None,
            role=_role.value,
            action="list_assets",
            resource_type="trust_center",
            ip_address=request.client.host if request.client else None,
        )
        assets = list_trust_center_assets(session, tenant_id, sensitivity_max=max_sens)
        return {"assets": assets, "count": len(assets)}
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/assets/{asset_id}",
    tags=["trust-center"],
)
def get_trust_center_asset_endpoint(
    asset_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.DOWNLOAD_ASSURANCE_DOCS))
    ],
    request: Request,
) -> dict:
    """Retrieve a single trust center asset (gated download)."""
    from app.services.trust_center_service import (
        get_trust_center_asset,
        log_trust_center_access,
        max_sensitivity_for_role,
    )

    max_sens = max_sensitivity_for_role(_role.value)
    session = next(get_session())
    try:
        asset = get_trust_center_asset(session, tenant_id, asset_id, sensitivity_max=max_sens)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        log_trust_center_access(
            session,
            tenant_id=tenant_id,
            actor=None,
            role=_role.value,
            action="download_asset",
            resource_type="trust_center_asset",
            resource_id=asset_id,
            ip_address=request.client.host if request.client else None,
        )
        return asset
    finally:
        session.close()


class TrustCenterAssetInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    asset_type: str = "policy"
    sensitivity: str = "customer"
    framework_refs: list[str] = Field(default_factory=list)
    file_name: str | None = None
    published: bool = False


@app.post(
    "/api/v1/trust-center/assets",
    tags=["trust-center"],
    status_code=status.HTTP_201_CREATED,
)
def create_trust_center_asset_endpoint(
    body: TrustCenterAssetInput,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_TRUST_CENTER))],
) -> dict:
    """Create a new trust center asset (admin)."""
    from app.services.trust_center_service import create_trust_center_asset

    session = next(get_session())
    try:
        return create_trust_center_asset(session, tenant_id, body.model_dump())
    finally:
        session.close()


@app.put(
    "/api/v1/trust-center/assets/{asset_id}",
    tags=["trust-center"],
)
def update_trust_center_asset_endpoint(
    asset_id: str,
    body: TrustCenterAssetInput,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_TRUST_CENTER))],
) -> dict:
    """Update an existing trust center asset (admin)."""
    from app.services.trust_center_service import update_trust_center_asset

    session = next(get_session())
    try:
        result = update_trust_center_asset(session, tenant_id, asset_id, body.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Asset not found")
        return result
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/evidence-bundles",
    tags=["trust-center"],
)
def list_evidence_bundles_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.ACCESS_EVIDENCE_BUNDLES))
    ],
) -> dict:
    """List evidence bundles for the tenant."""
    from app.services.trust_center_service import list_evidence_bundles

    session = next(get_session())
    try:
        bundles = list_evidence_bundles(session, tenant_id)
        return {"bundles": bundles, "count": len(bundles)}
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/evidence-bundles/{bundle_id}",
    tags=["trust-center"],
)
def get_evidence_bundle_endpoint(
    bundle_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.ACCESS_EVIDENCE_BUNDLES))
    ],
    request: Request,
) -> dict:
    """Retrieve a single evidence bundle."""
    from app.services.trust_center_service import (
        get_evidence_bundle,
        log_trust_center_access,
    )

    session = next(get_session())
    try:
        bundle = get_evidence_bundle(session, tenant_id, bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="Evidence bundle not found")
        log_trust_center_access(
            session,
            tenant_id=tenant_id,
            actor=None,
            role=_role.value,
            action="download_bundle",
            resource_type="evidence_bundle",
            resource_id=bundle_id,
            ip_address=request.client.host if request.client else None,
        )
        return bundle
    finally:
        session.close()


class GenerateBundleInput(BaseModel):
    bundle_type: str = Field(
        ...,
        description=(
            "One of: iso_27001, nis2, dsgvo, eu_ai_act,"
            " gobd_revision, vendor_security_review, auditor_bundle"
        ),
    )


@app.post(
    "/api/v1/trust-center/evidence-bundles/generate",
    tags=["trust-center"],
    status_code=status.HTTP_201_CREATED,
)
def generate_evidence_bundle_endpoint(
    body: GenerateBundleInput,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[
        EnterpriseRole, Depends(require_permission(Permission.ACCESS_EVIDENCE_BUNDLES))
    ],
    request: Request,
) -> dict:
    """Generate a new evidence bundle for due-diligence."""
    from app.services.trust_center_service import (
        BUNDLE_TYPES,
        generate_evidence_bundle,
        log_trust_center_access,
    )

    if body.bundle_type not in BUNDLE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bundle_type. Must be one of: {', '.join(BUNDLE_TYPES)}",
        )
    session = next(get_session())
    try:
        bundle = generate_evidence_bundle(session, tenant_id, body.bundle_type)
        log_trust_center_access(
            session,
            tenant_id=tenant_id,
            actor=None,
            role=_role.value,
            action="generate_bundle",
            resource_type="evidence_bundle",
            resource_id=bundle["id"],
            ip_address=request.client.host if request.client else None,
        )
        return bundle
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/compliance-mapping",
    tags=["trust-center"],
)
def get_compliance_mapping_endpoint(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_TRUST_CENTER))],
) -> dict:
    """Compliance mapping overview: controls × frameworks."""
    from app.services.trust_center_service import (
        get_compliance_mapping_overview,
        max_sensitivity_for_role,
    )

    max_sens = max_sensitivity_for_role(_role.value)
    session = next(get_session())
    try:
        return get_compliance_mapping_overview(session, tenant_id, sensitivity_max=max_sens)
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/bundle-types",
    tags=["trust-center"],
)
def list_bundle_types() -> dict:
    """List available evidence bundle types (public info)."""
    from app.services.trust_center_service import _BUNDLE_DEFAULTS, BUNDLE_TYPES

    return {
        "bundle_types": [
            {
                "key": bt,
                "title": _BUNDLE_DEFAULTS.get(bt, {}).get("title", bt),
                "description": _BUNDLE_DEFAULTS.get(bt, {}).get("description", ""),
            }
            for bt in BUNDLE_TYPES
        ]
    }


# ---------------------------------------------------------------------------
# Evidence Bundle E-Signing Endpoints (Phase 11)
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/trust-center/bundles/{bundle_id}/sign",
    tags=["trust-center"],
)
def sign_evidence_bundle_endpoint(
    bundle_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.MANAGE_TRUST_CENTER))],
    request: Request,
) -> dict:
    """Sign an evidence bundle (compliance_admin / tenant_admin only)."""
    from app.services.trust_center_service import (
        KeyRegistryError,
        log_trust_center_access,
        sign_evidence_bundle,
    )

    session = next(get_session())
    try:
        try:
            result = sign_evidence_bundle(session, tenant_id, bundle_id, _role.value)
        except KeyRegistryError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        if not result:
            raise HTTPException(status_code=404, detail="Evidence bundle not found")
        log_trust_center_access(
            session,
            tenant_id=tenant_id,
            actor=None,
            role=_role.value,
            action="sign_bundle",
            resource_type="evidence_bundle",
            resource_id=bundle_id,
            ip_address=request.client.host if request.client else None,
        )
        return result
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/bundles/{bundle_id}/verify",
    tags=["trust-center"],
)
def verify_evidence_bundle_endpoint(
    bundle_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    _role: Annotated[EnterpriseRole, Depends(require_permission(Permission.VIEW_TRUST_CENTER))],
) -> dict:
    """Verify the signature integrity of an evidence bundle."""
    from app.services.trust_center_service import verify_evidence_bundle

    session = next(get_session())
    try:
        result = verify_evidence_bundle(session, tenant_id, bundle_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Evidence bundle not found")
        return result
    finally:
        session.close()


@app.get(
    "/api/v1/trust-center/health",
    tags=["trust-center"],
)
def trust_center_health_endpoint() -> dict:
    """Return key-registry health status (no key material exposed)."""
    from app.services.trust_center_service import get_key_registry_health

    return get_key_registry_health()
