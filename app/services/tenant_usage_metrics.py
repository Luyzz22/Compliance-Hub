from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.llm_models import LLMTaskType
from app.repositories.llm_call_metadata import LLMCallMetadataRepository
from app.repositories.usage_events import UsageEventRepository
from app.services import usage_event_logger as uel
from app.usage_metrics_models import TenantUsageMetricsResponse


def compute_tenant_usage_metrics(session: Session, tenant_id: str) -> TenantUsageMetricsResponse:
    """Aggregiert einfache Kennzahlen aus usage_events (letzte 30 Tage)."""
    since = datetime.now(UTC) - timedelta(days=30)
    repo = UsageEventRepository(session)
    types = [
        uel.BOARD_VIEW_OPENED,
        uel.ADVISOR_PORTFOLIO_VIEWED,
        uel.ADVISOR_TENANT_REPORT_VIEWED,
        uel.EVIDENCE_UPLOADED,
        uel.GOVERNANCE_ACTION_CREATED,
    ]
    counts = repo.count_by_type_since(tenant_id, types, since=since)
    board = int(counts.get(uel.BOARD_VIEW_OPENED, 0))
    advisor = int(counts.get(uel.ADVISOR_PORTFOLIO_VIEWED, 0)) + int(
        counts.get(uel.ADVISOR_TENANT_REPORT_VIEWED, 0),
    )
    evidence = int(counts.get(uel.EVIDENCE_UPLOADED, 0))
    actions = int(counts.get(uel.GOVERNANCE_ACTION_CREATED, 0))
    last_at = repo.last_event_at(tenant_id)

    llm_repo = LLMCallMetadataRepository(session)
    llm_by_task = llm_repo.count_by_task_since(tenant_id, since=since)
    llm_total = sum(llm_by_task.values())

    def _tc(tt: LLMTaskType) -> int:
        return int(llm_by_task.get(tt.value, 0))

    return TenantUsageMetricsResponse(
        tenant_id=tenant_id,
        last_active_at=last_at,
        board_views_last_30d=board,
        advisor_views_last_30d=advisor,
        evidence_uploads_last_30d=evidence,
        actions_created_last_30d=actions,
        llm_calls_last_30d=llm_total,
        llm_legal_reasoning_calls_last_30d=_tc(LLMTaskType.LEGAL_REASONING),
        llm_structured_output_calls_last_30d=_tc(LLMTaskType.STRUCTURED_OUTPUT),
        llm_classification_calls_last_30d=_tc(LLMTaskType.CLASSIFICATION_TAGGING),
        llm_chat_assistant_calls_last_30d=_tc(LLMTaskType.CHAT_ASSISTANT),
        llm_embedding_calls_last_30d=_tc(LLMTaskType.EMBEDDING_RETRIEVAL),
        llm_on_prem_sensitive_calls_last_30d=_tc(LLMTaskType.ON_PREM_SENSITIVE),
    )
