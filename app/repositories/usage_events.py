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
