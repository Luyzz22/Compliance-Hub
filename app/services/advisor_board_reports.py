"""Berater-Sicht: AI-Compliance-Board-Reports nur für verknüpfte Mandanten."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai_compliance_board_report_models import (
    AdvisorBoardReportListRow,
    AdvisorBoardReportsPortfolioResponse,
    AiComplianceBoardReportDetailResponse,
)
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.services.ai_compliance_board_report import get_ai_compliance_board_report_detail

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def list_advisor_portfolio_board_reports(
    session: Session,
    advisor_id: str,
    advisor_repo: AdvisorTenantRepository,
    *,
    limit_per_tenant: int = 30,
) -> AdvisorBoardReportsPortfolioResponse:
    links = advisor_repo.list_for_advisor(advisor_id)
    name_by_tenant = {ln.tenant_id: ln.tenant_display_name for ln in links}
    report_repo = AiComplianceBoardReportRepository(session)
    rows: list[AdvisorBoardReportListRow] = []
    for ln in links:
        for r in report_repo.list_for_tenant(ln.tenant_id, limit=limit_per_tenant):
            rows.append(
                AdvisorBoardReportListRow(
                    tenant_id=r.tenant_id,
                    tenant_display_name=name_by_tenant.get(r.tenant_id),
                    report_id=r.id,
                    title=r.title,
                    audience_type=r.audience_type,
                    created_at=r.created_at_utc.isoformat(),
                )
            )
    rows.sort(key=lambda x: x.created_at, reverse=True)
    return AdvisorBoardReportsPortfolioResponse(advisor_id=advisor_id, reports=rows)


def get_board_report_detail_for_advisor(
    session: Session,
    advisor_id: str,
    tenant_id: str,
    report_id: str,
    advisor_repo: AdvisorTenantRepository,
) -> AiComplianceBoardReportDetailResponse | None:
    if advisor_repo.get_link(advisor_id, tenant_id) is None:
        return None
    return get_ai_compliance_board_report_detail(session, tenant_id, report_id)
