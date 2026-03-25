"""Opt-in Nutzungs-Telemetrie (strukturierte Events, getrennt vom Audit-Log)."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.usage_events import UsageEventRepository

logger = logging.getLogger(__name__)

USAGE_TRACKING_ENV = "COMPLIANCEHUB_USAGE_TRACKING"

BOARD_VIEW_OPENED = "board_view_opened"
ADVISOR_PORTFOLIO_VIEWED = "advisor_portfolio_viewed"
ADVISOR_TENANT_REPORT_VIEWED = "advisor_tenant_report_viewed"
TENANT_SEEDED = "tenant_seeded"
TENANT_PROVISIONED = "tenant_provisioned"
EVIDENCE_UPLOADED = "evidence_uploaded"
GUIDED_SETUP_COMPLETED = "guided_setup_completed"
GOVERNANCE_ACTION_CREATED = "governance_action_created"
LLM_KPI_SUGGESTION_REQUESTED = "llm_kpi_suggestion_requested"
LLM_EXPLAIN_REQUESTED = "llm_explain_requested"
LLM_ACTION_DRAFT_REQUESTED = "llm_action_draft_requested"
LLM_AI_ACT_DOC_DRAFT_REQUESTED = "llm_ai_act_doc_draft_requested"
DEMO_SESSION_STARTED = "demo_session_started"
DEMO_FEATURE_USED = "demo_feature_used"


def _parse_tracking_enabled() -> bool:
    raw = os.getenv(USAGE_TRACKING_ENV)
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def usage_tracking_enabled() -> bool:
    return _parse_tracking_enabled()


def log_usage_event(
    session: Session,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    dedupe_same_type_hours: float | None = None,
) -> None:
    """
    Schreibt ein usage_events-Datensatz. Bei Fehlern nur Log, kein Raise (kein Request-Break).

    dedupe_same_type_hours: wenn gesetzt, kein Insert bei gleichem event_type im Zeitfenster.
    """
    if not usage_tracking_enabled():
        return
    data = dict(payload or {})
    try:
        repo = UsageEventRepository(session)
        if dedupe_same_type_hours is not None:
            since = datetime.now(UTC) - timedelta(hours=dedupe_same_type_hours)
            if repo.has_event_since(tenant_id, event_type, since=since):
                return
        repo.insert(tenant_id, event_type, data)
    except Exception:
        logger.exception(
            "usage_event_write_failed tenant=%s type=%s",
            tenant_id,
            event_type,
        )
