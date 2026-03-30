"""LLM: strukturierte Erklärung zum Readiness Score (API-Enums, deutsch, kein PII)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm.client_wrapped import guardrailed_route_and_call_sync
from app.llm.context import LlmCallContext
from app.llm_models import LLMTaskType
from app.readiness_score_models import ReadinessScoreExplainResponse, ReadinessScoreResponse
from app.services.readiness_explain_prompt import build_readiness_explain_prompt
from app.services.readiness_explain_structured import parse_and_validate_readiness_explain_response

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def explain_readiness_score(
    session: Session,
    tenant_id: str,
    snapshot: ReadinessScoreResponse,
    *,
    llm_call_context: LlmCallContext | None = None,
) -> ReadinessScoreExplainResponse:
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        msg = "LLM features are disabled for this tenant (COMPLIANCEHUB_FEATURE_LLM_ENABLED)."
        raise PermissionError(msg)

    oami_context: dict[str, object] | None = None
    oami_index: int | None = None
    oami_level: str | None = None
    has_oami_context = False
    oami_enrichment: dict[str, object] | None = None
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
            "runtime_incident_by_subtype": oami.runtime_incident_by_subtype,
            "safety_related_runtime_incidents_90d": oami.safety_related_runtime_incident_count,
            "availability_runtime_incidents_90d": oami.availability_runtime_incident_count,
            "oami_operational_hint_de": oami.oami_operational_hint_de,
            "oami_subtype_note": (
                "Laufzeit-Incidents können z. B. Subtypes safety_violation oder "
                "availability_incident tragen; sicherheitsrelevante Subtypes zählen im Index "
                "stärker als reine Verfügbarkeit (keine Gewichtszahlen nennen)."
            ),
        }
        if oami.has_any_runtime_data:
            oami_enrichment = {
                "safety_related_incidents_90d": oami.safety_related_runtime_incident_count,
                "availability_incidents_90d": oami.availability_runtime_incident_count,
                "oami_subtype_hint_de": oami.oami_operational_hint_de,
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
    prompt = build_readiness_explain_prompt(facts_envelope=envelope)
    ctx = llm_call_context or LlmCallContext(
        tenant_id=tenant_id,
        action_name="readiness_score_explain",
    )
    resp = guardrailed_route_and_call_sync(
        session,
        LLMTaskType.READINESS_SCORE_EXPLAIN,
        prompt,
        tenant_id,
        context=ctx,
        response_format="json_object",
    )
    return parse_and_validate_readiness_explain_response(
        resp.text or "",
        snapshot=snapshot,
        oami_index=oami_index,
        oami_level=oami_level,
        has_oami_context=has_oami_context,
        provider=str(resp.provider.value),
        model_id=resp.model_id,
        oami_operational_enrichment=oami_enrichment,
    )
