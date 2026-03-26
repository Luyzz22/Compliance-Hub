#!/usr/bin/env python3
"""
SYNTHETISCHE Demo-/Pilot-Daten für ai_runtime_events (nicht für Produktion).

- Quelle: synthetic_demo_seed (von Runtime-Katalog erlaubt).
- Idempotente source_event_ids: synthetic-seed-{tenant_short}-{system_short}-{n}.
- Umgeht API-Ingest (Demo-Mandanten blocken API) – direkte Session.

Usage:
  python scripts/seed_synthetic_ai_runtime_events.py --tenant-id TENANT --system-id SYS1
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from app.db import engine  # noqa: E402
from app.models_db import AiRuntimeEventTable, AISystemTable  # noqa: E402
from app.repositories.ai_runtime_events import AiRuntimeEventRepository  # noqa: E402
from app.services.operational_monitoring_index import (  # noqa: E402
    compute_tenant_operational_monitoring_index,
)


def _slug(s: str, n: int = 8) -> str:
    x = "".join(c if c.isalnum() else "-" for c in s.lower())
    return x[:n]


def main() -> None:
    p = argparse.ArgumentParser(description="Seed synthetic AI runtime events (labeled).")
    p.add_argument("--tenant-id", required=True)
    p.add_argument("--system-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    tid = args.tenant_id.strip()
    sid = args.system_id.strip()

    with Session(engine) as session:
        sys_row = session.get(AISystemTable, sid)
        if sys_row is None or str(sys_row.tenant_id) != tid:
            print("error: ai_system not found for tenant", file=sys.stderr)
            sys.exit(1)

        repo = AiRuntimeEventRepository(session)
        now = datetime.now(UTC)
        ts = _slug(tid, 6)
        ss = _slug(sid, 6)
        events: list[dict] = [
            {
                "source_event_id": f"synthetic-seed-{ts}-{ss}-hb",
                "event_type": "heartbeat",
                "occurred_at": now - timedelta(days=1),
            },
            {
                "source_event_id": f"synthetic-seed-{ts}-{ss}-snap",
                "event_type": "metric_snapshot",
                "metric_key": "drift_score",
                "value": 0.08,
                "occurred_at": now - timedelta(days=2),
            },
            {
                "source_event_id": f"synthetic-seed-{ts}-{ss}-inc1",
                "event_type": "incident",
                "severity": "medium",
                "incident_code": "SYNTH_DEPLOYMENT_DELAY",
                "occurred_at": now - timedelta(days=5),
            },
            {
                "source_event_id": f"synthetic-seed-{ts}-{ss}-breach",
                "event_type": "metric_threshold_breach",
                "metric_key": "error_rate",
                "value": 0.12,
                "threshold_breached": True,
                "occurred_at": now - timedelta(days=7),
            },
        ]

        inserted = 0
        for spec in events:
            seid = spec["source_event_id"]
            if repo.exists_by_tenant_source_event_id(tid, "synthetic_demo_seed", seid):
                continue
            row = AiRuntimeEventTable(
                id=str(uuid.uuid4()),
                tenant_id=tid,
                ai_system_id=sid,
                source="synthetic_demo_seed",
                source_event_id=seid,
                event_type=spec["event_type"],
                severity=spec.get("severity"),
                metric_key=spec.get("metric_key"),
                incident_code=spec.get("incident_code"),
                value=spec.get("value"),
                delta=None,
                threshold_breached=spec.get("threshold_breached"),
                environment="prod",
                model_version="synthetic-v1",
                occurred_at=spec["occurred_at"].astimezone(UTC),
                received_at=now,
                extra={"region": "eu-de"},
            )
            session.add(row)
            inserted += 1

        if args.dry_run:
            session.rollback()
            print(f"dry-run: would insert {inserted} events")
            return

        session.commit()
        print(f"inserted {inserted} synthetic runtime events")

        oami = compute_tenant_operational_monitoring_index(
            session,
            tid,
            window_days=90,
            persist_snapshot=True,
        )
        print(
            f"tenant OAMI snapshot (90d): index={oami.operational_monitoring_index} "
            f"level={oami.level} systems={oami.systems_scored}",
        )


if __name__ == "__main__":
    main()
