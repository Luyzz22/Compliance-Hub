from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

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
    return TenantUsageMetricsResponse(
        tenant_id=tenant_id,
        last_active_at=last_at,
        board_views_last_30d=board,
        advisor_views_last_30d=advisor,
        evidence_uploads_last_30d=evidence,
        actions_created_last_30d=actions,
    )
