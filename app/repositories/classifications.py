from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification_models import RiskLevel
from app.models_db import RiskClassificationDB


class ClassificationSummary:
    prohibited: int = 0
    high_risk: int = 0
    limited_risk: int = 0
    minimal_risk: int = 0
    total: int = 0


async def get_classification_summary(
    session: AsyncSession,
    ai_system_ids: Iterable[str],
) -> ClassificationSummary:
    stmt = select(
        RiskClassificationDB.risk_level,
        RiskClassificationDB.id,
    ).where(RiskClassificationDB.ai_system_id.in_(list(ai_system_ids)))
    result = await session.execute(stmt)
    rows = result.fetchall()

    summary = ClassificationSummary()
    for level, _ in rows:
        if level == RiskLevel.prohibited:
            summary.prohibited += 1
        elif level == RiskLevel.high_risk:
            summary.high_risk += 1
        elif level == RiskLevel.limited_risk:
            summary.limited_risk += 1
        elif level == RiskLevel.minimal_risk:
            summary.minimal_risk += 1

    summary.total = (
        summary.prohibited
        + summary.high_risk
        + summary.limited_risk
        + summary.minimal_risk
    )
    return summary
