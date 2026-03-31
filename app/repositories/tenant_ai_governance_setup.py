"""Repository: tenant_ai_governance_setup."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models_db import TenantAIGovernanceSetupDB


class TenantAIGovernanceSetupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_payload(self, tenant_id: str) -> dict | None:
        row = self._session.get(TenantAIGovernanceSetupDB, tenant_id)
        if row is None:
            return None
        return dict(row.payload) if row.payload else {}

    def upsert_payload(self, tenant_id: str, payload: dict) -> None:
        now = datetime.now(UTC)
        row = self._session.get(TenantAIGovernanceSetupDB, tenant_id)
        if row is None:
            row = TenantAIGovernanceSetupDB(
                tenant_id=tenant_id,
                payload=payload,
                updated_at_utc=now,
            )
            self._session.add(row)
        else:
            row.payload = payload
            row.updated_at_utc = now
        self._session.commit()
