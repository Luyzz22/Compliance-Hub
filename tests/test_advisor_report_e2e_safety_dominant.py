"""
E2E-Golden: Advisor-Tenant-Report (Brief ↔ Drilldown ↔ Risiko ↔ Markdown).

Fixtures: tests/fixtures/advisor-report-e2e/
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.advisor_models import AdvisorTenantReport, TenantReportCriticalRequirementItem
from app.governance_maturity_models import GovernanceMaturityResponse
from app.incident_drilldown_models import TenantIncidentDrilldownOut
from app.services.advisor_brief_drilldown_alignment import (
    FOCUS_MONITORING_COVERAGE_DE,
    apply_drilldown_alignment_to_brief,
)
from app.services.advisor_governance_maturity_brief_parse import (
    build_fallback_advisor_governance_maturity_brief_parse_result,
)
from app.services.advisor_tenant_report_incident_drilldown_md import (
    build_incident_system_supplier_drilldown_section,
)
from app.services.advisor_tenant_report_markdown import (
    render_risiko_incident_lage_markdown_section,
    render_tenant_report_markdown,
)
from app.services.advisor_tenant_report_risiko import nis2_entity_category_report_label_de
from app.services.incident_drilldown_signal_utils import drilldown_mandate_pattern

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "advisor-report-e2e"


def _norm_md(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip() + "\n"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _safety_aligned_brief_and_drilldown() -> tuple[
    GovernanceMaturityResponse,
    TenantIncidentDrilldownOut,
    dict,
    AdvisorGovernanceMaturityBrief,
]:
    case = _FIXTURES / "safety_dominant_case"
    snap = GovernanceMaturityResponse.model_validate_json(
        (case / "governance_maturity_snapshot.json").read_text(encoding="utf-8"),
    )
    dd = TenantIncidentDrilldownOut.model_validate_json(
        (case / "incident_drilldown.json").read_text(encoding="utf-8"),
    )
    exp = _load_json(case / "expected_assertions.json")
    base = build_fallback_advisor_governance_maturity_brief_parse_result(snap).brief
    aligned = apply_drilldown_alignment_to_brief(base, dd)
    return snap, dd, exp, aligned


def test_e2e_safety_dominant_brief_alignment_matches_golden() -> None:
    _, dd, exp, aligned = _safety_aligned_brief_and_drilldown()
    want = exp["brief_after_alignment"]
    assert (
        aligned.governance_maturity_summary.overall_assessment.level
        == want["governance_maturity_summary_overall_level"]
    )
    assert aligned.recommended_focus_areas[0] == want["recommended_focus_areas_0"]
    assert aligned.client_ready_paragraph_de == want["client_ready_paragraph_de"]
    assert "Acme Claims Assistant" in (aligned.client_ready_paragraph_de or "")
    assert "Batch Scoring API" in (aligned.client_ready_paragraph_de or "")
    assert drilldown_mandate_pattern(dd.items) == "safety"


def test_e2e_safety_dominant_risiko_and_drilldown_fragments_match_golden_files() -> None:
    case = _FIXTURES / "safety_dominant_case"
    _, dd, _, aligned = _safety_aligned_brief_and_drilldown()
    report = _safety_domain_report(aligned, dd)
    risiko_md = render_risiko_incident_lage_markdown_section(report)
    expected_risiko = (case / "expected_risiko_fragment.md").read_text(encoding="utf-8")
    assert _norm_md(risiko_md) == _norm_md(expected_risiko)

    drill_md = build_incident_system_supplier_drilldown_section(
        dd,
        include_governance_brief_bridge=True,
    )
    expected_drill = (case / "expected_drilldown_fragment.md").read_text(encoding="utf-8")
    assert _norm_md(drill_md or "") == _norm_md(expected_drill)


def _safety_domain_report(
    brief: AdvisorGovernanceMaturityBrief,
    dd: TenantIncidentDrilldownOut,
) -> AdvisorTenantReport:
    fixed = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return AdvisorTenantReport(
        tenant_id="e2e-golden-safety-tenant",
        tenant_name="E2E Golden Mandant",
        industry="IT",
        country="DE",
        generated_at_utc=fixed,
        ai_systems_total=5,
        high_risk_systems_count=2,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.72,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=400,
        nis2_incident_readiness_percent=70.0,
        nis2_supplier_risk_coverage_percent=65.0,
        nis2_ot_it_segregation_mean_percent=55.0,
        nis2_critical_focus_systems_count=1,
        governance_open_actions_count=3,
        governance_overdue_actions_count=1,
        top_critical_requirements=[
            TenantReportCriticalRequirementItem(code="X1", name="Gap", affected_systems_count=2),
        ],
        setup_completed_steps=5,
        setup_total_steps=7,
        setup_open_step_labels=[],
        governance_maturity_advisor_brief=brief,
        incident_drilldown_snapshot=dd,
        risiko_nis2_scope_label_de=nis2_entity_category_report_label_de("important_entity"),
        risiko_kritis_sector_label_de="Energie",
        risiko_incidents_90d_count=9,
        risiko_incidents_90d_high_severity=3,
        risiko_incident_burden_level="high",
        risiko_open_incidents_count=2,
        risiko_regulatory_priority_note_de=None,
        risiko_nis2_entity_category="important_entity",
    )


def test_e2e_safety_dominant_full_markdown_structure_and_alignment() -> None:
    _, dd, exp, aligned = _safety_aligned_brief_and_drilldown()
    report = _safety_domain_report(aligned, dd)
    md = render_tenant_report_markdown(report)
    for needle in exp["full_markdown_must_contain"]:
        assert needle in md, f"missing fragment: {needle!r}"
    order = exp["section_order"]
    positions = [md.index(marker) for marker in order]
    assert positions == sorted(positions)


def test_e2e_benign_low_monitoring_focus_and_wenige_drilldown_text() -> None:
    case = _FIXTURES / "benign_low_case"
    snap = GovernanceMaturityResponse.model_validate_json(
        (case / "governance_maturity_snapshot.json").read_text(encoding="utf-8"),
    )
    dd = TenantIncidentDrilldownOut.model_validate_json(
        (case / "incident_drilldown.json").read_text(encoding="utf-8"),
    )
    exp = _load_json(case / "expected_assertions.json")
    base = build_fallback_advisor_governance_maturity_brief_parse_result(snap).brief
    aligned = apply_drilldown_alignment_to_brief(base, dd)
    want = exp["brief_after_alignment"]
    assert aligned.recommended_focus_areas[0] == want["recommended_focus_areas_0"]
    assert aligned.recommended_focus_areas[0] == FOCUS_MONITORING_COVERAGE_DE
    assert aligned.client_ready_paragraph_de == want["client_ready_paragraph_de"]

    fixed = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    report = AdvisorTenantReport(
        tenant_id="e2e-golden-benign-tenant",
        tenant_name="E2E Benign Mandant",
        industry="IT",
        country="DE",
        generated_at_utc=fixed,
        ai_systems_total=3,
        high_risk_systems_count=0,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.42,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=400,
        nis2_incident_readiness_percent=50.0,
        nis2_supplier_risk_coverage_percent=40.0,
        nis2_ot_it_segregation_mean_percent=None,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=1,
        governance_overdue_actions_count=0,
        top_critical_requirements=[],
        setup_completed_steps=2,
        setup_total_steps=7,
        setup_open_step_labels=["KI-Inventar"],
        governance_maturity_advisor_brief=aligned,
        incident_drilldown_snapshot=dd,
        risiko_nis2_scope_label_de=nis2_entity_category_report_label_de("none"),
        risiko_kritis_sector_label_de=None,
        risiko_incidents_90d_count=2,
        risiko_incidents_90d_high_severity=0,
        risiko_incident_burden_level="low",
        risiko_open_incidents_count=0,
        risiko_regulatory_priority_note_de=None,
        risiko_nis2_entity_category="none",
    )
    md = render_tenant_report_markdown(report)
    for needle in exp["full_markdown_must_contain"]:
        assert needle in md, f"missing: {needle!r}"
    for forbidden in exp["full_markdown_must_not_contain"]:
        assert forbidden not in md
