"""Assembler: Mandanten-Governance-Snapshot für verknüpfte Berater."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.advisor_client_snapshot_models import (
    AdvisorClientGovernanceSnapshotResponse,
    AdvisorGovernanceSnapshotMarkdownResponse,
    AdvisorTenantGovernanceBrief,
    AiSystemsSummarySnapshot,
    ClientInfoSnapshot,
    CrossRegFrameworkSnapshot,
    FrameworkScopeSnapshot,
    GapAssistSnapshot,
    KpiSummarySnapshot,
    OperationalAiMonitoringSnapshot,
    ReportsSummarySnapshot,
    SetupStatusSnapshot,
)
from app.ai_kpi_models import AiKpiSummaryResponse
from app.ai_system_models import AISystemCriticality, AISystemRiskLevel
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm_models import LLMTaskType
from app.readiness_score_models import ReadinessScoreResponse
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.tenant_ai_governance_setup import TenantAIGovernanceSetupRepository
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services.ai_kpi_service import build_ai_kpi_summary
from app.services.cross_regulation import build_cross_regulation_summary
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps
from app.services.llm_router import LLMRouter
from app.services.oami_explanation import explain_tenant_oami_de
from app.services.operational_monitoring_index import compute_tenant_operational_monitoring_index
from app.services.readiness_score_service import compute_readiness_score
from app.services.setup_status import compute_tenant_setup_status
from app.services.tenant_ai_governance_setup import build_setup_response, normalize_payload

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_STRUCTURE_HINT = (
    "Struktur-Vorgabe:\n"
    "1) Mandant & Scope – Branche, Frameworks, Tenant-Typ\n"
    "2) AI Governance Setup-Status – Wizard-Fortschritt, Guided-Setup\n"
    "3) AI-Systeme & High-Risk – Anzahl, High-Risk, NIS2-kritisch\n"
    "4) AI KPIs & Monitoring – Kurz, welche KPIs gesetzt sind, Trends\n"
    "5) Framework-Coverage & Gaps – Cross-Regulation\n"
    "6) Nächste empfohlene Schritte – 3–5 Maßnahmen, in 90 Tagen umsetzbar\n\n"
    "Antwort ausschließlich als Markdown."
)


def _systems_with_kpi_proxy(ksum: AiKpiSummaryResponse) -> int:
    return max((p.systems_with_data for p in ksum.per_kpi), default=0)


def build_governance_brief_for_tenant(
    session: Session,
    tenant_id: str,
) -> AdvisorTenantGovernanceBrief:
    """Leichte Aggregation für Portfolio-Zeilen (ohne Advisor-Link-Prüfung)."""
    raw = TenantAIGovernanceSetupRepository(session).get_payload(tenant_id)
    payload = normalize_payload(raw)
    setup_read = build_setup_response(session, tenant_id, payload)
    prog = {p for p in setup_read.progress_steps if isinstance(p, int) and 1 <= p <= 6}
    fw = list(payload.get("active_frameworks") or [])

    cross_mean: float | None = None
    gap_n = 0
    if is_feature_enabled(FeatureFlag.cross_regulation_dashboard):
        try:
            xsum = build_cross_regulation_summary(session, tenant_id)
            if xsum.frameworks:
                cross_mean = round(
                    sum(f.coverage_percent for f in xsum.frameworks) / len(xsum.frameworks),
                    2,
                )
            gaps = compute_cross_regulation_gaps(
                session,
                tenant_id,
                focus_framework_keys=fw if fw else None,
            )
            gap_n = len(gaps.gaps)
        except Exception:
            logger.exception("governance_brief_cross_reg_failed tenant=%s", tenant_id)

    nis2_crit = 0
    for s in AISystemRepository(session).list_for_tenant(tenant_id):
        if s.criticality == AISystemCriticality.very_high:
            nis2_crit += 1

    return AdvisorTenantGovernanceBrief(
        wizard_progress_count=len(prog),
        wizard_steps_total=6,
        active_framework_keys=fw,
        cross_reg_mean_coverage_percent=cross_mean,
        regulatory_gap_count=gap_n,
        nis2_critical_ai_count=nis2_crit,
    )


def build_client_governance_snapshot(
    session: Session,
    advisor_id: str,
    client_tenant_id: str,
    advisor_repo: AdvisorTenantRepository,
) -> AdvisorClientGovernanceSnapshotResponse | None:
    if advisor_repo.get_link(advisor_id, client_tenant_id) is None:
        return None

    now = datetime.now(UTC)
    treg = TenantRegistryRepository(session).get_by_id(client_tenant_id)
    display = (treg.display_name if treg else None) or client_tenant_id
    industry = treg.industry if treg else None
    country = treg.country if treg else None
    nis2_scope = treg.nis2_scope if treg else None
    ai_act_scope = treg.ai_act_scope if treg else None

    setup_repo = TenantAIGovernanceSetupRepository(session)
    raw = setup_repo.get_payload(client_tenant_id)
    payload = normalize_payload(raw)
    ag_setup = build_setup_response(session, client_tenant_id, payload)
    tenant_kind = ag_setup.tenant_kind

    guided = compute_tenant_setup_status(session, client_tenant_id)
    setup_snap = SetupStatusSnapshot(
        guided_setup_completed_steps=guided.completed_steps,
        guided_setup_total_steps=guided.total_steps,
        ai_governance_wizard_progress_steps=sorted(
            {p for p in ag_setup.progress_steps if isinstance(p, int) and 1 <= p <= 6},
        ),
        ai_governance_wizard_steps_total=6,
        ai_governance_wizard_marked_steps=list(ag_setup.steps_marked_complete),
    )

    fw_scope = FrameworkScopeSnapshot(
        active_frameworks=list(ag_setup.active_frameworks),
        compliance_scopes=list(ag_setup.compliance_scopes),
    )

    ai_repo = AISystemRepository(session)
    systems = ai_repo.list_for_tenant(client_tenant_id)
    high_risk = 0
    nis2_crit = 0
    by_rl: dict[str, int] = {}
    for s in systems:
        if isinstance(s.risk_level, AISystemRiskLevel):
            rl = s.risk_level.value
        else:
            rl = str(s.risk_level)
        by_rl[rl] = by_rl.get(rl, 0) + 1
        if s.risk_level == AISystemRiskLevel.high:
            high_risk += 1
        if s.criticality == AISystemCriticality.very_high:
            nis2_crit += 1

    ai_sum = AiSystemsSummarySnapshot(
        total_count=len(systems),
        high_risk_count=high_risk,
        nis2_critical_count=nis2_crit,
        by_risk_level=by_rl,
    )

    kpi_snap = KpiSummarySnapshot(
        high_risk_systems_in_scope=0,
        systems_with_kpi_values=0,
        critical_kpi_system_rows=0,
        aggregate_trends_non_flat=0,
    )
    if is_feature_enabled(FeatureFlag.ai_kpi_kri):
        try:
            ksum = build_ai_kpi_summary(session, client_tenant_id)
            kpi_snap = KpiSummarySnapshot(
                high_risk_systems_in_scope=ksum.high_risk_system_count,
                systems_with_kpi_values=_systems_with_kpi_proxy(ksum),
                critical_kpi_system_rows=len(ksum.per_system_critical),
                aggregate_trends_non_flat=sum(
                    1 for p in ksum.per_kpi if p.trend != "flat" and p.systems_with_data > 0
                ),
            )
        except Exception:
            logger.exception("snapshot_kpi_summary_failed tenant=%s", client_tenant_id)

    cross_list: list[CrossRegFrameworkSnapshot] = []
    gap_n = 0
    if is_feature_enabled(FeatureFlag.cross_regulation_dashboard):
        try:
            xsum = build_cross_regulation_summary(session, client_tenant_id)
            cross_list = [
                CrossRegFrameworkSnapshot(
                    framework_key=f.framework_key,
                    name=f.name,
                    coverage_percent=float(f.coverage_percent),
                    gap_count=f.gap_count,
                    total_requirements=f.total_requirements,
                )
                for f in xsum.frameworks
            ]
            gaps = compute_cross_regulation_gaps(
                session,
                client_tenant_id,
                focus_framework_keys=fw_scope.active_frameworks or None,
            )
            gap_n = len(gaps.gaps)
        except Exception:
            logger.exception("snapshot_cross_reg_failed tenant=%s", client_tenant_id)

    reports = ReportsSummarySnapshot(reports_total=0)
    if is_feature_enabled(FeatureFlag.ai_compliance_board_report):
        try:
            rows = AiComplianceBoardReportRepository(session).list_for_tenant(
                client_tenant_id,
                limit=200,
            )
            reports = ReportsSummarySnapshot(
                reports_total=len(rows),
                last_report_id=rows[0].id if rows else None,
                last_report_created_at=rows[0].created_at_utc if rows else None,
                last_report_audience=rows[0].audience_type if rows else None,
                last_report_title=rows[0].title if rows else None,
            )
        except Exception:
            logger.exception("snapshot_board_reports_failed tenant=%s", client_tenant_id)

    gap_assist = GapAssistSnapshot(
        regulatory_gap_items_count=gap_n,
        llm_gap_suggestions_count=None,
    )

    readiness: ReadinessScoreResponse | None = None
    if is_feature_enabled(FeatureFlag.readiness_score):
        try:
            readiness = compute_readiness_score(session, client_tenant_id)
        except Exception:
            logger.exception("snapshot_readiness_failed tenant=%s", client_tenant_id)
            readiness = None

    oami_snap: OperationalAiMonitoringSnapshot | None = None
    try:
        oami = compute_tenant_operational_monitoring_index(
            session,
            client_tenant_id,
            window_days=90,
            persist_snapshot=False,
        )
        expl = explain_tenant_oami_de(oami)
        oami_snap = OperationalAiMonitoringSnapshot(
            index_90d=oami.operational_monitoring_index if oami.has_any_runtime_data else None,
            level=str(oami.level) if oami.has_any_runtime_data else None,
            has_runtime_data=oami.has_any_runtime_data,
            systems_scored=oami.systems_scored,
            narrative_de=expl.summary_de,
            drivers_de=list(expl.drivers_de)[:12],
        )
    except Exception:
        logger.exception("snapshot_oami_failed tenant=%s", client_tenant_id)

    return AdvisorClientGovernanceSnapshotResponse(
        advisor_id=advisor_id,
        client_tenant_id=client_tenant_id,
        generated_at_utc=now,
        client_info=ClientInfoSnapshot(
            tenant_id=client_tenant_id,
            display_name=display,
            industry=industry,
            country=country,
            tenant_kind=tenant_kind,
            registry_nis2_scope=nis2_scope,
            registry_ai_act_scope=ai_act_scope,
        ),
        setup_status=setup_snap,
        framework_scope=fw_scope,
        ai_systems_summary=ai_sum,
        kpi_summary=kpi_snap,
        cross_reg_summary=cross_list,
        gap_assist=gap_assist,
        reports_summary=reports,
        readiness=readiness,
        operational_ai_monitoring=oami_snap,
    )


def generate_advisor_governance_snapshot_markdown(
    session: Session,
    client_tenant_id: str,
    snapshot: AdvisorClientGovernanceSnapshotResponse,
) -> AdvisorGovernanceSnapshotMarkdownResponse:
    if not is_feature_enabled(FeatureFlag.llm_enabled, client_tenant_id, session=session):
        msg = "LLM features are disabled for this tenant (COMPLIANCEHUB_FEATURE_LLM_ENABLED)."
        raise PermissionError(msg)

    system_block = (
        "Du bist ein erfahrener GRC- und AI-Governance-Berater in DACH. Erstelle knappe "
        "Mandanten-Snapshots (max. 1 Seite) auf Basis eines strukturierten Governance-Status. "
        "Zielgruppe: Geschäftsführung/CISO des Mandanten. Schreibe deutsch, neutral, mit klaren "
        "Bullet Points. Nutze ausschließlich die JSON-Fakten; erfinde keine Zahlen oder Namen.\n\n"
    )
    facts = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False)
    prompt = system_block + _STRUCTURE_HINT + "\n\nJSON-Fakten:\n" + facts

    router = LLMRouter(session=session)
    resp = router.route_and_call(
        LLMTaskType.ADVISOR_GOVERNANCE_SNAPSHOT,
        prompt,
        client_tenant_id,
    )
    return AdvisorGovernanceSnapshotMarkdownResponse(
        markdown=(resp.text or "").strip(),
        provider=str(resp.provider.value),
        model_id=resp.model_id,
    )
