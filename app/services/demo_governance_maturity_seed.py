"""Demo/Pilot: Governance-Telemetrie (GAI), synthetische Laufzeit-Events (OAMI), Snapshot-Refresh.

Idempotent pro Mandant (Anker-Usage-Event + stabile source_event_ids).
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import AISystemTable, UsageEventTable
from app.repositories.ai_runtime_events import AiRuntimeEventRepository
from app.services.demo_synthetic_runtime_events import ensure_synthetic_runtime_events_for_system
from app.services.operational_monitoring_index import compute_tenant_operational_monitoring_index
from app.services.usage_event_logger import WORKSPACE_FEATURE_USED, WORKSPACE_SESSION_STARTED

logger = logging.getLogger(__name__)

_DEMO_SEED_PAYLOAD_MARKER = "governance_maturity_v1"

# GAI: mittlerer bis mittel-hoher Index (~60–75) bei 90-Tage-Fenster
_GAI_FEATURE_ROTATION: tuple[str, ...] = (
    "playbook_overview",
    "ai_governance_playbook",
    "cross_regulation_summary",
    "cross_regulation_dashboard",
    "board_reports_overview",
)


@dataclass(frozen=True)
class DemoGovernanceMaturitySeedResult:
    telemetry_events_inserted: int
    runtime_events_inserted: int
    oami_snapshot_persisted: bool
    skipped_already_seeded: bool


def _anchor_usage_event_id(tenant_id: str) -> str:
    return str(uuid5(NAMESPACE_DNS, f"compliancehub:demo:gov_maturity:anchor:{tenant_id}"))


def _usage_event_id(tenant_id: str, seq: int) -> str:
    return str(uuid5(NAMESPACE_DNS, f"compliancehub:demo:gov_maturity:evt:{tenant_id}:{seq}"))


def _list_high_risk_system_ids(session: Session, tenant_id: str, *, limit: int = 2) -> list[str]:
    stmt = (
        select(AISystemTable.id)
        .where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.risk_level == "high",
        )
        .order_by(AISystemTable.created_at_utc.asc())
        .limit(limit)
    )
    return [str(x) for x in session.execute(stmt).scalars().all()]


def _insert_governance_telemetry(session: Session, tenant_id: str, *, now: datetime) -> int:
    """Sessions + feature_used über 8 Kalendertage; 4 unterschiedliche Governance-Features."""
    anchor = _anchor_usage_event_id(tenant_id)
    if session.get(UsageEventTable, anchor) is not None:
        return 0

    rows: list[UsageEventTable] = []
    base_payload = {"_demo_seed": _DEMO_SEED_PAYLOAD_MARKER}

    rows.append(
        UsageEventTable(
            id=anchor,
            tenant_id=tenant_id,
            event_type=WORKSPACE_SESSION_STARTED,
            payload_json=json.dumps({**base_payload, "phase": "anchor"}),
            created_at_utc=now - timedelta(days=8, hours=2),
        ),
    )

    seq = 0
    for day in range(8):
        day_ts = now - timedelta(days=7 - day, hours=10)
        seq += 1
        rows.append(
            UsageEventTable(
                id=_usage_event_id(tenant_id, seq),
                tenant_id=tenant_id,
                event_type=WORKSPACE_SESSION_STARTED,
                payload_json=json.dumps({**base_payload, "day": day}),
                created_at_utc=day_ts,
            ),
        )
        # 1–2 Feature-Events pro Tag, rotierend durch 4 Features (K=4)
        for j in range(2 if day % 2 == 0 else 1):
            fn = _GAI_FEATURE_ROTATION[(day + j) % len(_GAI_FEATURE_ROTATION)]
            seq += 1
            rows.append(
                UsageEventTable(
                    id=_usage_event_id(tenant_id, seq),
                    tenant_id=tenant_id,
                    event_type=WORKSPACE_FEATURE_USED,
                    payload_json=json.dumps({**base_payload, "feature_name": fn}),
                    created_at_utc=day_ts + timedelta(minutes=15 + j * 20),
                ),
            )

    for row in rows:
        session.add(row)
    return len(rows)


def seed_demo_governance_maturity_layer(
    session: Session,
    tenant_id: str,
    *,
    runtime_tag: str = "govmat",
) -> DemoGovernanceMaturitySeedResult:
    """
    Ergänzt einen bereits (Kern-)geseedeten Mandanten um GAI- und OAMI-Story.

    - Leerer Mandant ohne AI-Systeme: ValueError.
    - Bereits ausgeführter Telemetrie-Seed: überspringt Usage-Inserts, Runtime bleibt idempotent,
      OAMI-Snapshot wird trotzdem neu geschrieben (persist).
    """
    tid = tenant_id.strip()
    if not tid:
        raise ValueError("tenant_id required")

    stmt_count = select(AISystemTable.id).where(AISystemTable.tenant_id == tid).limit(1)
    if session.execute(stmt_count).scalar_one_or_none() is None:
        raise ValueError("Tenant has no AI systems; run core demo seed first.")

    now = datetime.now(UTC)
    skipped_anchor = session.get(UsageEventTable, _anchor_usage_event_id(tid)) is not None

    tel_n = _insert_governance_telemetry(session, tid, now=now)
    if tel_n:
        logger.info("demo_gov_maturity_telemetry tenant_id=%s rows=%d", tid, tel_n)

    high_risk = _list_high_risk_system_ids(session, tid, limit=2)
    rt_n = 0
    for sid in high_risk:
        rt_n += ensure_synthetic_runtime_events_for_system(
            session,
            tid,
            sid,
            tag=runtime_tag,
        )

    if tel_n or rt_n:
        session.flush()

    ev_repo = AiRuntimeEventRepository(session)
    win_end = now
    win_start = now - timedelta(days=90)
    for sid in high_risk:
        ev_repo.refresh_incident_summary(
            tenant_id=tid,
            ai_system_id=sid,
            window_start=win_start,
            window_end=win_end,
            summary_id=str(uuid.uuid4()),
        )

    session.flush()
    session.commit()

    oami = compute_tenant_operational_monitoring_index(
        session,
        tid,
        window_days=90,
        persist_snapshot=True,
    )
    session.commit()

    logger.info(
        "demo_gov_maturity_done tenant_id=%s telemetry=%s runtime_inserted=%d oami_index=%s",
        tid,
        tel_n,
        rt_n,
        oami.operational_monitoring_index,
    )

    return DemoGovernanceMaturitySeedResult(
        telemetry_events_inserted=tel_n,
        runtime_events_inserted=rt_n,
        oami_snapshot_persisted=True,
        skipped_already_seeded=skipped_anchor and tel_n == 0 and rt_n == 0,
    )
