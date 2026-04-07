from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enterprise_integration_blueprint_models import (
    EnterpriseIntegrationBlueprintRow,
    EnterpriseIntegrationBlueprintUpsert,
)
from app.models_db import EnterpriseIntegrationBlueprintDB


class EnterpriseIntegrationBlueprintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_tenant(self, tenant_id: str) -> list[EnterpriseIntegrationBlueprintRow]:
        stmt = (
            select(EnterpriseIntegrationBlueprintDB)
            .where(EnterpriseIntegrationBlueprintDB.tenant_id == tenant_id)
            .order_by(EnterpriseIntegrationBlueprintDB.source_system_type.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        out: list[EnterpriseIntegrationBlueprintRow] = []
        for row in rows:
            payload = EnterpriseIntegrationBlueprintUpsert.model_validate(row.payload)
            out.append(
                EnterpriseIntegrationBlueprintRow(
                    blueprint_id=row.blueprint_id,
                    tenant_id=row.tenant_id,
                    source_system_type=payload.source_system_type,
                    evidence_domains=payload.evidence_domains,
                    onboarding_readiness_ref=payload.onboarding_readiness_ref,
                    security_prerequisites=payload.security_prerequisites,
                    data_owner=payload.data_owner,
                    technical_owner=payload.technical_owner,
                    integration_status=payload.integration_status,
                    blockers=payload.blockers,
                    notes=payload.notes,
                    created_at_utc=row.created_at_utc,
                    updated_at_utc=row.updated_at_utc,
                    updated_by=row.updated_by,
                )
            )
        return out

    def upsert(
        self,
        tenant_id: str,
        body: EnterpriseIntegrationBlueprintUpsert,
        actor: str,
    ) -> EnterpriseIntegrationBlueprintRow:
        stmt = select(EnterpriseIntegrationBlueprintDB).where(
            EnterpriseIntegrationBlueprintDB.tenant_id == tenant_id,
            EnterpriseIntegrationBlueprintDB.blueprint_id == body.blueprint_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        now = datetime.now(UTC)
        if row is None:
            row = EnterpriseIntegrationBlueprintDB(
                tenant_id=tenant_id,
                blueprint_id=body.blueprint_id,
                source_system_type=body.source_system_type.value,
                payload=body.model_dump(mode="json"),
                created_at_utc=now,
                updated_at_utc=now,
                updated_by=actor,
            )
            self._session.add(row)
        else:
            row.source_system_type = body.source_system_type.value
            row.payload = body.model_dump(mode="json")
            row.updated_at_utc = now
            row.updated_by = actor
        self._session.commit()
        self._session.refresh(row)
        return EnterpriseIntegrationBlueprintRow(
            blueprint_id=row.blueprint_id,
            tenant_id=row.tenant_id,
            source_system_type=body.source_system_type,
            evidence_domains=body.evidence_domains,
            onboarding_readiness_ref=body.onboarding_readiness_ref,
            security_prerequisites=body.security_prerequisites,
            data_owner=body.data_owner,
            technical_owner=body.technical_owner,
            integration_status=body.integration_status,
            blockers=body.blockers,
            notes=body.notes,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
            updated_by=row.updated_by,
        )
