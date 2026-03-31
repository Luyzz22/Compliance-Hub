"""Tests: Markdown-Abschnitt „System- und Lieferanten-Drilldown“ im Advisor-Mandanten-Steckbrief."""

from __future__ import annotations

from app.incident_drilldown_models import (
    IncidentDrilldownCategoryCounts,
    TenantIncidentDrilldownItem,
    TenantIncidentDrilldownOut,
)
from app.services.advisor_tenant_report_incident_drilldown_md import (
    build_incident_system_supplier_drilldown_section,
)


def _item(
    *,
    sid: str,
    name: str,
    supplier: str = "SAP AI Core",
    total: int = 5,
    ws: float = 0.55,
    wa: float = 0.25,
    wo: float = 0.2,
    hint: str = "",
    safety_c: int = 3,
    avail_c: int = 1,
    other_c: int = 1,
) -> TenantIncidentDrilldownItem:
    return TenantIncidentDrilldownItem(
        ai_system_id=sid,
        ai_system_name=name,
        supplier_label_de=supplier,
        event_source="sap_ai_core",
        incident_total_90d=total,
        incident_count_by_category=IncidentDrilldownCategoryCounts(
            safety=safety_c,
            availability=avail_c,
            other=other_c,
        ),
        weighted_incident_share_safety=ws,
        weighted_incident_share_availability=wa,
        weighted_incident_share_other=wo,
        oami_local_hint_de=hint,
    )


def _out(items: list[TenantIncidentDrilldownItem]) -> TenantIncidentDrilldownOut:
    return TenantIncidentDrilldownOut(
        tenant_id="t-1",
        window_days=90,
        systems_with_runtime_events=len(items),
        systems_with_incidents=len(items),
        items=items,
    )


def test_build_section_returns_none_when_empty() -> None:
    assert build_incident_system_supplier_drilldown_section(None) is None
    assert build_incident_system_supplier_drilldown_section(_out([])) is None


def test_safety_dominant_wording_and_system_name() -> None:
    data = _out(
        [
            _item(
                sid="a",
                name="SafetyBot",
                supplier="SAP AI Core",
                total=2,
                ws=0.55,
                wa=0.2,
                wo=0.25,
            ),
        ],
    )
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert "### System- und Lieferanten-Drilldown" in md
    assert "Überblick zu den KI-Systemen und Lieferanten" in md
    assert "**SafetyBot**" in md
    assert "SAP AI Core" in md
    assert "sicherheitsrelevante Incidents" in md
    assert "OAMI" in md
    assert "nur wenige Incidents beobachtet" in md


def test_availability_dominant_wording() -> None:
    data = _out(
        [
            _item(
                sid="b",
                name="LatencySvc",
                supplier="Manuell / Custom",
                total=12,
                ws=0.15,
                wa=0.55,
                wo=0.3,
                safety_c=1,
                avail_c=8,
                other_c=3,
            ),
        ],
    )
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert "**LatencySvc**" in md
    assert "Manuell / Custom" in md
    assert "Verfügbarkeits-/Performance-Incidents" in md
    assert "Betriebsstabilität" in md
    assert "nur wenige Incidents beobachtet" not in md


def test_low_other_template() -> None:
    data = _out(
        [
            _item(
                sid="c",
                name="QuietSys",
                total=8,
                ws=0.32,
                wa=0.33,
                wo=0.35,
                safety_c=2,
                avail_c=3,
                other_c=3,
            ),
        ],
    )
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert "**QuietSys**" in md
    assert "kein primärer OAMI-Treiber" in md


def test_includes_safety_and_availability_representatives_when_both_exist() -> None:
    data = _out(
        [
            _item(
                sid="avail",
                name="AvailFirst",
                supplier="SAP BTP Event Mesh",
                total=20,
                ws=0.2,
                wa=0.55,
                wo=0.25,
            ),
            _item(
                sid="safe",
                name="SafeSecond",
                supplier="SAP AI Core",
                total=15,
                ws=0.55,
                wa=0.25,
                wo=0.2,
            ),
            _item(
                sid="noise",
                name="NoiseThird",
                supplier="Sonstiger Anbieter",
                total=2,
                ws=0.34,
                wa=0.33,
                wo=0.33,
            ),
        ],
    )
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert "**AvailFirst**" in md
    assert "**SafeSecond**" in md


def test_appends_oami_hint_when_distinct() -> None:
    hint = "Zusätzlicher Kurzvermerk aus dem Drilldown."
    data = _out([_item(sid="x", name="Hinted", total=5, hint=hint)])
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert hint in md
    assert "*Kurz:*" in md


def test_high_volume_safety_template() -> None:
    data = _out([_item(sid="h", name="HeavySafe", total=10, ws=0.6, wa=0.2, wo=0.2)])
    md = build_incident_system_supplier_drilldown_section(data)
    assert md is not None
    assert "erhöhtes Volumen" in md
    assert "überwiegend sicherheitsrelevant" in md


def test_drilldown_includes_governance_brief_bridge_when_requested() -> None:
    dd = _out([_item(sid="z", name="BridgeSys", total=5, ws=0.55, wa=0.22, wo=0.23)])
    with_bridge = build_incident_system_supplier_drilldown_section(
        dd,
        include_governance_brief_bridge=True,
    )
    without = build_incident_system_supplier_drilldown_section(dd)
    assert with_bridge is not None and without is not None
    assert "Governance-Kurzbriefs wider" in with_bridge
    assert "Governance-Kurzbriefs wider" not in without


def test_render_full_markdown_inserts_drilldown_before_eu_ai_act_section() -> None:
    from datetime import UTC, datetime

    from app.advisor_models import AdvisorTenantReport, TenantReportCriticalRequirementItem
    from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown

    snap = _out([_item(sid="z", name="ReportSys", total=6, ws=0.55, wa=0.22, wo=0.23)])
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
        incident_drilldown_snapshot=snap,
    )
    md = render_tenant_report_markdown(r)
    ridx = md.index("## Risiko- und Incident-Lage (NIS2/KRITIS)")
    didx = md.index("### System- und Lieferanten-Drilldown")
    pidx = md.index("## Profil")
    eidx = md.index("## EU AI Act")
    assert ridx < didx < pidx < eidx
    assert "**ReportSys**" in md
