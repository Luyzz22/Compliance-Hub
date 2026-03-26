"""Golden regression: fake LLM JSON → parse/align → Markdown + tenant report embed."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from advisor_brief_scenario_snapshots import SCENARIO_SNAPSHOTS

from app.advisor_models import AdvisorTenantReport, TenantReportCriticalRequirementItem
from app.services.advisor_governance_maturity_brief_markdown import (
    render_advisor_governance_maturity_brief_markdown_section,
)
from app.services.advisor_governance_maturity_brief_parse import (
    parse_advisor_governance_maturity_brief,
)
from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown

_JSON_DIR = Path(__file__).resolve().parent / "fixtures" / "advisor-governance-maturity-brief"
_MD_DIR = Path(__file__).resolve().parent / "fixtures" / "advisor-tenant-report-markdown"


def _normalize_markdown(text: str) -> str:
    """Stabile Vergleichsbasis: keine trailing spaces, konsistentes Datei-Ende."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip() + "\n"


@pytest.mark.parametrize(
    ("scenario_id", "expected_overall"),
    [
        ("a", "low"),
        ("b", "low"),
        ("c", "medium"),
        ("d", "high"),
    ],
)
def test_parse_fake_llm_json_aligns_conservative_overall_level(
    scenario_id: str,
    expected_overall: str,
) -> None:
    snap = SCENARIO_SNAPSHOTS[scenario_id]
    raw = (_JSON_DIR / f"scenario_{scenario_id}_llm.json").read_text(encoding="utf-8")
    out = parse_advisor_governance_maturity_brief(raw, snap)
    assert out.parse_ok is True
    assert out.used_llm_client_paragraph is True
    assert out.brief.governance_maturity_summary.overall_assessment.level == expected_overall


@pytest.mark.parametrize("scenario_id", ["a", "b", "c", "d"])
def test_advisor_brief_markdown_matches_golden_file(scenario_id: str) -> None:
    snap = SCENARIO_SNAPSHOTS[scenario_id]
    raw = (_JSON_DIR / f"scenario_{scenario_id}_llm.json").read_text(encoding="utf-8")
    out = parse_advisor_governance_maturity_brief(raw, snap)
    generated = render_advisor_governance_maturity_brief_markdown_section(out.brief)
    expected_path = _MD_DIR / f"scenario_{scenario_id}_brief_section.md"
    expected = expected_path.read_text(encoding="utf-8")
    assert _normalize_markdown(generated) == _normalize_markdown(expected)


def test_tenant_report_markdown_embeds_normalized_brief_section() -> None:
    """Vollständiger Steckbrief enthält denselben Brief-Block wie die Golden-Datei."""
    snap = SCENARIO_SNAPSHOTS["a"]
    raw = (_JSON_DIR / "scenario_a_llm.json").read_text(encoding="utf-8")
    brief = parse_advisor_governance_maturity_brief(raw, snap).brief
    fixed_ts = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
    report = AdvisorTenantReport(
        tenant_id="golden-tenant-a",
        tenant_name="Golden Mandant A",
        industry="IT",
        country="DE",
        generated_at_utc=fixed_ts,
        ai_systems_total=5,
        high_risk_systems_count=1,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.45,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=400,
        nis2_incident_readiness_percent=60.0,
        nis2_supplier_risk_coverage_percent=55.0,
        nis2_ot_it_segregation_mean_percent=None,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=2,
        governance_overdue_actions_count=0,
        top_critical_requirements=[
            TenantReportCriticalRequirementItem(
                code="HR-01",
                name="Dokumentation",
                affected_systems_count=1,
            ),
        ],
        setup_completed_steps=4,
        setup_total_steps=7,
        setup_open_step_labels=["Evidenzen"],
        governance_maturity_advisor_brief=brief,
    )
    full_md = render_tenant_report_markdown(report)
    frag = render_advisor_governance_maturity_brief_markdown_section(brief)
    assert "## Governance-Reife – Kurzüberblick" in full_md
    assert _normalize_markdown(frag) in _normalize_markdown(full_md)
    assert "nächste 90 Tage" in full_md
