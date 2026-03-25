from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import AdvisorTenantDB


class AdvisorTenantLink:
    __slots__ = ("advisor_id", "tenant_id", "tenant_display_name", "industry", "country")

    def __init__(
        self,
        *,
        advisor_id: str,
        tenant_id: str,
        tenant_display_name: str | None,
        industry: str | None,
        country: str | None,
    ) -> None:
        self.advisor_id = advisor_id
        self.tenant_id = tenant_id
        self.tenant_display_name = tenant_display_name
        self.industry = industry
        self.country = country


class AdvisorTenantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_advisor(self, advisor_id: str) -> list[AdvisorTenantLink]:
        stmt = (
            select(AdvisorTenantDB)
            .where(AdvisorTenantDB.advisor_id == advisor_id)
            .order_by(AdvisorTenantDB.tenant_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            AdvisorTenantLink(
                advisor_id=r.advisor_id,
                tenant_id=r.tenant_id,
                tenant_display_name=r.tenant_display_name,
                industry=r.industry,
                country=r.country,
            )
            for r in rows
        ]

    def upsert_link(
        self,
        *,
        advisor_id: str,
        tenant_id: str,
        tenant_display_name: str | None = None,
        industry: str | None = None,
        country: str | None = None,
    ) -> AdvisorTenantLink:
        """Hilfsmethode für Tests/Seeding (idempotent pro advisor_id+tenant_id)."""
        stmt = select(AdvisorTenantDB).where(
            AdvisorTenantDB.advisor_id == advisor_id,
            AdvisorTenantDB.tenant_id == tenant_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = AdvisorTenantDB(
                advisor_id=advisor_id,
                tenant_id=tenant_id,
                tenant_display_name=tenant_display_name,
                industry=industry,
                country=country,
            )
            self._session.add(row)
        else:
            row.tenant_display_name = tenant_display_name
            row.industry = industry
            row.country = country
        self._session.commit()
        self._session.refresh(row)
        return AdvisorTenantLink(
            advisor_id=row.advisor_id,
            tenant_id=row.tenant_id,
            tenant_display_name=row.tenant_display_name,
            industry=row.industry,
            country=row.country,
        )
