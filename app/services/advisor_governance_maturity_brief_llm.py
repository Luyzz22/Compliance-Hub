"""LLM: Advisor Governance-Maturity-Brief (JSON mode, Parse + Fallback)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.governance_maturity_models import GovernanceMaturityResponse
from app.governance_maturity_summary_models import GovernanceMaturitySummary
from app.llm_models import LLMTaskType
from app.services.advisor_governance_maturity_brief_parse import (
    AdvisorGovernanceMaturityBriefParseResult,
    build_fallback_advisor_governance_maturity_brief_parse_result,
    parse_advisor_governance_maturity_brief,
)
from app.services.advisor_governance_maturity_brief_prompt import (
    build_advisor_governance_maturity_brief_prompt,
)
from app.services.governance_maturity_service import build_governance_maturity_response
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def render_advisor_governance_maturity_brief(
    session: Session | None,
    tenant_id: str,
    snapshot: GovernanceMaturityResponse,
    board_summary: GovernanceMaturitySummary | None = None,
) -> AdvisorGovernanceMaturityBriefParseResult:
    prompt = build_advisor_governance_maturity_brief_prompt(
        snapshot,
        board_summary,
    )
    router = LLMRouter(session=session)
    try:
        resp = router.route_and_call(
            LLMTaskType.ADVISOR_GOVERNANCE_MATURITY_BRIEF,
            prompt,
            tenant_id,
            response_format="json_object",
        )
    except Exception:
        logger.exception("advisor_governance_maturity_brief_llm_failed tenant=%s", tenant_id)
        return build_fallback_advisor_governance_maturity_brief_parse_result(snapshot)
    return parse_advisor_governance_maturity_brief(resp.text or "", snapshot)


def maybe_build_advisor_governance_maturity_brief_result(
    session: Session | None,
    tenant_id: str,
    *,
    board_summary: GovernanceMaturitySummary | None = None,
) -> AdvisorGovernanceMaturityBriefParseResult | None:
    """
    Wenn Governance-Maturity aktiv: Brief (LLM falls erlaubt, sonst deterministisch).

    Gibt None zurück, wenn das Feature abgeschaltet ist.
    """
    if not is_feature_enabled(FeatureFlag.governance_maturity, tenant_id, session=session):
        return None
    try:
        snapshot = build_governance_maturity_response(session, tenant_id)
    except Exception:
        logger.exception("advisor_brief_snapshot_failed tenant=%s", tenant_id)
        return None

    if is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        return render_advisor_governance_maturity_brief(
            session,
            tenant_id,
            snapshot,
            board_summary=board_summary,
        )
    return build_fallback_advisor_governance_maturity_brief_parse_result(snapshot)
