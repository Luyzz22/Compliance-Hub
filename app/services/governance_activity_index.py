"""Governance Activity Index (GAI) aus usage_events – gemäß docs/governance-activity-index.md."""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.governance_maturity_models import (
    GovernanceActivityBlock,
    GovernanceActivityIndexComponents,
)
from app.repositories.usage_events import UsageEventRepository
from app.services.usage_event_logger import WORKSPACE_FEATURE_USED, WORKSPACE_SESSION_STARTED

logger = logging.getLogger(__name__)


def _occurred_at_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


GAI_GOVERNANCE_FEATURE_NAMES: frozenset[str] = frozenset(
    {
        "playbook_overview",
        "ai_governance_playbook",
        "cross_regulation_summary",
        "cross_regulation_dashboard",
        "board_reports_overview",
        "board_report_detail",
        "ai_system_detail",
        "advisor_governance_snapshot",
    },
)

_K_MAX = 5


def _gai_level(idx: int) -> str:
    if idx < 40:
        return "low"
    if idx < 70:
        return "medium"
    return "high"


def compute_governance_activity_index(
    session: Session,
    tenant_id: str,
    *,
    window_days: int = 90,
    as_of: datetime | None = None,
) -> GovernanceActivityBlock:
    now = as_of or datetime.now(UTC)
    since = now - timedelta(days=window_days)
    repo = UsageEventRepository(session)
    rows = repo.list_payloads_in_window(
        tenant_id,
        since=since,
        until=now,
        event_types=[WORKSPACE_SESSION_STARTED, WORKSPACE_FEATURE_USED],
    )

    active_days: set[str] = set()
    F_raw = 0
    feature_names_hit: set[str] = set()
    S = 0

    for created_at, event_type, payload_raw in rows:
        d_key = _occurred_at_utc(created_at).date().isoformat()
        payload: dict = {}
        try:
            payload = json.loads(payload_raw or "{}")
        except json.JSONDecodeError:
            logger.debug("gai_skip_bad_payload tenant=%s", tenant_id)
            continue

        if event_type == WORKSPACE_SESSION_STARTED:
            S += 1
            active_days.add(d_key)
            continue

        if event_type == WORKSPACE_FEATURE_USED:
            fn = str(payload.get("feature_name") or "").strip()
            if fn in GAI_GOVERNANCE_FEATURE_NAMES:
                F_raw += 1
                feature_names_hit.add(fn)
                active_days.add(d_key)

    D = len(active_days)
    d_sat = 20 if window_days >= 60 else 8
    f_max = 120 if window_days >= 60 else 45
    f_sat = 60 if window_days >= 60 else 20
    e_max = 4.0
    e_sat = 2.0

    F_eff = min(F_raw, f_max)
    K = min(len(feature_names_hit), _K_MAX)
    denom_d = min(window_days, d_sat)
    s_d = min(1.0, math.sqrt(D / denom_d)) if denom_d > 0 else 0.0
    s_f = min(1.0, math.sqrt(F_eff / f_sat)) if f_sat > 0 else 0.0
    s_k = K / float(_K_MAX)
    e_raw = F_eff / float(max(S, 1))
    e = min(e_raw, e_max)
    s_e = min(1.0, math.sqrt(e / e_sat)) if e_sat > 0 else 0.0

    gai_01 = 0.35 * s_d + 0.25 * s_f + 0.30 * s_k + 0.10 * s_e
    idx = int(round(100.0 * max(0.0, min(1.0, gai_01))))

    components = GovernanceActivityIndexComponents(
        s_D=round(s_d, 4),
        s_F=round(s_f, 4),
        s_K=round(s_k, 4),
        s_E=round(s_e, 4),
        D=D,
        F_eff=F_eff,
        K=K,
        S=S,
    )
    return GovernanceActivityBlock(
        index=idx,
        level=_gai_level(idx),  # type: ignore[arg-type]
        window_days=window_days,
        last_computed_at=now,
        components=components,
    )
