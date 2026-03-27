from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.advisor_governance_maturity_brief_models import (
    AdvisorGovernanceMaturityBrief,
    merge_recommended_focus_areas_runtime_safety,
)
from app.advisor_portfolio_models import (
    AdvisorPortfolioResponse,
    AdvisorPortfolioTenantEntry,
    GovernanceActivityPortfolioSummary,
    IncidentBurdenLevel,
    Nis2EntityCategory,
    OperationalMonitoringPortfolioSummary,
)
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.readiness_score_models import ReadinessScoreSummary
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.tenant_registry import TenantRegistryRepository
from app.repositories.violations import ViolationRepository
from app.services.advisor_client_governance_snapshot import build_governance_brief_for_tenant
from app.services.advisor_governance_maturity_brief_llm import (
    maybe_build_advisor_governance_maturity_brief_result,
)
from app.services.advisor_portfolio_priority import (
    advisor_portfolio_priority_sort_key,
    advisor_priority_explanation_de,
    apply_regulatory_priority_adjustment,
    compute_advisor_priority_bucket,
    compute_incident_burden_level,
    derive_primary_focus_tag_de,
    effective_readiness_level,
    infer_maturity_scenario_hint,
    normalize_nis2_entity_category,
)
from app.services.ai_governance_kpis import compute_ai_governance_kpis
from app.services.compliance_dashboard import compute_ai_compliance_overview
from app.services.governance_maturity_service import build_governance_maturity_response
from app.services.readiness_score_service import compute_readiness_score
from app.services.setup_status import compute_tenant_setup_status

logger = logging.getLogger(__name__)


def _portfolio_priority_fields(
    *,
    readiness_summary: ReadinessScoreSummary | None,
    eu_ai_act_readiness: float,
    gai_summary: GovernanceActivityPortfolioSummary | None,
    oami_summary: OperationalMonitoringPortfolioSummary | None,
    gm_brief: AdvisorGovernanceMaturityBrief | None,
    nis2_entity_category: Nis2EntityCategory,
    kritis_sector_key: str | None,
    recent_incidents_90d: bool,
    incident_burden_level: IncidentBurdenLevel,
) -> dict[str, object]:
    """Priorität, Szenario, Schwerpunkt; optional NIS2/KRITIS/Incident-Aufstock."""
    rd_level = effective_readiness_level(readiness_summary, eu_ai_act_readiness)
    gai_lv = gai_summary.level if gai_summary else None
    oami_lv = oami_summary.level if oami_summary and oami_summary.level is not None else None

    if gai_summary is None and oami_summary is None:
        primary = derive_primary_focus_tag_de(
            gm_brief,
            readiness_level=rd_level,
            gai_level=None,
            oami_level=None,
        )
        base_expl = (
            "Keine GAI/OAMI-Kennzahlen verfügbar; Priorität standardmäßig „mittel“. "
            "Hauptschwerpunkt aus Kontext geschätzt."
        )
        bucket, expl = apply_regulatory_priority_adjustment(
            "medium",
            base_expl,
            readiness_level=rd_level,
            oami_level=oami_lv,
            nis2_category=nis2_entity_category,
            kritis_sector_key=kritis_sector_key,
            recent_incidents_90d=recent_incidents_90d,
            incident_burden=incident_burden_level,
        )
        return {
            "advisor_priority": bucket,
            "advisor_priority_sort_key": advisor_portfolio_priority_sort_key(bucket),
            "advisor_priority_explanation_de": expl,
            "maturity_scenario_hint": None,
            "primary_focus_tag_de": primary,
        }

    scenario = infer_maturity_scenario_hint(rd_level, gai_lv, oami_lv)
    bucket = compute_advisor_priority_bucket(rd_level, gai_lv, oami_lv, scenario)
    primary = derive_primary_focus_tag_de(
        gm_brief,
        readiness_level=rd_level,
        gai_level=gai_lv,
        oami_level=oami_lv,
    )
    explanation = advisor_priority_explanation_de(bucket, scenario, primary)
    bucket2, expl2 = apply_regulatory_priority_adjustment(
        bucket,
        explanation,
        readiness_level=rd_level,
        oami_level=oami_lv,
        nis2_category=nis2_entity_category,
        kritis_sector_key=kritis_sector_key,
        recent_incidents_90d=recent_incidents_90d,
        incident_burden=incident_burden_level,
    )
    return {
        "advisor_priority": bucket2,
        "advisor_priority_sort_key": advisor_portfolio_priority_sort_key(bucket2),
        "advisor_priority_explanation_de": expl2,
        "maturity_scenario_hint": scenario,
        "primary_focus_tag_de": primary,
    }


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
    incident_repo: IncidentRepository,
) -> AdvisorPortfolioResponse:
    links = advisor_repo.list_for_advisor(advisor_id)
    tenants_out: list[AdvisorPortfolioTenantEntry] = []
    now = datetime.now(UTC)
    treg = TenantRegistryRepository(session)

    for link in links:
        tid = link.tenant_id
        trow = treg.get_by_id(tid)
        nis2_cat = normalize_nis2_entity_category(trow.nis2_scope if trow else None)
        kritis_key = (
            trow.kritis_sector.strip()
            if trow and trow.kritis_sector and str(trow.kritis_sector).strip()
            else None
        )
        c90 = incident_repo.count_created_since_days(tid, days=90)
        h90 = incident_repo.count_high_severity_since_days(tid, days=90)
        burden: IncidentBurdenLevel = compute_incident_burden_level(c90, h90)
        recent = c90 > 0
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

        gai_summary: GovernanceActivityPortfolioSummary | None = None
        oami_summary: OperationalMonitoringPortfolioSummary | None = None
        gm_brief = None
        if is_feature_enabled(FeatureFlag.governance_maturity):
            try:
                gm = build_governance_maturity_response(session, tid, window_days=90)
                ga = gm.governance_activity
                gai_summary = GovernanceActivityPortfolioSummary(
                    index=ga.index,
                    level=ga.level,
                )
                ob = gm.operational_ai_monitoring
                if ob.status == "active" and ob.level is not None:
                    oami_summary = OperationalMonitoringPortfolioSummary(
                        index=ob.index,
                        level=ob.level,
                        safety_related_runtime_incidents_90d=ob.safety_related_runtime_incident_count,
                        availability_runtime_incidents_90d=ob.availability_runtime_incident_count,
                        oami_operational_hint_de=ob.operational_subtype_hint_de,
                    )
            except Exception:
                logger.exception("advisor_portfolio_governance_maturity_failed tenant=%s", tid)
                gai_summary = None
                oami_summary = None
            try:
                br = maybe_build_advisor_governance_maturity_brief_result(session, tid)
                if br is not None:
                    gm_brief = br.brief
                    safety_ct = (
                        int(oami_summary.safety_related_runtime_incidents_90d)
                        if oami_summary is not None
                        else 0
                    )
                    gm_brief = merge_recommended_focus_areas_runtime_safety(gm_brief, safety_ct)
            except Exception:
                logger.exception(
                    "advisor_portfolio_governance_maturity_brief_failed tenant=%s",
                    tid,
                )
                gm_brief = None

        eu_rd = round(overview.overall_readiness, 4)
        pri = _portfolio_priority_fields(
            readiness_summary=readiness_summary,
            eu_ai_act_readiness=eu_rd,
            gai_summary=gai_summary,
            oami_summary=oami_summary,
            gm_brief=gm_brief,
            nis2_entity_category=nis2_cat,
            kritis_sector_key=kritis_key,
            recent_incidents_90d=recent,
            incident_burden_level=burden,
        )

        tenants_out.append(
            AdvisorPortfolioTenantEntry(
                tenant_id=tid,
                tenant_name=(link.tenant_display_name or tid).strip() or tid,
                industry=link.industry,
                country=link.country,
                nis2_entity_category=nis2_cat,
                kritis_sector_key=kritis_key,
                recent_incidents_90d=recent,
                incident_burden_level=burden,
                eu_ai_act_readiness=eu_rd,
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
                governance_activity_summary=gai_summary,
                operational_monitoring_summary=oami_summary,
                governance_maturity_advisor_brief=gm_brief,
                advisor_priority=pri["advisor_priority"],  # type: ignore[arg-type]
                advisor_priority_sort_key=int(pri["advisor_priority_sort_key"]),
                advisor_priority_explanation_de=str(pri["advisor_priority_explanation_de"]),
                maturity_scenario_hint=pri["maturity_scenario_hint"],  # type: ignore[arg-type]
                primary_focus_tag_de=str(pri["primary_focus_tag_de"]),
            ),
        )

    tenants_out.sort(key=lambda t: (t.advisor_priority_sort_key, t.tenant_name.lower()))

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
        "nis2_entity_category",
        "kritis_sector_key",
        "recent_incidents_90d",
        "incident_burden_level",
        "eu_ai_act_readiness",
        "nis2_kritis_kpi_mean_percent",
        "nis2_kritis_systems_full_coverage_ratio",
        "high_risk_systems_count",
        "open_governance_actions_count",
        "setup_completed_steps",
        "setup_total_steps",
        "setup_progress_ratio",
        "advisor_priority",
        "advisor_priority_sort_key",
        "advisor_priority_explanation_de",
        "maturity_scenario_hint",
        "primary_focus_tag_de",
        "readiness_score",
        "readiness_level",
        "gai_index",
        "gai_level",
        "oami_index",
        "oami_level",
        "governance_maturity_overall_level",
        "governance_maturity_focus_1",
        "governance_maturity_next_window",
    ]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for t in portfolio.tenants:
        row: dict[str, object] = {}
        d = t.model_dump(mode="python")
        for k in (
            "tenant_id",
            "tenant_name",
            "industry",
            "country",
            "nis2_entity_category",
            "kritis_sector_key",
            "recent_incidents_90d",
            "incident_burden_level",
            "eu_ai_act_readiness",
            "nis2_kritis_kpi_mean_percent",
            "nis2_kritis_systems_full_coverage_ratio",
            "high_risk_systems_count",
            "open_governance_actions_count",
            "setup_completed_steps",
            "setup_total_steps",
            "setup_progress_ratio",
            "advisor_priority",
            "advisor_priority_sort_key",
            "advisor_priority_explanation_de",
            "maturity_scenario_hint",
            "primary_focus_tag_de",
        ):
            row[k] = d.get(k, "")
        rs = d.get("readiness_summary")
        row["readiness_score"] = rs["score"] if rs else ""
        row["readiness_level"] = rs["level"] if rs else ""
        ga = d.get("governance_activity_summary")
        om = d.get("operational_monitoring_summary")
        row["gai_index"] = ga["index"] if ga else ""
        row["gai_level"] = ga["level"] if ga else ""
        row["oami_index"] = om["index"] if om and om.get("index") is not None else ""
        row["oami_level"] = om["level"] if om and om.get("level") is not None else ""
        gmb = d.get("governance_maturity_advisor_brief")
        if gmb:
            gms = gmb.get("governance_maturity_summary") or {}
            oa = gms.get("overall_assessment") or {}
            row["governance_maturity_overall_level"] = oa.get("level", "")
            areas = gmb.get("recommended_focus_areas") or []
            row["governance_maturity_focus_1"] = areas[0] if areas else ""
            row["governance_maturity_next_window"] = gmb.get("suggested_next_steps_window", "")
        else:
            row["governance_maturity_overall_level"] = ""
            row["governance_maturity_focus_1"] = ""
            row["governance_maturity_next_window"] = ""
        w.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


def advisor_portfolio_to_json_bytes(portfolio: AdvisorPortfolioResponse) -> bytes:
    payload = portfolio.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
