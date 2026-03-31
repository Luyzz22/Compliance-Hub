"""Board-Report-Prompt enthält KPI-Section für LLM."""

from __future__ import annotations

from app.ai_compliance_board_report_models import AiComplianceBoardReportInput
from app.services.ai_compliance_board_report_llm import build_board_report_user_prompt


def test_board_report_user_prompt_includes_ai_performance_kpi_heading() -> None:
    inp = AiComplianceBoardReportInput(
        tenant_id="t-1",
        audience_type="board",
        language="de",
    )
    prompt = build_board_report_user_prompt(inp)
    assert "AI Performance & Risk KPIs" in prompt
    assert "high_risk_kpi_summaries" in prompt


def test_board_report_user_prompt_includes_oami_subtype_when_profile_set() -> None:
    from app.ai_governance_models import OamiIncidentCategoryCounts, OamiIncidentSubtypeProfile

    prof = OamiIncidentSubtypeProfile(
        incident_weighted_share_safety=0.5,
        incident_weighted_share_availability=0.25,
        incident_weighted_share_other=0.25,
        incident_count_by_category=OamiIncidentCategoryCounts(
            safety=1,
            availability=1,
            other=0,
        ),
        oami_subtype_narrative_de="Test.",
    )
    inp = AiComplianceBoardReportInput(
        tenant_id="t-1",
        audience_type="board",
        language="de",
        oami_subtype_profile=prof,
    )
    prompt = build_board_report_user_prompt(inp)
    assert "OAMI Incident-Subtypen" in prompt
    assert "oami_subtype_profile" in prompt
