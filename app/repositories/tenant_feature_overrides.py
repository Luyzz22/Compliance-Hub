from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import TenantFeatureFlagOverrideDB


class TenantFeatureOverrideRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_override(self, tenant_id: str, flag_key: str) -> bool | None:
        stmt = select(TenantFeatureFlagOverrideDB).where(
            TenantFeatureFlagOverrideDB.tenant_id == tenant_id,
            TenantFeatureFlagOverrideDB.flag_key == flag_key,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return bool(row.enabled)

    def set_override(self, *, tenant_id: str, flag_key: str, enabled: bool) -> None:
        stmt = select(TenantFeatureFlagOverrideDB).where(
            TenantFeatureFlagOverrideDB.tenant_id == tenant_id,
            TenantFeatureFlagOverrideDB.flag_key == flag_key,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = TenantFeatureFlagOverrideDB(
                tenant_id=tenant_id,
                flag_key=flag_key,
                enabled=enabled,
            )
            self._session.add(row)
        else:
            row.enabled = enabled
        self._session.commit()

    def set_many(self, tenant_id: str, flags: dict[str, bool]) -> None:
        for k, v in flags.items():
            self.set_override(tenant_id=tenant_id, flag_key=k, enabled=v)

    def list_for_tenant(self, tenant_id: str) -> dict[str, bool]:
        stmt = select(TenantFeatureFlagOverrideDB).where(
            TenantFeatureFlagOverrideDB.tenant_id == tenant_id,
        )
        rows = self._session.execute(stmt).scalars().all()
        return {r.flag_key: bool(r.enabled) for r in rows}
