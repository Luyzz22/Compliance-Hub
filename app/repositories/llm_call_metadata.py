from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm_models import LLMCallMetadataRecord
from app.models_db import LLMCallMetadataDB


class LLMCallMetadataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, row: LLMCallMetadataRecord) -> None:
        rec = LLMCallMetadataDB(
            id=str(uuid4()),
            tenant_id=row.tenant_id,
            task_type=row.task_type.value,
            provider=row.provider.value,
            model_id=row.model_id,
            prompt_length=row.prompt_length,
            response_length=row.response_length,
            latency_ms=row.latency_ms,
            estimated_input_tokens=row.estimated_input_tokens,
            estimated_output_tokens=row.estimated_output_tokens,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(rec)
        self._session.commit()

    def count_since(self, tenant_id: str, *, since: datetime) -> int:
        stmt = select(func.count()).where(
            LLMCallMetadataDB.tenant_id == tenant_id,
            LLMCallMetadataDB.created_at_utc >= since,
        )
        n = self._session.execute(stmt).scalar_one()
        return int(n or 0)

    def count_by_task_since(self, tenant_id: str, *, since: datetime) -> dict[str, int]:
        stmt = (
            select(LLMCallMetadataDB.task_type, func.count())
            .where(
                LLMCallMetadataDB.tenant_id == tenant_id,
                LLMCallMetadataDB.created_at_utc >= since,
            )
            .group_by(LLMCallMetadataDB.task_type)
        )
        rows = self._session.execute(stmt).all()
        return {str(tt): int(cnt) for tt, cnt in rows}
