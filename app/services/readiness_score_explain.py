"""LLM: strukturierte Erklärung zum Readiness Score (API-Enums, deutsch, kein PII)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.governance_maturity_contract import (
    readiness_explain_json_schema_instructions,
    terminology_contract_for_llm_prompt,
)
from app.llm_models import LLMTaskType
from app.readiness_score_models import ReadinessScoreExplainResponse, ReadinessScoreResponse
from app.services.llm_router import LLMRouter
from app.services.readiness_explain_structured import (
    build_readiness_explain_response_from_llm_text,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SYSTEM_PREFIX = (
    "Du bist ein Compliance-Assistenzmodell für deutschsprachige Board- und CISO-Audienz "
    "(DACH). Antworte nur mit gültigem JSON gemäß Schema — kein Markdown, keine Einleitung.\n\n"
)


def _build_system_prompt() -> str:
    return (
        _SYSTEM_PREFIX
        + terminology_contract_for_llm_prompt()
        + "\n"
        + readiness_explain_json_schema_instructions()
        + "\n"
        "Nutze ausschließlich die nachfolgenden JSON-Fakten; erfinde keine Zahlen, Mandanten "
        "oder KI-Systeme.\n"
    )


def explain_readiness_score(
    session: Session,
    tenant_id: str,
    snapshot: ReadinessScoreResponse,
) -> ReadinessScoreExplainResponse:
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        msg = "LLM features are disabled for this tenant (COMPLIANCEHUB_FEATURE_LLM_ENABLED)."
        raise PermissionError(msg)

    oami_context: dict[str, object] | None = None
    oami_index: int | None = None
    oami_level: str | None = None
    has_oami_context = False
    try:
        from app.services.oami_explanation import explain_tenant_oami_de
        from app.services.operational_monitoring_index import (
            compute_tenant_operational_monitoring_index,
        )

        oami = compute_tenant_operational_monitoring_index(
            session,
            tenant_id,
            window_days=90,
            persist_snapshot=False,
        )
        expl = explain_tenant_oami_de(oami)
        oami_index = oami.operational_monitoring_index
        oami_level = oami.level
        has_oami_context = bool(oami.has_any_runtime_data)
        oami_context = {
            "window_days": 90,
            "operational_monitoring_index": oami.operational_monitoring_index,
            "level": oami.level,
            "has_any_runtime_data": oami.has_any_runtime_data,
            "systems_scored": oami.systems_scored,
            "summary_de": expl.summary_de,
            "drivers_de": expl.drivers_de[:6],
        }
    except Exception:
        logger.exception("readiness_explain_oami_context_failed tenant=%s", tenant_id)

    gai_context: dict[str, object] | None = None
    if is_feature_enabled(FeatureFlag.governance_maturity):
        try:
            from app.services.governance_activity_index import compute_governance_activity_index

            gai = compute_governance_activity_index(
                session,
                tenant_id,
                window_days=90,
                as_of=datetime.now(UTC),
            )
            gai_context = {
                "governance_activity_index": gai.index,
                "level": gai.level,
                "window_days": gai.window_days,
            }
        except Exception:
            logger.exception("readiness_explain_gai_context_failed tenant=%s", tenant_id)

    envelope: dict[str, object] = {
        "readiness": snapshot.model_dump(mode="json"),
        "operational_ai_monitoring": oami_context,
        "governance_activity": gai_context,
    }
    facts = json.dumps(envelope, ensure_ascii=False)
    prompt = _build_system_prompt() + "\nJSON-Fakten:\n" + facts

    router = LLMRouter(session=session)
    resp = router.route_and_call(
        LLMTaskType.READINESS_SCORE_EXPLAIN,
        prompt,
        tenant_id,
        response_format="json_object",
    )
    return build_readiness_explain_response_from_llm_text(
        resp.text or "",
        snapshot=snapshot,
        oami_index=oami_index,
        oami_level=oami_level,
        has_oami_context=has_oami_context,
        provider=str(resp.provider.value),
        model_id=resp.model_id,
    )
