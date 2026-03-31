from __future__ import annotations

import hashlib
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai_act_evidence_models import (
    AdvisorAgentEvidenceStoredEvent,
    RagEvidenceStatsResponse,
    RagEvidenceStoredEvent,
    RagRetrieveRequest,
    RagRetrieveResponse,
)
from app.ai_governance_models import AIBoardKpiSummary, AIGovernanceKpiSummary
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
    ComplianceDashboard,
    ComplianceRequirement,
    ComplianceStatus,
    ComplianceStatusEntry,
    ComplianceStatusUpdate,
    SystemReadiness,
)
from app.db import engine, get_session
from app.models import (
    ComplianceAction,
    DocumentIngestRequest,
    DocumentType,
    EInvoiceFormat,
)
from app.models_db import Base
from app.policy_models import Violation
from app.policy_service import evaluate_policies_for_ai_system
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository
from app.security import AuthContext, get_api_key_and_tenant, get_auth_context
from app.services.ai_governance_kpis import compute_ai_board_kpis, compute_ai_governance_kpis
from app.services.classification_engine import classify_ai_system
from app.services.compliance_engine import build_audit_hash, derive_actions
from app.services.rag.confidence import should_decline_answer
from app.services.rag.config import RAGConfig
from app.services.rag.corpus_loader import load_advisor_corpus
from app.services.rag.evidence_store import aggregate_rag_hybrid_stats, list_advisor_agent_events, list_rag_events
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.logging import log_rag_query_event
from app.services.tenant_compliance_overview import (
    TenantComplianceOverview,
    compute_tenant_compliance_overview,
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


def get_classification_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ClassificationRepository:
    return ClassificationRepository(session)


def get_compliance_gap_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ComplianceGapRepository:
    return ComplianceGapRepository(session)


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
    """Retrieval-only advisor call (no LLM). Records metadata-only RAG evidence (SHA-256 of query)."""
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
    ai_repository: Annotated[AISystemRepository, Depends(get_ai_system_repository)],
    violation_repository: Annotated[ViolationRepository, Depends(get_violation_repository)],
) -> AIBoardKpiSummary:
    return compute_ai_board_kpis(
        tenant_id=auth_context.tenant_id,
        ai_system_repository=ai_repository,
        violation_repository=violation_repository,
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
) -> AIGovernanceKpiSummary:
    if tenant_id != auth_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    return compute_ai_governance_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repository,
        policy_repository=policy_repository,
        violation_repository=violation_repository,
        audit_repository=audit_repository,
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
    tenant_id = auth_context.tenant_id
    systems = ai_repo.list_for_tenant(tenant_id)
    all_statuses = gap_repo.list_all_for_tenant(tenant_id)

    # Group statuses by ai_system_id
    status_map: dict[str, list[ComplianceStatusEntry]] = {}
    for s in all_statuses:
        status_map.setdefault(s.ai_system_id, []).append(s)

    system_readiness_list: list[SystemReadiness] = []
    total_weighted_score = 0.0
    total_weight = 0.0

    for sys in systems:
        classification = cls_repo.get_for_system(tenant_id, sys.id)
        risk_level = classification.risk_level if classification else "unclassified"

        statuses = status_map.get(sys.id, [])
        if not statuses:
            system_readiness_list.append(
                SystemReadiness(
                    ai_system_id=sys.id,
                    ai_system_name=sys.name,
                    risk_level=risk_level,
                    readiness_score=0.0,
                    total_requirements=0,
                    completed=0,
                    in_progress=0,
                    not_started=0,
                )
            )
            continue

        completed = sum(1 for s in statuses if s.status == ComplianceStatus.completed)
        in_progress = sum(1 for s in statuses if s.status == ComplianceStatus.in_progress)
        not_started = sum(1 for s in statuses if s.status == ComplianceStatus.not_started)

        # Weighted readiness score
        weighted_completed = 0.0
        weighted_total = 0.0
        for s in statuses:
            req = REQUIREMENTS_BY_ID.get(s.requirement_id)
            weight = req.weight if req else 1.0
            weighted_total += weight
            if s.status == ComplianceStatus.completed:
                weighted_completed += weight

        readiness = weighted_completed / weighted_total if weighted_total > 0 else 0.0
        total_weighted_score += weighted_completed
        total_weight += weighted_total

        system_readiness_list.append(
            SystemReadiness(
                ai_system_id=sys.id,
                ai_system_name=sys.name,
                risk_level=risk_level,
                readiness_score=round(readiness, 3),
                total_requirements=len(statuses),
                completed=completed,
                in_progress=in_progress,
                not_started=not_started,
            )
        )

    overall = round(total_weighted_score / total_weight, 3) if total_weight > 0 else 0.0

    # Deadline countdown
    from datetime import date

    deadline = date(2026, 8, 2)
    today = date.today()
    days_remaining = max(0, (deadline - today).days)

    # Top urgent gaps: not_started requirements for high_risk systems
    urgent_gaps: list[dict[str, str]] = []
    for sys in systems:
        classification = cls_repo.get_for_system(tenant_id, sys.id)
        if classification and classification.risk_level == "high_risk":
            for s in status_map.get(sys.id, []):
                if s.status == ComplianceStatus.not_started:
                    req = REQUIREMENTS_BY_ID.get(s.requirement_id)
                    if req:
                        urgent_gaps.append(
                            {
                                "ai_system_id": sys.id,
                                "ai_system_name": sys.name,
                                "requirement_id": req.id,
                                "requirement_name": req.name,
                                "article": req.article,
                            }
                        )
    urgent_gaps = urgent_gaps[:3]

    return ComplianceDashboard(
        tenant_id=tenant_id,
        overall_readiness=overall,
        systems=system_readiness_list,
        days_remaining=days_remaining,
        urgent_gaps=urgent_gaps,
    )
