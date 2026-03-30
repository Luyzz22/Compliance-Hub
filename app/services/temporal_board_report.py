"""Business helpers for the Temporal Board Report pilot (snapshot load + persist)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast

from app.ai_compliance_board_report_models import AiComplianceBoardReportInput
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.ai_systems import AISystemRepository
from app.services.ai_compliance_board_report_input import assemble_ai_compliance_board_report_input
from app.services.ai_compliance_board_report_llm import (
    render_ai_compliance_board_report_markdown_guardrailed,
)
from app.services.governance_maturity_service import build_governance_maturity_response
from app.services.governance_maturity_summary_parse import (
    build_fallback_governance_maturity_board_summary_parse_result,
)
from app.services.readiness_score_service import compute_readiness_score
from app.workflows.board_report import BoardReportWorkflowInput

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _pick_primary_ai_system_id(
    session: Session,
    tenant_id: str,
    override: str | None,
) -> str | None:
    if override and override.strip():
        row = AISystemRepository(session).get_by_id(tenant_id, override.strip())
        if row is not None:
            return row.id
    systems = AISystemRepository(session).list_for_tenant(tenant_id)
    for s in systems:
        rl = str(s.risk_level or "").lower()
        if rl in ("high", "unacceptable"):
            return s.id
    if systems:
        return systems[0].id
    return None


def load_tenant_snapshot_for_board_report(
    session: Session,
    inp: BoardReportWorkflowInput,
) -> dict:
    """
    Deterministic DB-backed snapshot: coverage, gaps, OAMI profile, readiness, governance (no LLM).
    """
    ai_repo = AISystemRepository(session)
    audience = cast(
        Literal["board", "management", "advisor_client"],
        inp.audience_type
        if inp.audience_type in ("board", "management", "advisor_client")
        else "board",
    )
    assembled = assemble_ai_compliance_board_report_input(
        session,
        inp.tenant_id,
        audience_type=audience,
        language=inp.language or "de",
        focus_framework_keys=inp.focus_frameworks or None,
        include_ai_act_only=bool(inp.include_ai_act_only),
        ai_repo=ai_repo,
    )
    primary_id = _pick_primary_ai_system_id(session, inp.tenant_id, inp.primary_ai_system_id)

    readiness_dump: dict | None = None
    if is_feature_enabled(FeatureFlag.readiness_score, inp.tenant_id, session=session):
        try:
            readiness_dump = compute_readiness_score(session, inp.tenant_id).model_dump(
                mode="json",
            )
        except Exception:
            logger.exception("temporal_board_report_readiness_failed tenant=%s", inp.tenant_id)

    governance_dump: dict | None = None
    gm_inp = assembled
    if is_feature_enabled(FeatureFlag.governance_maturity, inp.tenant_id, session=session):
        try:
            snap = build_governance_maturity_response(session, inp.tenant_id)
            fb = build_fallback_governance_maturity_board_summary_parse_result(snap)
            gm_inp = assembled.model_copy(
                update={
                    "governance_maturity_summary": fb.summary,
                    "governance_maturity_executive_paragraph_de": (
                        fb.executive_overview_governance_maturity_de
                    ),
                },
            )
            governance_dump = {
                "parse_ok": fb.parse_ok,
                "used_llm_paragraph": fb.used_llm_paragraph,
                "summary": fb.summary.model_dump(mode="json"),
            }
        except Exception:
            logger.exception("temporal_board_report_governance_failed tenant=%s", inp.tenant_id)

    return {
        "assembled_input": gm_inp.model_dump(mode="json"),
        "primary_ai_system_id": primary_id,
        "snapshot_reference": inp.snapshot_reference,
        "readiness_score": readiness_dump,
        "governance_maturity_board_summary": governance_dump,
    }


def persist_versioned_board_report_from_workflow(
    session: Session,
    *,
    tenant_id: str,
    user_role: str,
    workflow_input_dict: dict,
    snapshot: dict,
    oami_explanation: dict,
    temporal_workflow_id: str,
    temporal_run_id: str,
) -> str:
    """OPA + guardrailed board markdown, then versioned ai_compliance_board_reports row."""
    from app.policy.opa_client import evaluate_action_policy

    decision = evaluate_action_policy(
        {
            "tenant_id": tenant_id,
            "user_role": user_role or "tenant_admin",
            "action": "generate_board_report",
            "risk_score": 0.75,
        },
    )
    if not decision.allowed:
        raise PermissionError("OPA denied board report generation for persist activity")

    assembled_raw = snapshot.get("assembled_input") or {}
    body_audience = workflow_input_dict.get("audience_type") or "board"
    audience = cast(
        Literal["board", "management", "advisor_client"],
        body_audience
        if body_audience in ("board", "management", "advisor_client")
        else "board",
    )
    inp = AiComplianceBoardReportInput.model_validate({**assembled_raw, "tenant_id": tenant_id})
    primary = snapshot.get("primary_ai_system_id")
    inp = inp.model_copy(
        update={
            "audience_type": audience,
            "temporal_langgraph_oami_system_id": str(primary) if primary else None,
            "temporal_langgraph_oami_explanation": oami_explanation if oami_explanation else None,
        },
    )

    md = render_ai_compliance_board_report_markdown_guardrailed(
        inp,
        tenant_id,
        session=session,
        user_role=user_role,
    )
    if not md.strip():
        md = (
            "## Executive Overview\n\n"
            "*Es konnte kein KI-Text erzeugt werden. Bitte LLM-Konfiguration und "
            "Feature-Flags prüfen.*\n"
        )

    now = datetime.now(UTC)
    title = (
        f"AI Compliance Board-Report (Temporal) – "
        f"{audience.replace('_', ' ')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"
    )
    raw_payload: dict = {
        "version": 2,
        "source": "temporal_board_report_workflow",
        "temporal_workflow_id": temporal_workflow_id,
        "temporal_run_id": temporal_run_id,
        "snapshot_reference": snapshot.get("snapshot_reference"),
        "focus_frameworks": workflow_input_dict.get("focus_frameworks"),
        "include_ai_act_only": workflow_input_dict.get("include_ai_act_only"),
        "language": workflow_input_dict.get("language"),
        "input": inp.model_dump(mode="json"),
        "readiness_score": snapshot.get("readiness_score"),
        "governance_maturity_board_summary": snapshot.get("governance_maturity_board_summary"),
        "langgraph_oami_explanation": oami_explanation or None,
    }

    repo = AiComplianceBoardReportRepository(session)
    row = repo.create(
        tenant_id=tenant_id,
        created_by="temporal:board_report_workflow",
        title=title,
        audience_type=audience,
        raw_payload=raw_payload,
        rendered_markdown=md,
        rendered_html=None,
        period_start=None,
        period_end=None,
    )
    return row.id
