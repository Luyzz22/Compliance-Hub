from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai_transparency_assurance_models import (
    CONTROL_DEFINITIONS,
    AITransparencyAssessmentRead,
    AITransparencyAssessmentUpsert,
    TransparencyControlKey,
    TransparencyControlRead,
    default_transparency_controls,
)
from app.models_db import AITransparencyAssessmentTable, AITransparencyControlTable


class TransparencyAssessmentVersionConflict(RuntimeError):
    """Raised when a stale browser attempts to overwrite a newer assessment."""


class AITransparencyAssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _controls_for_assessment(
        self,
        tenant_id: str,
        assessment_id: str,
    ) -> list[AITransparencyControlTable]:
        stmt = select(AITransparencyControlTable).where(
            AITransparencyControlTable.tenant_id == tenant_id,
            AITransparencyControlTable.assessment_id == assessment_id,
        )
        return list(self._session.scalars(stmt).all())

    @staticmethod
    def _to_domain(
        row: AITransparencyAssessmentTable,
        control_rows: list[AITransparencyControlTable],
    ) -> AITransparencyAssessmentRead:
        by_key = {control.control_key: control for control in control_rows}
        controls: list[TransparencyControlRead] = []
        for key, definition in CONTROL_DEFINITIONS.items():
            stored = by_key.get(key.value)
            if stored is None:
                controls.append(
                    TransparencyControlRead(
                        control_key=key,
                        status="not_assessed",
                        **definition,
                    )
                )
                continue
            controls.append(
                TransparencyControlRead(
                    control_key=TransparencyControlKey(stored.control_key),
                    status=stored.status,
                    evidence_reference=stored.evidence_reference,
                    rationale=stored.rationale,
                    updated_at_utc=stored.updated_at_utc,
                    **definition,
                )
            )
        return AITransparencyAssessmentRead(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            role_scope=row.role_scope,
            control_owner=row.control_owner,
            reviewer=row.reviewer,
            reviewed_at_utc=row.reviewed_at_utc,
            review_due_at_utc=row.review_due_at_utc,
            version=row.version,
            controls=controls,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
            updated_by=row.updated_by,
        )

    def get(
        self,
        tenant_id: str,
        ai_system_id: str,
    ) -> AITransparencyAssessmentRead | None:
        stmt = select(AITransparencyAssessmentTable).where(
            AITransparencyAssessmentTable.tenant_id == tenant_id,
            AITransparencyAssessmentTable.ai_system_id == ai_system_id,
        )
        row = self._session.scalar(stmt)
        if row is None:
            return None
        return self._to_domain(row, self._controls_for_assessment(tenant_id, row.id))

    def default_for_system(
        self,
        tenant_id: str,
        ai_system_id: str,
    ) -> AITransparencyAssessmentRead:
        return AITransparencyAssessmentRead(
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            role_scope="unknown",
            controls=default_transparency_controls(),
        )

    def list_for_tenant(self, tenant_id: str) -> dict[str, AITransparencyAssessmentRead]:
        rows = list(
            self._session.scalars(
                select(AITransparencyAssessmentTable).where(
                    AITransparencyAssessmentTable.tenant_id == tenant_id
                )
            ).all()
        )
        if not rows:
            return {}
        assessment_ids = [row.id for row in rows]
        controls = list(
            self._session.scalars(
                select(AITransparencyControlTable).where(
                    AITransparencyControlTable.tenant_id == tenant_id,
                    AITransparencyControlTable.assessment_id.in_(assessment_ids),
                )
            ).all()
        )
        controls_by_assessment: dict[str, list[AITransparencyControlTable]] = {}
        for control in controls:
            controls_by_assessment.setdefault(control.assessment_id, []).append(control)
        return {
            row.ai_system_id: self._to_domain(row, controls_by_assessment.get(row.id, []))
            for row in rows
        }

    def upsert(
        self,
        tenant_id: str,
        ai_system_id: str,
        payload: AITransparencyAssessmentUpsert,
        *,
        actor: str,
        commit: bool = True,
    ) -> AITransparencyAssessmentRead:
        now = datetime.now(UTC)
        stmt = (
            select(AITransparencyAssessmentTable)
            .where(
                AITransparencyAssessmentTable.tenant_id == tenant_id,
                AITransparencyAssessmentTable.ai_system_id == ai_system_id,
            )
            .with_for_update()
        )
        row = self._session.scalar(stmt)
        current_version = row.version if row is not None else 0
        if payload.expected_version != current_version:
            raise TransparencyAssessmentVersionConflict(
                f"expected version {payload.expected_version}, current version {current_version}"
            )

        try:
            if row is None:
                row = AITransparencyAssessmentTable(
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

            row.role_scope = payload.role_scope.value
            row.control_owner = payload.control_owner
            row.reviewer = payload.reviewer
            row.reviewed_at_utc = payload.reviewed_at_utc
            row.review_due_at_utc = payload.review_due_at_utc

            existing_controls = {
                control.control_key: control
                for control in self._controls_for_assessment(tenant_id, row.id)
            }
            for control in payload.controls:
                control_row = existing_controls.get(control.control_key.value)
                if control_row is None:
                    control_row = AITransparencyControlTable(
                        id=str(uuid4()),
                        assessment_id=row.id,
                        tenant_id=tenant_id,
                        control_key=control.control_key.value,
                    )
                    self._session.add(control_row)
                control_row.status = control.status.value
                control_row.evidence_reference = control.evidence_reference
                control_row.rationale = control.rationale
                control_row.updated_at_utc = now

            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise TransparencyAssessmentVersionConflict(
                "assessment was created or updated by another transaction"
            ) from exc

        self._session.refresh(row)
        return self._to_domain(row, self._controls_for_assessment(tenant_id, row.id))
