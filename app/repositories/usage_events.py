from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import UsageEventTable


class UsageEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, tenant_id: str, event_type: str, payload: dict) -> None:
        row = UsageEventTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            event_type=event_type,
            payload_json=json.dumps(payload, default=str),
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()

    def has_event_since(
        self,
        tenant_id: str,
        event_type: str,
        *,
        since: datetime,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(UsageEventTable)
            .where(
                UsageEventTable.tenant_id == tenant_id,
                UsageEventTable.event_type == event_type,
                UsageEventTable.created_at_utc >= since,
            )
        )
        n = self._session.execute(stmt).scalar_one()
        return int(n or 0) > 0

    def count_by_type_since(
        self,
        tenant_id: str,
        event_types: list[str],
        *,
        since: datetime,
    ) -> dict[str, int]:
        stmt = (
            select(UsageEventTable.event_type, func.count())
            .where(
                UsageEventTable.tenant_id == tenant_id,
                UsageEventTable.created_at_utc >= since,
                UsageEventTable.event_type.in_(event_types),
            )
            .group_by(UsageEventTable.event_type)
        )
        rows = self._session.execute(stmt).all()
        out = {t: 0 for t in event_types}
        for et, cnt in rows:
            out[str(et)] = int(cnt)
        return out

    def last_event_at(self, tenant_id: str) -> datetime | None:
        stmt = select(func.max(UsageEventTable.created_at_utc)).where(
            UsageEventTable.tenant_id == tenant_id,
        )
        raw = self._session.execute(stmt).scalar_one_or_none()
        return raw if isinstance(raw, datetime) else None

    def list_payloads_in_window(
        self,
        tenant_id: str,
        *,
        since: datetime,
        until: datetime,
        event_types: list[str] | None = None,
    ) -> list[tuple[datetime, str, str]]:
        """(created_at_utc, event_type, payload_json) für GAI / Aggregation."""
        stmt = select(
            UsageEventTable.created_at_utc,
            UsageEventTable.event_type,
            UsageEventTable.payload_json,
        ).where(
            UsageEventTable.tenant_id == tenant_id,
            UsageEventTable.created_at_utc >= since,
            UsageEventTable.created_at_utc <= until,
        )
        if event_types:
            stmt = stmt.where(UsageEventTable.event_type.in_(event_types))
        rows = self._session.execute(stmt).all()
        return [(r[0], str(r[1]), str(r[2] if r[2] is not None else "{}")) for r in rows]
