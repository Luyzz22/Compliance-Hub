from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai_inventory_models import (
    AISystemInventoryProfileRead,
    AISystemInventoryProfileUpsert,
    KIRegisterEntryRead,
    KIRegisterEntryUpsert,
    KIRegisterPostureSummary,
    KiRegisterStatus,
)
from app.models_db import AIRegisterEntryDB, AISystemInventoryProfileDB


class AISystemInventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_profile(row: AISystemInventoryProfileDB) -> AISystemInventoryProfileRead:
        return AISystemInventoryProfileRead(
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            provider_name=row.provider_name,
            provider_type=row.provider_type,
            use_case=row.use_case,
            business_process=row.business_process,
            eu_ai_act_scope=row.eu_ai_act_scope,
            iso_42001_scope=row.iso_42001_scope,
            nis2_scope=row.nis2_scope,
            dsgvo_special_risk=row.dsgvo_special_risk,
            register_status=row.register_status,
            register_metadata=dict(row.register_metadata or {}),
            authority_reporting_flags=dict(row.authority_reporting_flags or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    def get_profile(self, tenant_id: str, ai_system_id: str) -> AISystemInventoryProfileRead | None:
        row = self._session.get(AISystemInventoryProfileDB, (tenant_id, ai_system_id))
        if row is None:
            return None
        return self._to_profile(row)

    def upsert_profile(
        self,
        tenant_id: str,
        ai_system_id: str,
        payload: AISystemInventoryProfileUpsert,
        actor: str,
    ) -> AISystemInventoryProfileRead:
        now = datetime.now(UTC)
        row = self._session.get(AISystemInventoryProfileDB, (tenant_id, ai_system_id))
        data = payload.model_dump()
        if row is None:
            row = AISystemInventoryProfileDB(
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                created_at=now,
                updated_at=now,
                created_by=actor,
                updated_by=actor,
                **data,
            )
            self._session.add(row)
        else:
            for k, v in data.items():
                setattr(row, k, v)
            row.updated_at = now
            row.updated_by = actor
        self._session.commit()
        self._session.refresh(row)
        return self._to_profile(row)

    @staticmethod
    def _to_register(row: AIRegisterEntryDB) -> KIRegisterEntryRead:
        return KIRegisterEntryRead(
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            version=row.version,
            status=row.status,
            authority_name=row.authority_name,
            national_register_id=row.national_register_id,
            reportable_incident=row.reportable_incident,
            reportable_change=row.reportable_change,
            fields=dict(row.fields_json or {}),
            created_at=row.created_at,
            created_by=row.created_by,
        )

    def upsert_register_entry(
        self,
        tenant_id: str,
        ai_system_id: str,
        payload: KIRegisterEntryUpsert,
        actor: str,
    ) -> KIRegisterEntryRead:
        latest = self.get_latest_register_entry(tenant_id, ai_system_id)
        next_version = (latest.version + 1) if latest else 1
        row = AIRegisterEntryDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            version=next_version,
            status=payload.status.value,
            authority_name=payload.authority_name,
            national_register_id=payload.national_register_id,
            reportable_incident=payload.reportable_incident,
            reportable_change=payload.reportable_change,
            fields_json=payload.fields,
            created_at=datetime.now(UTC),
            created_by=actor,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_register(row)

    def get_latest_register_entry(
        self,
        tenant_id: str,
        ai_system_id: str,
    ) -> KIRegisterEntryRead | None:
        stmt = (
            select(AIRegisterEntryDB)
            .where(
                AIRegisterEntryDB.tenant_id == tenant_id,
                AIRegisterEntryDB.ai_system_id == ai_system_id,
            )
            .order_by(desc(AIRegisterEntryDB.version))
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_register(row)

    def list_latest_register_entries(self, tenant_id: str) -> list[KIRegisterEntryRead]:
        sub = (
            select(
                AIRegisterEntryDB.ai_system_id,
                func.max(AIRegisterEntryDB.version).label("max_version"),
            )
            .where(AIRegisterEntryDB.tenant_id == tenant_id)
            .group_by(AIRegisterEntryDB.ai_system_id)
            .subquery()
        )
        stmt = (
            select(AIRegisterEntryDB)
            .join(
                sub,
                (AIRegisterEntryDB.ai_system_id == sub.c.ai_system_id)
                & (AIRegisterEntryDB.version == sub.c.max_version),
            )
            .where(AIRegisterEntryDB.tenant_id == tenant_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_register(r) for r in rows]

    def posture_summary(self, tenant_id: str, total_systems: int) -> KIRegisterPostureSummary:
        entries = self.list_latest_register_entries(tenant_id)
        counts = {
            KiRegisterStatus.registered.value: 0,
            KiRegisterStatus.planned.value: 0,
            "partial": 0,
        }
        for e in entries:
            if e.status in counts:
                counts[e.status] += 1
            elif e.status == KiRegisterStatus.partial.value:
                counts["partial"] += 1
        known = (
            counts[KiRegisterStatus.registered.value]
            + counts[KiRegisterStatus.planned.value]
            + counts["partial"]
        )
        return KIRegisterPostureSummary(
            registered=counts[KiRegisterStatus.registered.value],
            planned=counts[KiRegisterStatus.planned.value],
            partial=counts["partial"],
            unknown=max(total_systems - known, 0),
        )
