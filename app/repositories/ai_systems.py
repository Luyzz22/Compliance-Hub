from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_system_models import AISystem, AISystemCreate, AISystemStatus
from app.models_db import AISystemTable


class AISystemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: AISystemTable) -> AISystem:
        return AISystem(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            business_unit=row.business_unit,
            risk_level=row.risk_level,
            ai_act_category=row.ai_act_category,
            gdpr_dpia_required=row.gdpr_dpia_required,
            owner_email=row.owner_email,
            criticality=row.criticality,
            data_sensitivity=row.data_sensitivity,
            status=row.status,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
        )

    def get_by_id(self, tenant_id: str, aisystem_id: str) -> AISystem | None:
        stmt = select(AISystemTable).where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.id == aisystem_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def list_for_tenant(self, tenant_id: str) -> list[AISystem]:
        stmt = (
            select(AISystemTable)
            .where(AISystemTable.tenant_id == tenant_id)
            .order_by(AISystemTable.created_at_utc.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def compliance_summary_for_tenant(self, tenant_id: str) -> dict[str, object]:
        # Anzahl pro Risk Level
        risk_stmt = (
            select(AISystemTable.risk_level, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.risk_level)
        )
        risk_rows = self._session.execute(risk_stmt).all()
        by_risk_level = [
            {
                "risk_level": risk_level,
                "count": count,
            }
            for risk_level, count in risk_rows
        ]

        # Anzahl pro AI Act Category
        ai_act_stmt = (
            select(AISystemTable.ai_act_category, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.ai_act_category)
        )
        ai_act_rows = self._session.execute(ai_act_stmt).all()
        by_ai_act_category = [
            {
                "ai_act_category": category,
                "count": count,
            }
            for category, count in ai_act_rows
        ]

        # Anzahl pro Criticality
        criticality_stmt = (
            select(AISystemTable.criticality, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.criticality)
        )
        criticality_rows = self._session.execute(criticality_stmt).all()
        by_criticality = [
            {
                "criticality": criticality,
                "count": count,
            }
            for criticality, count in criticality_rows
        ]

        # Anzahl pro Data Sensitivity
        data_sensitivity_stmt = (
            select(AISystemTable.data_sensitivity, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.data_sensitivity)
        )
        data_sensitivity_rows = self._session.execute(data_sensitivity_stmt).all()
        by_data_sensitivity = [
            {
                "data_sensitivity": sensitivity,
                "count": count,
            }
            for sensitivity, count in data_sensitivity_rows
        ]

        total = sum(item["count"] for item in by_risk_level)

        return {
            "tenant_id": tenant_id,
            "total_systems": total,
            "by_risk_level": by_risk_level,
            "by_ai_act_category": by_ai_act_category,
            "by_criticality": by_criticality,
            "by_data_sensitivity": by_data_sensitivity,
        }


        # Anzahl pro Risk Level
        risk_stmt = (
            select(AISystemTable.risk_level, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.risk_level)
        )
        risk_rows = self._session.execute(risk_stmt).all()
        by_risk_level = [
            {
                "risk_level": risk_level,
                "count": count,
            }
            for risk_level, count in risk_rows
        ]

        # Anzahl pro AI Act Category
        ai_act_stmt = (
            select(AISystemTable.ai_act_category, func.count())
            .where(AISystemTable.tenant_id == tenant_id)
            .group_by(AISystemTable.ai_act_category)
        )
        ai_act_rows = self._session.execute(ai_act_stmt).all()
        by_ai_act_category = [
            {
                "ai_act_category": category,
                "count": count,
            }
            for category, count in ai_act_rows
        ]

        total = sum(item["count"] for item in by_risk_level)

        return {
            "tenant_id": tenant_id,
            "total_systems": total,
            "by_risk_level": by_risk_level,
            "by_ai_act_category": by_ai_act_category,
        }

    def create(self, tenant_id: str, payload: AISystemCreate) -> AISystem:
        now = datetime.now(UTC)
        row = AISystemTable(
            id=payload.id,
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            business_unit=payload.business_unit,
            risk_level=payload.risk_level,
            ai_act_category=payload.ai_act_category,
            gdpr_dpia_required=payload.gdpr_dpia_required,
            owner_email=str(payload.owner_email),
            criticality=payload.criticality,
            data_sensitivity=payload.data_sensitivity,
            status=AISystemStatus.draft,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def update_status(
        self,
        tenant_id: str,
        aisystem_id: str,
        new_status: AISystemStatus,
    ) -> AISystem:
        stmt = select(AISystemTable).where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.id == aisystem_id,
        )
        row = self._session.execute(stmt).scalar_one()
        row.status = new_status
        row.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

