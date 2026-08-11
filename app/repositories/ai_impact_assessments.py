from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai_impact_assessment_models import (
    SECTION_DEFINITIONS,
    AIImpactAssessmentRead,
    AIImpactAssessmentUpsert,
    ImpactAssessmentSectionRead,
    ImpactSectionKey,
    default_impact_sections,
)
from app.models_db import AIImpactAssessmentSectionTable, AIImpactAssessmentTable


class ImpactAssessmentVersionConflict(RuntimeError):
    """Raised when a stale client tries to overwrite a newer assessment."""


class AIImpactAssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _sections_for_assessment(
        self,
        tenant_id: str,
        assessment_id: str,
    ) -> list[AIImpactAssessmentSectionTable]:
        statement = select(AIImpactAssessmentSectionTable).where(
            AIImpactAssessmentSectionTable.tenant_id == tenant_id,
            AIImpactAssessmentSectionTable.assessment_id == assessment_id,
        )
        return list(self._session.scalars(statement).all())

    @staticmethod
    def _to_domain(
        row: AIImpactAssessmentTable,
        section_rows: list[AIImpactAssessmentSectionTable],
    ) -> AIImpactAssessmentRead:
        by_key = {section.section_key: section for section in section_rows}
        sections: list[ImpactAssessmentSectionRead] = []
        for key, definition in SECTION_DEFINITIONS.items():
            stored = by_key.get(key.value)
            if stored is None:
                sections.append(
                    ImpactAssessmentSectionRead(
                        section_key=key,
                        status="not_started",
                        **definition,
                    )
                )
                continue
            sections.append(
                ImpactAssessmentSectionRead(
                    section_key=ImpactSectionKey(stored.section_key),
                    status=stored.status,
                    summary=stored.summary,
                    evidence_reference=stored.evidence_reference,
                    rationale=stored.rationale,
                    updated_at_utc=stored.updated_at_utc,
                    **definition,
                )
            )
        return AIImpactAssessmentRead(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            dpia_scope=row.dpia_scope,
            fria_scope=row.fria_scope,
            deployer_context=row.deployer_context,
            scope_rationale=row.scope_rationale,
            lifecycle_status=row.lifecycle_status,
            residual_risk=row.residual_risk,
            assessment_owner=row.assessment_owner,
            independent_reviewer=row.independent_reviewer,
            dpo_involved=row.dpo_involved,
            stakeholder_views_status=row.stakeholder_views_status,
            prior_consultation_status=row.prior_consultation_status,
            prior_consultation_reference=row.prior_consultation_reference,
            reviewed_at_utc=row.reviewed_at_utc,
            approved_at_utc=row.approved_at_utc,
            review_due_at_utc=row.review_due_at_utc,
            version=row.version,
            sections=sections,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
            updated_by=row.updated_by,
        )

    def get(self, tenant_id: str, ai_system_id: str) -> AIImpactAssessmentRead | None:
        statement = select(AIImpactAssessmentTable).where(
            AIImpactAssessmentTable.tenant_id == tenant_id,
            AIImpactAssessmentTable.ai_system_id == ai_system_id,
        )
        row = self._session.scalar(statement)
        if row is None:
            return None
        return self._to_domain(row, self._sections_for_assessment(tenant_id, row.id))

    def default_for_system(
        self,
        tenant_id: str,
        ai_system_id: str,
    ) -> AIImpactAssessmentRead:
        return AIImpactAssessmentRead(
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            dpia_scope="undetermined",
            fria_scope="undetermined",
            deployer_context="unknown",
            lifecycle_status="draft",
            residual_risk="unknown",
            stakeholder_views_status="not_assessed",
            prior_consultation_status="not_assessed",
            sections=default_impact_sections(),
        )

    def list_for_tenant(self, tenant_id: str) -> dict[str, AIImpactAssessmentRead]:
        rows = list(
            self._session.scalars(
                select(AIImpactAssessmentTable).where(
                    AIImpactAssessmentTable.tenant_id == tenant_id
                )
            ).all()
        )
        if not rows:
            return {}
        assessment_ids = [row.id for row in rows]
        section_rows = list(
            self._session.scalars(
                select(AIImpactAssessmentSectionTable).where(
                    AIImpactAssessmentSectionTable.tenant_id == tenant_id,
                    AIImpactAssessmentSectionTable.assessment_id.in_(assessment_ids),
                )
            ).all()
        )
        sections_by_assessment: dict[str, list[AIImpactAssessmentSectionTable]] = {}
        for section in section_rows:
            sections_by_assessment.setdefault(section.assessment_id, []).append(section)
        return {
            row.ai_system_id: self._to_domain(
                row,
                sections_by_assessment.get(row.id, []),
            )
            for row in rows
        }

    def upsert(
        self,
        tenant_id: str,
        ai_system_id: str,
        payload: AIImpactAssessmentUpsert,
        *,
        actor: str,
        commit: bool = True,
    ) -> AIImpactAssessmentRead:
        now = datetime.now(UTC)
        statement = (
            select(AIImpactAssessmentTable)
            .where(
                AIImpactAssessmentTable.tenant_id == tenant_id,
                AIImpactAssessmentTable.ai_system_id == ai_system_id,
            )
            .with_for_update()
        )
        row = self._session.scalar(statement)
        current_version = row.version if row is not None else 0
        if payload.expected_version != current_version:
            raise ImpactAssessmentVersionConflict(
                f"expected version {payload.expected_version}, current version {current_version}"
            )

        try:
            if row is None:
                row = AIImpactAssessmentTable(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    ai_system_id=ai_system_id,
                    version=1,
                    created_at_utc=now,
                    updated_at_utc=now,
                    updated_by=actor,
                )
                self._session.add(row)
                self._session.flush()
            else:
                row.version += 1
                row.updated_at_utc = now
                row.updated_by = actor

            row.dpia_scope = payload.dpia_scope.value
            row.fria_scope = payload.fria_scope.value
            row.deployer_context = payload.deployer_context.value
            row.scope_rationale = payload.scope_rationale
            row.lifecycle_status = payload.lifecycle_status.value
            row.residual_risk = payload.residual_risk.value
            row.assessment_owner = payload.assessment_owner
            row.independent_reviewer = payload.independent_reviewer
            row.dpo_involved = payload.dpo_involved
            row.stakeholder_views_status = payload.stakeholder_views_status.value
            row.prior_consultation_status = payload.prior_consultation_status.value
            row.prior_consultation_reference = payload.prior_consultation_reference
            row.reviewed_at_utc = payload.reviewed_at_utc
            row.approved_at_utc = payload.approved_at_utc
            row.review_due_at_utc = payload.review_due_at_utc

            existing_sections = {
                section.section_key: section
                for section in self._sections_for_assessment(tenant_id, row.id)
            }
            for section in payload.sections:
                section_row = existing_sections.get(section.section_key.value)
                if section_row is None:
                    section_row = AIImpactAssessmentSectionTable(
                        id=str(uuid4()),
                        assessment_id=row.id,
                        tenant_id=tenant_id,
                        section_key=section.section_key.value,
                    )
                    self._session.add(section_row)
                section_row.status = section.status.value
                section_row.summary = section.summary
                section_row.evidence_reference = section.evidence_reference
                section_row.rationale = section.rationale
                section_row.updated_at_utc = now

            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ImpactAssessmentVersionConflict(
                "assessment was created or updated by another transaction"
            ) from exc

        self._session.refresh(row)
        return self._to_domain(row, self._sections_for_assessment(tenant_id, row.id))
