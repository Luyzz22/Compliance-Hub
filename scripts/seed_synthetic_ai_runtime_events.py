#!/usr/bin/env python3
"""
SYNTHETISCHE Demo-/Pilot-Daten für ai_runtime_events (nicht für Produktion).

- Quelle: synthetic_demo_seed (Runtime-Katalog).
- Idempotent über stabile source_event_ids (siehe app.services.demo_synthetic_runtime_events).

Usage:
  python scripts/seed_synthetic_ai_runtime_events.py --tenant-id TENANT --system-id SYS1
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from app.db import engine  # noqa: E402
from app.models_db import AISystemTable  # noqa: E402
from app.services.demo_synthetic_runtime_events import (  # noqa: E402
    ensure_synthetic_runtime_events_for_system,
)
from app.services.operational_monitoring_index import (  # noqa: E402
    compute_tenant_operational_monitoring_index,
)


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

        n = ensure_synthetic_runtime_events_for_system(
            session,
            tid,
            sid,
            tag="cli",
        )
        if args.dry_run:
            session.rollback()
            print(f"dry-run: would insert up to {n} new events (rolled back)")
            return

        session.commit()
        print(f"inserted {n} synthetic runtime events")

        oami = compute_tenant_operational_monitoring_index(
            session,
            tid,
            window_days=90,
            persist_snapshot=True,
        )
        session.commit()
        print(
            f"tenant OAMI snapshot (90d): index={oami.operational_monitoring_index} "
            f"level={oami.level} systems={oami.systems_scored}",
        )


if __name__ == "__main__":
    main()
