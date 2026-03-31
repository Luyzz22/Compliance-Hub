"""LLM call: governance maturity executive summary JSON + Board paragraph."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.governance_maturity_models import GovernanceMaturityResponse
from app.llm_models import LLMTaskType
from app.services.governance_maturity_service import build_governance_maturity_response
from app.services.governance_maturity_summary_parse import (
    GovernanceMaturityBoardSummaryParseResult,
    build_fallback_governance_maturity_board_summary_parse_result,
    parse_governance_maturity_board_summary,
)
from app.services.governance_maturity_summary_prompt import build_governance_maturity_summary_prompt
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def render_governance_maturity_board_summary(
    session: Session | None,
    tenant_id: str,
    snapshot: GovernanceMaturityResponse,
) -> GovernanceMaturityBoardSummaryParseResult:
    """
    Invoke LLM with JSON mode; parse and align to snapshot; fallback on errors.
    """
    prompt = build_governance_maturity_summary_prompt(snapshot)
    router = LLMRouter(session=session)
    try:
        resp = router.route_and_call(
            LLMTaskType.GOVERNANCE_MATURITY_BOARD_SUMMARY,
            prompt,
            tenant_id,
            response_format="json_object",
        )
    except Exception:
        logger.exception("governance_maturity_board_summary_llm_failed tenant=%s", tenant_id)
        return build_fallback_governance_maturity_board_summary_parse_result(snapshot)
    return parse_governance_maturity_board_summary(resp.text or "", snapshot)


def maybe_build_governance_maturity_board_summary_result(
    session: Session | None,
    tenant_id: str,
) -> GovernanceMaturityBoardSummaryParseResult | None:
    """
    When governance maturity is enabled: return summary (LLM if allowed, else deterministic).

    Returns None when governance maturity feature is off.
    """
    if not is_feature_enabled(FeatureFlag.governance_maturity, tenant_id, session=session):
        return None
    try:
        snapshot = build_governance_maturity_response(session, tenant_id)
    except Exception:
        logger.exception("governance_maturity_snapshot_for_board_failed tenant=%s", tenant_id)
        return None

    if is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        return render_governance_maturity_board_summary(session, tenant_id, snapshot)
    det = build_fallback_governance_maturity_board_summary_parse_result(snapshot)
    return det.model_copy(update={"parse_ok": True})
