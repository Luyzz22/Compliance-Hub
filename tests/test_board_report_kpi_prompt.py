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
