"""Persistenz: AI-Compliance-Board-Reports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import AiComplianceBoardReportDB


class AiComplianceBoardReportRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self,
        *,
        tenant_id: str,
        created_by: str | None,
        title: str,
        audience_type: str,
        raw_payload: dict,
        rendered_markdown: str,
        rendered_html: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> AiComplianceBoardReportDB:
        row = AiComplianceBoardReportDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by=created_by,
            created_at_utc=datetime.now(UTC),
            period_start=period_start,
            period_end=period_end,
            title=title,
            audience_type=audience_type,
            raw_payload=raw_payload,
            rendered_markdown=rendered_markdown,
            rendered_html=rendered_html,
        )
        self._s.add(row)
        self._s.commit()
        self._s.refresh(row)
        return row

    def get(self, report_id: str, tenant_id: str) -> AiComplianceBoardReportDB | None:
        stmt = select(AiComplianceBoardReportDB).where(
            AiComplianceBoardReportDB.id == report_id,
            AiComplianceBoardReportDB.tenant_id == tenant_id,
        )
        return self._s.scalars(stmt).first()

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
    ) -> list[AiComplianceBoardReportDB]:
        stmt = (
            select(AiComplianceBoardReportDB)
            .where(AiComplianceBoardReportDB.tenant_id == tenant_id)
            .order_by(AiComplianceBoardReportDB.created_at_utc.desc())
            .limit(limit)
        )
        return list(self._s.scalars(stmt))
