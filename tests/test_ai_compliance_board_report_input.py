"""Unit-Tests: Assembler für AI-Compliance-Board-Report-Input."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db import engine
from app.repositories.ai_systems import AISystemRepository
from app.services.ai_compliance_board_report_input import (
    assemble_ai_compliance_board_report_input,
    effective_focus_keys_for_board_report,
)


def test_effective_focus_ai_act_only_overrides() -> None:
    assert effective_focus_keys_for_board_report(
        focus_framework_keys=["nis2", "dsgvo"],
        include_ai_act_only=True,
    ) == ["eu_ai_act"]


def test_assemble_input_respects_framework_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "true")
    tid = f"br-inp-{uuid.uuid4().hex[:10]}"
    with Session(engine) as s:
        inp = assemble_ai_compliance_board_report_input(
            s,
            tid,
            audience_type="board",
            language="de",
            focus_framework_keys=["eu_ai_act"],
            include_ai_act_only=False,
            ai_repo=AISystemRepository(s),
        )
        assert inp.tenant_id == tid
        assert all(f.framework_key == "eu_ai_act" for f in inp.coverage)
        assert all(g.framework_key == "eu_ai_act" for g in inp.top_gaps)
        assert inp.trend_note is not None
