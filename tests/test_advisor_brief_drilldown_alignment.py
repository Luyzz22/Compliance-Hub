"""Tests: Abgleich AdvisorGovernanceMaturityBrief mit Incident-Drilldown."""

from __future__ import annotations

from datetime import UTC, datetime

from advisor_brief_scenario_snapshots import SCENARIO_SNAPSHOTS

from app.advisor_models import AdvisorTenantReport, TenantReportCriticalRequirementItem
from app.incident_drilldown_models import (
    IncidentDrilldownCategoryCounts,
    TenantIncidentDrilldownItem,
    TenantIncidentDrilldownOut,
)
from app.services.advisor_brief_drilldown_alignment import (
    FOCUS_AVAILABILITY_DRILLDOWN_DE,
    FOCUS_MONITORING_COVERAGE_DE,
    FOCUS_SAFETY_DRILLDOWN_DE,
    apply_drilldown_alignment_to_brief,
)
from app.services.advisor_governance_maturity_brief_parse import (
    build_fallback_advisor_governance_maturity_brief_parse_result,
)
from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown


def _item(
    *,
    sid: str,
    name: str,
    supplier: str = "SAP AI Core",
    total: int,
    ws: float,
    wa: float,
    wo: float,
) -> TenantIncidentDrilldownItem:
    return TenantIncidentDrilldownItem(
        ai_system_id=sid,
        ai_system_name=name,
        supplier_label_de=supplier,
        event_source="sap_ai_core",
        incident_total_90d=total,
        incident_count_by_category=IncidentDrilldownCategoryCounts(
            safety=int(ws * 10),
            availability=int(wa * 10),
            other=int(wo * 10),
        ),
        weighted_incident_share_safety=ws,
        weighted_incident_share_availability=wa,
        weighted_incident_share_other=wo,
        oami_local_hint_de="",
    )


def _brief_base():
    snap = SCENARIO_SNAPSHOTS["a"]
    return build_fallback_advisor_governance_maturity_brief_parse_result(snap).brief


def test_alignment_prepends_safety_focus_when_safety_dominant_drilldown() -> None:
    brief = _brief_base()
    dd_items = [
        _item(sid="s1", name="SafetyBot", total=12, ws=0.55, wa=0.25, wo=0.2),
    ]
    dd = TenantIncidentDrilldownOut(
        tenant_id="t",
        window_days=90,
        systems_with_runtime_events=1,
        systems_with_incidents=1,
        items=dd_items,
    )
    out = apply_drilldown_alignment_to_brief(brief, dd)
    assert out.recommended_focus_areas[0] == FOCUS_SAFETY_DRILLDOWN_DE
    assert "SafetyBot" in (out.client_ready_paragraph_de or "")
    assert "Safety-Signalen" in (out.client_ready_paragraph_de or "")


def test_alignment_prepends_availability_focus() -> None:
    brief = _brief_base()
    dd = TenantIncidentDrilldownOut(
        tenant_id="t",
        window_days=90,
        systems_with_runtime_events=1,
        systems_with_incidents=1,
        items=[
            _item(sid="a", name="Lat", total=15, ws=0.2, wa=0.55, wo=0.25),
        ],
    )
    out = apply_drilldown_alignment_to_brief(brief, dd)
    assert out.recommended_focus_areas[0] == FOCUS_AVAILABILITY_DRILLDOWN_DE
    assert "Lat" in (out.client_ready_paragraph_de or "")
    assert "Verfügbarkeits-Signalen" in (out.client_ready_paragraph_de or "")


def test_markdown_low_incidents_wenige_wording_and_monitoring_focus() -> None:
    dd = TenantIncidentDrilldownOut(
        tenant_id="t",
        window_days=90,
        systems_with_runtime_events=1,
        systems_with_incidents=1,
        items=[
            _item(sid="q", name="Quiet", total=2, ws=0.34, wa=0.33, wo=0.33),
        ],
    )
    brief = apply_drilldown_alignment_to_brief(_brief_base(), dd)
    r = AdvisorTenantReport(
        tenant_id="t-x",
        tenant_name="X AG",
        industry="IT",
        country="DE",
        generated_at_utc=datetime.now(UTC),
        ai_systems_total=3,
        high_risk_systems_count=1,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.5,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=100,
        nis2_incident_readiness_percent=80.0,
        nis2_supplier_risk_coverage_percent=70.0,
        nis2_ot_it_segregation_mean_percent=60.0,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=0,
        governance_overdue_actions_count=0,
        top_critical_requirements=[
            TenantReportCriticalRequirementItem(code="C1", name="Gap", affected_systems_count=1),
        ],
        setup_completed_steps=4,
        setup_total_steps=7,
        setup_open_step_labels=[],
        governance_maturity_advisor_brief=brief,
        incident_drilldown_snapshot=dd,
    )
    md = render_tenant_report_markdown(r)
    assert "nur wenige Incidents beobachtet" in md
    assert "Monitoring-Abdeckung" in md


def test_alignment_benign_low_uses_monitoring_focus_and_no_system_bridge() -> None:
    brief = _brief_base()
    dd = TenantIncidentDrilldownOut(
        tenant_id="t",
        window_days=90,
        systems_with_runtime_events=1,
        systems_with_incidents=1,
        items=[
            _item(sid="q", name="Quiet", total=2, ws=0.34, wa=0.33, wo=0.33),
        ],
    )
    out = apply_drilldown_alignment_to_brief(brief, dd)
    assert out.recommended_focus_areas[0] == FOCUS_MONITORING_COVERAGE_DE
    para = out.client_ready_paragraph_de
    assert para is None or "Im Fokus stehen" not in para


def test_markdown_coherence_brief_risiko_drilldown_profil() -> None:
    brief = apply_drilldown_alignment_to_brief(
        _brief_base(),
        TenantIncidentDrilldownOut(
            tenant_id="t",
            window_days=90,
            systems_with_runtime_events=1,
            systems_with_incidents=1,
            items=[_item(sid="s1", name="CoherentSys", total=10, ws=0.55, wa=0.22, wo=0.23)],
        ),
    )
    r = AdvisorTenantReport(
        tenant_id="t-x",
        tenant_name="X AG",
        industry="IT",
        country="DE",
        generated_at_utc=datetime.now(UTC),
        ai_systems_total=3,
        high_risk_systems_count=1,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.5,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=100,
        nis2_incident_readiness_percent=80.0,
        nis2_supplier_risk_coverage_percent=70.0,
        nis2_ot_it_segregation_mean_percent=60.0,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=0,
        governance_overdue_actions_count=0,
        top_critical_requirements=[
            TenantReportCriticalRequirementItem(code="C1", name="Gap", affected_systems_count=1),
        ],
        setup_completed_steps=4,
        setup_total_steps=7,
        setup_open_step_labels=[],
        governance_maturity_advisor_brief=brief,
        incident_drilldown_snapshot=TenantIncidentDrilldownOut(
            tenant_id="t-x",
            window_days=90,
            systems_with_runtime_events=1,
            systems_with_incidents=1,
            items=[_item(sid="s1", name="CoherentSys", total=10, ws=0.55, wa=0.22, wo=0.23)],
        ),
    )
    md = render_tenant_report_markdown(r)
    gidx = md.index("## Governance-Reife – Kurzüberblick")
    ridx = md.index("## Risiko- und Incident-Lage (NIS2/KRITIS)")
    didx = md.index("### System- und Lieferanten-Drilldown")
    pidx = md.index("## Profil")
    eidx = md.index("## EU AI Act")
    assert gidx < ridx < didx < pidx < eidx
    assert "Governance-Kurzbriefs wider" in md
    assert "**CoherentSys**" in md
    assert FOCUS_SAFETY_DRILLDOWN_DE.split()[0] in md
