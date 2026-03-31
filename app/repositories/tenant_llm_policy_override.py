from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import TenantLLMPolicyOverrideDB


class TenantLLMPolicyOverrideRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_policy_json(self, tenant_id: str) -> str | None:
        stmt = select(TenantLLMPolicyOverrideDB.policy_json).where(
            TenantLLMPolicyOverrideDB.tenant_id == tenant_id,
        )
        raw = self._session.execute(stmt).scalar_one_or_none()
        return str(raw) if raw is not None else None

    def get_partial_dict(self, tenant_id: str) -> dict | None:
        raw = self.get_policy_json(tenant_id)
        if raw is None or not raw.strip():
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
