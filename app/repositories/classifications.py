from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.classification_models import (
    ClassificationOverrideRequest,
    ClassificationSummary,
    RiskClassification,
    RiskLevel,
)
from app.models_db import RiskClassificationTable


class ClassificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: RiskClassificationTable) -> RiskClassification:
        return RiskClassification(
            ai_system_id=row.ai_system_id,
            risk_level=row.risk_level,
            classification_path=row.classification_path,
            annex_iii_category=row.annex_iii_category,
            annex_i_legislation=row.annex_i_legislation,
            is_safety_component=row.is_safety_component,
            requires_third_party_assessment=row.requires_third_party_assessment,
            exception_applies=row.exception_applies,
            exception_reason=row.exception_reason,
            profiles_natural_persons=row.profiles_natural_persons,
            classification_rationale=row.classification_rationale,
            classified_at=row.classified_at,
            classified_by=row.classified_by,
            confidence_score=row.confidence_score,
        )

    def get_for_system(self, tenant_id: str, ai_system_id: str) -> RiskClassification | None:
        stmt = (
            select(RiskClassificationTable)
            .where(
                RiskClassificationTable.tenant_id == tenant_id,
                RiskClassificationTable.ai_system_id == ai_system_id,
            )
            .order_by(RiskClassificationTable.classified_at.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def save(self, tenant_id: str, classification: RiskClassification) -> RiskClassification:
        row = RiskClassificationTable(
            tenant_id=tenant_id,
            ai_system_id=classification.ai_system_id,
            risk_level=classification.risk_level,
            classification_path=classification.classification_path,
            annex_iii_category=classification.annex_iii_category,
            annex_i_legislation=classification.annex_i_legislation,
            is_safety_component=classification.is_safety_component,
            requires_third_party_assessment=classification.requires_third_party_assessment,
            exception_applies=classification.exception_applies,
            exception_reason=classification.exception_reason,
            profiles_natural_persons=classification.profiles_natural_persons,
            classification_rationale=classification.classification_rationale,
            classified_at=classification.classified_at,
            classified_by=classification.classified_by,
            confidence_score=classification.confidence_score,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def save_override(
        self,
        tenant_id: str,
        ai_system_id: str,
        override: ClassificationOverrideRequest,
        user_id: str,
    ) -> RiskClassification:
        row = RiskClassificationTable(
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            risk_level=override.risk_level,
            classification_path=override.classification_path,
            annex_iii_category=override.annex_iii_category,
            annex_i_legislation=override.annex_i_legislation,
            is_safety_component=False,
            requires_third_party_assessment=False,
            exception_applies=False,
            exception_reason=None,
            profiles_natural_persons=False,
            classification_rationale=f"Manuelle Überschreibung: {override.rationale}",
            classified_at=datetime.now(UTC),
            classified_by=user_id,
            confidence_score=1.0,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def summary_for_tenant(self, tenant_id: str) -> ClassificationSummary:
        """Get count of latest classification per system, grouped by risk level."""
        # Subquery: latest classification per ai_system_id
        latest_subq = (
            select(
                RiskClassificationTable.ai_system_id,
                func.max(RiskClassificationTable.classified_at).label("max_at"),
            )
            .where(RiskClassificationTable.tenant_id == tenant_id)
            .group_by(RiskClassificationTable.ai_system_id)
            .subquery()
        )

        stmt = (
            select(RiskClassificationTable.risk_level, func.count())
            .join(
                latest_subq,
                (RiskClassificationTable.ai_system_id == latest_subq.c.ai_system_id)
                & (RiskClassificationTable.classified_at == latest_subq.c.max_at),
            )
            .where(RiskClassificationTable.tenant_id == tenant_id)
            .group_by(RiskClassificationTable.risk_level)
        )
        rows = self._session.execute(stmt).all()

        summary = ClassificationSummary(tenant_id=tenant_id)
        for level, count in rows:
            if level == RiskLevel.prohibited:
                summary.prohibited = count
            elif level == RiskLevel.high_risk:
                summary.high_risk = count
            elif level == RiskLevel.limited_risk:
                summary.limited_risk = count
            elif level == RiskLevel.minimal_risk:
                summary.minimal_risk = count
        summary.total = summary.prohibited + summary.high_risk + summary.limited_risk + summary.minimal_risk
        return summary
