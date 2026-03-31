"""Advisor governance maturity brief: parse, align, fallback, portfolio helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.advisor_governance_maturity_brief_models import (
    advisor_brief_focus_marker_de,
    advisor_brief_portfolio_tooltip_de,
)
from app.governance_maturity_models import (
    GovernanceActivityBlock,
    GovernanceMaturityResponse,
    GovernanceReadinessBlock,
    OperationalAiMonitoringBlock,
)
from app.llm.exceptions import LLMContractViolation
from app.services.advisor_governance_maturity_brief_markdown import (
    render_advisor_governance_maturity_brief_markdown_section,
)
from app.services.advisor_governance_maturity_brief_parse import (
    build_fallback_advisor_governance_maturity_brief_parse_result,
    parse_advisor_governance_maturity_brief,
)
from app.services.advisor_governance_maturity_brief_prompt import (
    build_advisor_governance_maturity_brief_prompt,
)

_FIXTURES = (
    Path(__file__).resolve().parent / "fixtures" / "advisor_governance_maturity_brief_golden"
)


def _snap_basic_low() -> GovernanceMaturityResponse:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return GovernanceMaturityResponse(
        tenant_id="adv-brief-golden",
        computed_at=now,
        readiness=GovernanceReadinessBlock(
            score=38,
            level="basic",
            interpretation="Strukturell noch im Aufbau.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=35,
            level="low",
            window_days=90,
            last_computed_at=now,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=32,
            level="low",
            window_days=90,
            message_de="Kurz OAMI.",
            drivers_de=[],
        ),
    )


def test_parse_advisor_brief_aligns_core_to_snapshot() -> None:
    raw = (_FIXTURES / "response_ok.json").read_text(encoding="utf-8")
    snap = _snap_basic_low()
    out = parse_advisor_governance_maturity_brief(raw, snap)
    assert out.parse_ok is True
    assert out.used_llm_client_paragraph is True
    gm = out.brief.governance_maturity_summary
    assert gm.readiness.score == 38
    assert gm.readiness.level == "basic"
    assert gm.activity.index == 35
    assert gm.activity.level == "low"
    assert gm.operational_monitoring.index == 32
    assert gm.operational_monitoring.level == "low"
    assert out.brief.suggested_next_steps_window == "nächste 90 Tage"
    assert len(out.brief.recommended_focus_areas) >= 1
    assert "OAMI" in out.brief.recommended_focus_areas[0]


def test_parse_advisor_brief_invalid_json_falls_back() -> None:
    snap = _snap_basic_low()
    out = parse_advisor_governance_maturity_brief("not json {{{", snap)
    assert out.parse_ok is False
    assert out.brief.governance_maturity_summary.readiness.score == 38


def test_parse_advisor_brief_contract_violation_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit ``validate_llm_json_output`` failure maps to deterministic fallback."""

    def _raise(*_a: object, **_k: object) -> object:
        raise LLMContractViolation("forced contract failure")

    monkeypatch.setattr(
        "app.services.advisor_governance_maturity_brief_parse.validate_llm_json_output",
        _raise,
    )
    snap = _snap_basic_low()
    raw = (_FIXTURES / "response_ok.json").read_text(encoding="utf-8")
    out = parse_advisor_governance_maturity_brief(raw, snap)
    assert out.parse_ok is False
    assert out.brief.governance_maturity_summary.readiness.score == 38


def test_fallback_brief_has_heuristic_focus() -> None:
    snap = _snap_basic_low()
    out = build_fallback_advisor_governance_maturity_brief_parse_result(snap)
    assert out.parse_ok is False
    assert any("Readiness" in x for x in out.brief.recommended_focus_areas)
    assert any("OAMI" in x for x in out.brief.recommended_focus_areas)


def test_build_advisor_brief_prompt_contains_schema_markers() -> None:
    snap = _snap_basic_low()
    p = build_advisor_governance_maturity_brief_prompt(snap, None)
    assert "Advisor-Governance-Maturity-Brief-Schema-Version" in p
    assert "recommended_focus_areas" in p
    assert "adv-brief-golden" in p


def test_markdown_section_contains_header_and_bullets() -> None:
    snap = _snap_basic_low()
    out = build_fallback_advisor_governance_maturity_brief_parse_result(snap)
    md = render_advisor_governance_maturity_brief_markdown_section(out.brief)
    assert "Governance-Reife" in md
    assert "Empfohlene Fokusbereiche" in md
    assert "nächste 90 Tage" in md


def test_portfolio_marker_and_tooltip_from_structured_fields() -> None:
    snap = _snap_basic_low()
    out = build_fallback_advisor_governance_maturity_brief_parse_result(snap)
    m = advisor_brief_focus_marker_de(out.brief)
    assert m.startswith("Fokus:")
    tip = advisor_brief_portfolio_tooltip_de(out.brief)
    assert "low" in tip
    assert "Zeithorizont" in tip
