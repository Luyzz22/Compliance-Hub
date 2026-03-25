from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.advisor_portfolio_models import AdvisorPortfolioResponse, AdvisorPortfolioTenantEntry
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.readiness_score_models import ReadinessScoreSummary
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository
from app.services.advisor_client_governance_snapshot import build_governance_brief_for_tenant
from app.services.ai_governance_kpis import compute_ai_governance_kpis
from app.services.compliance_dashboard import compute_ai_compliance_overview
from app.services.readiness_score_service import compute_readiness_score
from app.services.setup_status import compute_tenant_setup_status

logger = logging.getLogger(__name__)


def build_advisor_portfolio(
    session: Session,
    advisor_id: str,
    advisor_repo: AdvisorTenantRepository,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
    nis2_repo: Nis2KritisKpiRepository,
    policy_repo: PolicyRepository,
    violation_repo: ViolationRepository,
    audit_repo: AuditRepository,
    action_repo: AIGovernanceActionRepository,
) -> AdvisorPortfolioResponse:
    links = advisor_repo.list_for_advisor(advisor_id)
    tenants_out: list[AdvisorPortfolioTenantEntry] = []
    now = datetime.now(UTC)

    for link in links:
        tid = link.tenant_id
        overview = compute_ai_compliance_overview(
            tenant_id=tid,
            ai_repo=ai_repo,
            cls_repo=cls_repo,
            gap_repo=gap_repo,
            nis2_kritis_kpi_repository=nis2_repo,
        )
        gov = compute_ai_governance_kpis(
            tenant_id=tid,
            ai_system_repository=ai_repo,
            policy_repository=policy_repo,
            violation_repository=violation_repo,
            audit_repository=audit_repo,
            nis2_kritis_kpi_repository=nis2_repo,
        )
        setup = compute_tenant_setup_status(session, tid)
        open_actions = action_repo.count_open_or_in_progress(tid)
        total_s = max(setup.total_steps, 1)
        setup_ratio = round(setup.completed_steps / total_s, 4)

        brief = None
        if is_feature_enabled(FeatureFlag.advisor_client_snapshot):
            try:
                brief = build_governance_brief_for_tenant(session, tid)
            except Exception:
                logger.exception("advisor_portfolio_governance_brief_failed tenant=%s", tid)
                brief = None

        readiness_summary: ReadinessScoreSummary | None = None
        if is_feature_enabled(FeatureFlag.readiness_score):
            try:
                rs = compute_readiness_score(session, tid)
                readiness_summary = ReadinessScoreSummary(score=rs.score, level=rs.level)
            except Exception:
                logger.exception("advisor_portfolio_readiness_failed tenant=%s", tid)
                readiness_summary = None

        tenants_out.append(
            AdvisorPortfolioTenantEntry(
                tenant_id=tid,
                tenant_name=(link.tenant_display_name or tid).strip() or tid,
                industry=link.industry,
                country=link.country,
                eu_ai_act_readiness=round(overview.overall_readiness, 4),
                nis2_kritis_kpi_mean_percent=overview.nis2_kritis_kpi_mean_percent,
                nis2_kritis_systems_full_coverage_ratio=round(
                    overview.nis2_kritis_systems_full_coverage_ratio,
                    4,
                ),
                high_risk_systems_count=gov.high_risk_total,
                open_governance_actions_count=open_actions,
                setup_completed_steps=setup.completed_steps,
                setup_total_steps=setup.total_steps,
                setup_progress_ratio=setup_ratio,
                governance_brief=brief,
                readiness_summary=readiness_summary,
            ),
        )

    return AdvisorPortfolioResponse(
        advisor_id=advisor_id,
        generated_at_utc=now,
        tenants=tenants_out,
    )


def advisor_portfolio_to_csv(portfolio: AdvisorPortfolioResponse) -> str:
    buf = io.StringIO()
    fieldnames = [
        "tenant_id",
        "tenant_name",
        "industry",
        "country",
        "eu_ai_act_readiness",
        "nis2_kritis_kpi_mean_percent",
        "nis2_kritis_systems_full_coverage_ratio",
        "high_risk_systems_count",
        "open_governance_actions_count",
        "setup_completed_steps",
        "setup_total_steps",
        "setup_progress_ratio",
        "readiness_score",
        "readiness_level",
    ]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for t in portfolio.tenants:
        row = t.model_dump()
        rs = row.get("readiness_summary")
        row["readiness_score"] = rs["score"] if rs else ""
        row["readiness_level"] = rs["level"] if rs else ""
        w.writerow({k: row.get(k) for k in fieldnames})
    return buf.getvalue()


def advisor_portfolio_to_json_bytes(portfolio: AdvisorPortfolioResponse) -> bytes:
    payload = portfolio.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
