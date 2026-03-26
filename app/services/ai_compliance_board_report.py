"""Orchestrierung: AI-Compliance-Board-Report inkl. optionalem Gap-Assist und Persistenz."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.ai_compliance_board_report_models import (
    AiComplianceBoardReportCreateBody,
    AiComplianceBoardReportCreateResponse,
    AiComplianceBoardReportDetailResponse,
    AiComplianceBoardReportInput,
    AiComplianceBoardReportListItem,
    CompressedGapSuggestion,
)
from app.cross_regulation_models import CrossRegLlmGapSuggestion
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.cross_regulation import CrossRegulationRepository
from app.services.ai_compliance_board_report_input import (
    assemble_ai_compliance_board_report_input,
    effective_focus_keys_for_board_report,
)
from app.services.ai_compliance_board_report_llm import render_ai_compliance_board_report_markdown
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps
from app.services.cross_regulation_llm_gap_assistant import (
    generate_cross_regulation_llm_gap_suggestions,
)
from app.services.governance_maturity_board_summary_llm import (
    maybe_build_governance_maturity_board_summary_result,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _compress_gap_suggestions(
    suggestions: list[CrossRegLlmGapSuggestion],
    id_to_code: dict[int, str],
) -> list[CompressedGapSuggestion]:
    out: list[CompressedGapSuggestion] = []
    for s in suggestions[:8]:
        codes = [id_to_code.get(rid, str(rid)) for rid in s.requirement_ids[:16]]
        out.append(
            CompressedGapSuggestion(
                suggested_control_name=s.suggested_control_name,
                priority=s.priority,
                frameworks=list(s.frameworks),
                requirement_codes=codes,
                recommendation_type=s.recommendation_type,
            )
        )
    return out


def _maybe_enrich_with_gap_assist(
    session: Session,
    tenant_id: str,
    inp: AiComplianceBoardReportInput,
    *,
    focus_framework_keys: list[str] | None,
    include_ai_act_only: bool,
) -> AiComplianceBoardReportInput:
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        return inp
    if not is_feature_enabled(
        FeatureFlag.cross_regulation_llm_assist,
        tenant_id,
        session=session,
    ):
        return inp
    eff = effective_focus_keys_for_board_report(
        focus_framework_keys=focus_framework_keys,
        include_ai_act_only=include_ai_act_only,
    )
    try:
        gaps_payload = compute_cross_regulation_gaps(
            session,
            tenant_id,
            focus_framework_keys=eff,
        )
        gap_resp = generate_cross_regulation_llm_gap_suggestions(
            gaps_payload,
            tenant_id,
            session=session,
            max_suggestions=6,
        )
        req_map = {
            int(r.id): r.code for r in CrossRegulationRepository(session).list_requirements()
        }
        hints = _compress_gap_suggestions(gap_resp.suggestions, req_map)
        return inp.model_copy(update={"gap_assist_hints": hints})
    except Exception as exc:
        logger.info(
            "board_report_gap_assist_skipped tenant=%s reason=%s",
            tenant_id,
            type(exc).__name__,
        )
        return inp


def create_ai_compliance_board_report(
    session: Session,
    tenant_id: str,
    body: AiComplianceBoardReportCreateBody,
    *,
    created_by: str | None,
) -> AiComplianceBoardReportCreateResponse:
    ai_repo = AISystemRepository(session)
    inp = assemble_ai_compliance_board_report_input(
        session,
        tenant_id,
        audience_type=body.audience_type,
        language=body.language,
        focus_framework_keys=body.focus_frameworks,
        include_ai_act_only=body.include_ai_act_only,
        ai_repo=ai_repo,
    )
    inp = _maybe_enrich_with_gap_assist(
        session,
        tenant_id,
        inp,
        focus_framework_keys=body.focus_frameworks,
        include_ai_act_only=body.include_ai_act_only,
    )

    gm_result = maybe_build_governance_maturity_board_summary_result(session, tenant_id)
    if gm_result is not None:
        inp = inp.model_copy(
            update={
                "governance_maturity_summary": gm_result.summary,
                "governance_maturity_executive_paragraph_de": (
                    gm_result.executive_overview_governance_maturity_de
                ),
            },
        )

    md = render_ai_compliance_board_report_markdown(inp, tenant_id, session=session)
    if not md.strip():
        md = (
            "## Executive Overview\n\n"
            "*Es konnte kein KI-Text erzeugt werden. Bitte LLM-Konfiguration und "
            "Feature-Flags prüfen.*\n"
        )

    now = datetime.now(UTC)
    title = (
        f"AI Compliance Board-Report – "
        f"{body.audience_type.replace('_', ' ')} – {now.strftime('%Y-%m-%d %H:%M')} UTC"
    )
    raw_payload: dict = {
        "version": 1,
        "focus_frameworks": body.focus_frameworks,
        "include_ai_act_only": body.include_ai_act_only,
        "language": body.language,
        "input": inp.model_dump(),
        "governance_maturity_board_summary": (
            {
                "parse_ok": gm_result.parse_ok,
                "used_llm_paragraph": gm_result.used_llm_paragraph,
                "summary": gm_result.summary.model_dump(),
            }
            if gm_result is not None
            else None
        ),
    }

    repo = AiComplianceBoardReportRepository(session)
    row = repo.create(
        tenant_id=tenant_id,
        created_by=created_by,
        title=title,
        audience_type=body.audience_type,
        raw_payload=raw_payload,
        rendered_markdown=md,
        rendered_html=None,
        period_start=body.period_start,
        period_end=body.period_end,
    )

    return AiComplianceBoardReportCreateResponse(
        report_id=row.id,
        title=row.title,
        rendered_markdown=row.rendered_markdown,
        coverage_snapshot=inp.coverage,
        created_at=row.created_at_utc.isoformat(),
        audience_type=row.audience_type,
    )


def list_ai_compliance_board_reports(
    session: Session,
    tenant_id: str,
    *,
    limit: int = 50,
) -> list[AiComplianceBoardReportListItem]:
    repo = AiComplianceBoardReportRepository(session)
    rows = repo.list_for_tenant(tenant_id, limit=limit)
    return [
        AiComplianceBoardReportListItem(
            id=r.id,
            title=r.title,
            audience_type=r.audience_type,
            created_at=r.created_at_utc.isoformat(),
        )
        for r in rows
    ]


def get_ai_compliance_board_report_detail(
    session: Session,
    tenant_id: str,
    report_id: str,
) -> AiComplianceBoardReportDetailResponse | None:
    repo = AiComplianceBoardReportRepository(session)
    row = repo.get(report_id, tenant_id)
    if row is None:
        return None
    return AiComplianceBoardReportDetailResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        audience_type=row.audience_type,
        created_at=row.created_at_utc.isoformat(),
        rendered_markdown=row.rendered_markdown,
        raw_payload=row.raw_payload if isinstance(row.raw_payload, dict) else {},
    )
