from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_act_doc_models import (
    AIActDoc,
    AIActDocContentSource,
    AIActDocSectionKey,
)
from app.models_db import AIActDocDB


class AIActDocRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: AIActDocDB) -> AIActDoc:
        src = row.content_source
        parsed: AIActDocContentSource | None = None
        if src:
            try:
                parsed = AIActDocContentSource(src)
            except ValueError:
                parsed = None
        return AIActDoc(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            section_key=AIActDocSectionKey(row.section_key),
            title=row.title,
            content_markdown=row.content_markdown or "",
            version=row.version,
            content_source=parsed,
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )

    def list_for_system(self, tenant_id: str, ai_system_id: str) -> list[AIActDoc]:
        stmt = (
            select(AIActDocDB)
            .where(
                AIActDocDB.tenant_id == tenant_id,
                AIActDocDB.ai_system_id == ai_system_id,
            )
            .order_by(AIActDocDB.section_key)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def get_by_section(
        self,
        tenant_id: str,
        ai_system_id: str,
        section_key: AIActDocSectionKey,
    ) -> AIActDoc | None:
        stmt = select(AIActDocDB).where(
            AIActDocDB.tenant_id == tenant_id,
            AIActDocDB.ai_system_id == ai_system_id,
            AIActDocDB.section_key == section_key.value,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_domain(row) if row else None

    def upsert(
        self,
        tenant_id: str,
        ai_system_id: str,
        section_key: AIActDocSectionKey,
        title: str,
        content_markdown: str,
        actor: str,
        content_source: AIActDocContentSource | None,
        *,
        now: datetime | None = None,
    ) -> AIActDoc:
        ts = now or datetime.utcnow()
        stmt = select(AIActDocDB).where(
            AIActDocDB.tenant_id == tenant_id,
            AIActDocDB.ai_system_id == ai_system_id,
            AIActDocDB.section_key == section_key.value,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = AIActDocDB(
                id=str(uuid4()),
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                section_key=section_key.value,
                title=title,
                content_markdown=content_markdown,
                version=1,
                content_source=(
                    content_source.value if content_source else AIActDocContentSource.manual.value
                ),
                created_at=ts,
                created_by=actor,
                updated_at=ts,
                updated_by=actor,
            )
            self._session.add(row)
        else:
            row.title = title
            row.content_markdown = content_markdown
            row.version = int(row.version) + 1
            if content_source is not None:
                row.content_source = content_source.value
            row.updated_at = ts
            row.updated_by = actor

        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)
