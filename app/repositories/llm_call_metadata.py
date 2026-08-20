from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.llm_models import LLMCallMetadataRecord
from app.models_db import LLMCallMetadataDB, LLMDailyUsageBudgetDB


class LLMCallMetadataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(self, row: LLMCallMetadataRecord) -> None:
        rec = LLMCallMetadataDB(
            id=str(uuid4()),
            tenant_id=row.tenant_id,
            task_type=row.task_type.value,
            data_class=row.data_class.value,
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

    def usage_since(self, tenant_id: str, *, since: datetime) -> tuple[int, int]:
        """Return successful call count and recorded input/output tokens since a boundary."""
        stmt = select(
            func.count(),
            func.coalesce(
                func.sum(
                    LLMCallMetadataDB.estimated_input_tokens
                    + LLMCallMetadataDB.estimated_output_tokens,
                ),
                0,
            ),
        ).where(
            LLMCallMetadataDB.tenant_id == tenant_id,
            LLMCallMetadataDB.created_at_utc >= since,
        )
        count, token_total = self._session.execute(stmt).one()
        return int(count or 0), int(token_total or 0)

    def reserve_daily_usage(
        self,
        tenant_id: str,
        *,
        usage_day_utc: str,
        projected_tokens: int,
        call_limit: int,
        token_limit: int,
    ) -> bool:
        """Atomically reserve conservative daily capacity before provider egress.

        Reservations are intentionally not released after a provider error: the provider may
        have consumed tokens before a timeout, so fail-closed accounting must retain them.
        """
        bind = self._session.get_bind()
        dialect = bind.dialect.name
        values = {
            "tenant_id": tenant_id,
            "usage_day_utc": usage_day_utc,
            "calls_reserved": 0,
            "tokens_reserved": 0,
            "updated_at_utc": datetime.now(UTC),
        }
        if dialect == "postgresql":
            create = postgresql_insert(LLMDailyUsageBudgetDB).values(**values)
            create = create.on_conflict_do_nothing(
                index_elements=["tenant_id", "usage_day_utc"],
            )
        elif dialect == "sqlite":
            create = sqlite_insert(LLMDailyUsageBudgetDB).values(**values)
            create = create.on_conflict_do_nothing(
                index_elements=["tenant_id", "usage_day_utc"],
            )
        else:
            raise RuntimeError(
                "Atomic LLM usage reservations require PostgreSQL or SQLite",
            )
        self._session.execute(create)

        predicates = [
            LLMDailyUsageBudgetDB.tenant_id == tenant_id,
            LLMDailyUsageBudgetDB.usage_day_utc == usage_day_utc,
        ]
        if call_limit:
            predicates.append(LLMDailyUsageBudgetDB.calls_reserved < call_limit)
        if token_limit:
            predicates.append(
                LLMDailyUsageBudgetDB.tokens_reserved + projected_tokens <= token_limit,
            )
        reserve = (
            update(LLMDailyUsageBudgetDB)
            .where(*predicates)
            .values(
                calls_reserved=LLMDailyUsageBudgetDB.calls_reserved + 1,
                tokens_reserved=LLMDailyUsageBudgetDB.tokens_reserved + projected_tokens,
                updated_at_utc=datetime.now(UTC),
            )
        )
        result = self._session.execute(reserve)
        accepted = result.rowcount == 1
        self._session.commit()
        return accepted

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
