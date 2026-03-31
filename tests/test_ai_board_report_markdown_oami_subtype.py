"""Board-Markdown: optionaler OAMI-Incident-Subtype-Block."""

from __future__ import annotations

from datetime import UTC, datetime

from app.ai_governance_models import (
    AIBoardGovernanceReport,
    AIBoardKpiSummary,
    BoardOperationalMonitoringSection,
    OamiIncidentCategoryCounts,
    OamiIncidentSubtypeProfile,
)
from app.compliance_gap_models import AIComplianceOverview
from app.incident_models import AIIncidentOverview, BySeverityEntry, IncidentSeverity
from app.services.board_report_markdown import render_board_report_markdown
from app.supplier_risk_models import AISupplierRiskOverview


def _minimal_report(*, om: BoardOperationalMonitoringSection | None) -> AIBoardGovernanceReport:
    kpis = AIBoardKpiSummary(
        tenant_id="t1",
        ai_systems_total=1,
        active_ai_systems=1,
        high_risk_systems=0,
        open_policy_violations=0,
        board_maturity_score=0.5,
        compliance_coverage_score=0.5,
        risk_governance_score=0.5,
        operational_resilience_score=0.5,
        responsible_ai_score=0.5,
        high_risk_systems_without_dpia=0,
        critical_systems_without_owner=0,
        nis2_control_gaps=0,
        nis2_incident_readiness_ratio=0.5,
        nis2_supplier_risk_coverage_ratio=0.5,
        iso42001_governance_score=0.5,
        score_change_vs_last_quarter=0.0,
        incidents_last_quarter=0,
        complaints_last_quarter=0,
    )
    compliance = AIComplianceOverview(
        tenant_id="t1",
        overall_readiness=0.5,
        high_risk_systems_with_full_controls=0,
        high_risk_systems_with_critical_gaps=0,
        top_critical_requirements=[],
        deadline="2026-08-02",
        days_remaining=100,
    )
    incidents = AIIncidentOverview(
        tenant_id="t1",
        total_incidents_last_12_months=0,
        open_incidents=0,
        major_incidents_last_12_months=0,
        by_severity=[BySeverityEntry(severity=IncidentSeverity.low, count=0)],
    )
    supplier = AISupplierRiskOverview(
        tenant_id="t1",
        total_systems_with_suppliers=0,
        systems_without_supplier_risk_register=0,
        critical_suppliers_total=0,
        critical_suppliers_without_controls=0,
        by_risk_level=[],
    )
    return AIBoardGovernanceReport(
        tenant_id="t1",
        generated_at=datetime.now(UTC),
        period="last_12_months",
        kpis=kpis,
        compliance_overview=compliance,
        incidents_overview=incidents,
        supplier_risk_overview=supplier,
        alerts=[],
        operational_monitoring=om,
    )


def test_markdown_includes_subtype_heading_when_profile_set() -> None:
    prof = OamiIncidentSubtypeProfile(
        incident_weighted_share_safety=0.7,
        incident_weighted_share_availability=0.2,
        incident_weighted_share_other=0.1,
        incident_count_by_category=OamiIncidentCategoryCounts(
            safety=3,
            availability=1,
            other=0,
        ),
        oami_subtype_narrative_de="Kurztext für den Test.",
    )
    om = BoardOperationalMonitoringSection(
        index_value=65,
        level="medium",
        window_days=90,
        has_data=True,
        systems_scored=2,
        summary_de="s",
        drivers_de=["d1"],
        oami_incident_subtype_profile=prof,
    )
    md = render_board_report_markdown(_minimal_report(om=om))
    assert "### Operatives AI-Monitoring – Incident-Subtypen" in md
    assert "chart:oami-subtype-shares" in md
    assert "Kurztext für den Test." in md
    assert "gewichteter Fokus" in md


def test_markdown_omits_subtype_block_without_profile() -> None:
    om = BoardOperationalMonitoringSection(
        index_value=50,
        level="medium",
        window_days=90,
        has_data=True,
        systems_scored=1,
        summary_de="s",
        drivers_de=[],
        oami_incident_subtype_profile=None,
    )
    md = render_board_report_markdown(_minimal_report(om=om))
    assert "### Operatives AI-Monitoring – Incident-Subtypen" not in md
