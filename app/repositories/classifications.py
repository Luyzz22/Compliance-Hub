from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classification_models import ClassificationSummary, RiskClassification
from app.models_db import RiskClassificationDB


class ClassificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, tenant_id: str, classification: RiskClassification) -> RiskClassification:
        row = RiskClassificationDB(
            ai_system_id=classification.ai_system_id,
            risk_level=classification.risk_level,
            classification_path=classification.classification_path,
            annex_i_legislation=classification.annex_i_legislation,
            is_safety_component=classification.is_safety_component,
            requires_third_party_assessment=classification.requires_third_party_assessment,
            annex_iii_category=classification.annex_iii_category,
            profiles_natural_persons=classification.profiles_natural_persons,
            exception_applies=classification.exception_applies,
            exception_reason=classification.exception_reason,
            classification_rationale=classification.classification_rationale,
            confidence_score=classification.confidence_score,
            classified_by=classification.classified_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return classification

    def save_override(
        self,
        tenant_id: str,
        ai_system_id: str,
        override: RiskClassification,
        actor_id: str | None = None,
    ) -> RiskClassification:
        stmt = select(RiskClassificationDB).where(
            RiskClassificationDB.ai_system_id == ai_system_id,
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            return self.save(tenant_id, override)

        row.risk_level = override.risk_level
        row.classification_path = override.classification_path
        row.annex_i_legislation = override.annex_i_legislation
        row.is_safety_component = override.is_safety_component
        row.requires_third_party_assessment = override.requires_third_party_assessment
        row.annex_iii_category = override.annex_iii_category
        row.profiles_natural_persons = override.profiles_natural_persons
        row.exception_applies = override.exception_applies
        row.exception_reason = override.exception_reason
        row.classification_rationale = override.classification_rationale
        row.confidence_score = override.confidence_score
        row.classified_by = override.classified_by
        self.session.commit()
        return override

    def get_for_system(self, tenant_id: str, ai_system_id: str) -> RiskClassification | None:
        stmt = select(RiskClassificationDB).where(
            RiskClassificationDB.ai_system_id == ai_system_id,
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        return RiskClassification(
            ai_system_id=row.ai_system_id,
            risk_level=row.risk_level,
            classification_path=row.classification_path,
            annex_i_legislation=row.annex_i_legislation,
            is_safety_component=row.is_safety_component,
            requires_third_party_assessment=row.requires_third_party_assessment,
            annex_iii_category=row.annex_iii_category,
            profiles_natural_persons=row.profiles_natural_persons,
            exception_applies=row.exception_applies,
            exception_reason=row.exception_reason,
            classification_rationale=row.classification_rationale,
            confidence_score=row.confidence_score,
            classified_by=row.classified_by,
        )

    def summary_for_tenant(self, tenant_id: str) -> ClassificationSummary:
        stmt = select(RiskClassificationDB.risk_level)
        rows = self.session.execute(stmt).scalars().all()
        return ClassificationSummary.from_risk_levels(rows)
