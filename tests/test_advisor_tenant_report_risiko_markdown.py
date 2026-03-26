"""Golden regression: Risiko- und Incident-Lage (NIS2/KRITIS) im Mandanten-Steckbrief."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.advisor_models import AdvisorTenantReport
from app.services.advisor_tenant_report_markdown import render_risiko_incident_lage_markdown_section
from app.services.advisor_tenant_report_risiko import nis2_entity_category_report_label_de

_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "advisor-tenant-report-markdown"
    / "risiko-incident-lage"
)


def _normalize_markdown(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip() + "\n"


def _minimal_report(**risiko: object) -> AdvisorTenantReport:
    base = dict(
        tenant_id="t-golden",
        tenant_name="Golden Mandant",
        industry="IT",
        country="DE",
        generated_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        ai_systems_total=1,
        high_risk_systems_count=0,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.5,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=100,
        nis2_incident_readiness_percent=50.0,
        nis2_supplier_risk_coverage_percent=50.0,
        nis2_ot_it_segregation_mean_percent=None,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=0,
        governance_overdue_actions_count=0,
        top_critical_requirements=[],
        setup_completed_steps=1,
        setup_total_steps=7,
        setup_open_step_labels=[],
    )
    base.update(risiko)
    return AdvisorTenantReport(**base)


@pytest.mark.parametrize(
    ("fixture_name", "report"),
    [
        (
            "case_c_outside_nis2_no_incidents.md",
            _minimal_report(
                risiko_nis2_scope_label_de=nis2_entity_category_report_label_de("none"),
                risiko_nis2_entity_category="none",
                risiko_incident_burden_level="low",
            ),
        ),
        (
            "case_b_important_low_burden.md",
            _minimal_report(
                risiko_nis2_scope_label_de=nis2_entity_category_report_label_de("important_entity"),
                risiko_nis2_entity_category="important_entity",
                risiko_incidents_90d_count=1,
                risiko_incidents_90d_high_severity=0,
                risiko_incident_burden_level="medium",
            ),
        ),
        (
            "case_a_essential_kritis_high.md",
            _minimal_report(
                risiko_nis2_scope_label_de=nis2_entity_category_report_label_de("essential_entity"),
                risiko_nis2_entity_category="essential_entity",
                risiko_kritis_sector_label_de="Energie",
                risiko_incidents_90d_count=6,
                risiko_incidents_90d_high_severity=3,
                risiko_incident_burden_level="high",
                risiko_open_incidents_count=2,
                risiko_regulatory_priority_note_de=(
                    "Regulatorischer Aufstock (Test); Priorität eine Stufe erhöht."
                ),
            ),
        ),
    ],
)
def test_risiko_incident_lage_matches_golden(
    fixture_name: str,
    report: AdvisorTenantReport,
) -> None:
    generated = render_risiko_incident_lage_markdown_section(report)
    expected = (_FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")
    assert _normalize_markdown(generated) == _normalize_markdown(expected)
