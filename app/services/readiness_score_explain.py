"""LLM: kurze Erklärung zum Readiness Score (aggregierte Kennzahlen, keine PII)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm_models import LLMTaskType
from app.readiness_score_models import ReadinessScoreExplainResponse, ReadinessScoreResponse
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Du erklärst CxOs und CISOs in DACH in 3–5 Sätzen, wie ein AI & Compliance Readiness Score "
    "zustande kommt und welche Top-3-Maßnahmen sinnvoll sind. Nutze klare Sprache, keine "
    "Normzitate. Nutze ausschließlich die JSON-Fakten; erfinde keine Zahlen.\n\n"
    "Struktur: (1) Kurz einordnen, warum Level und Score plausibel sind. "
    "(2) Genau drei nummerierte, priorisierte Maßnahmen."
)


def explain_readiness_score(
    session: Session,
    tenant_id: str,
    snapshot: ReadinessScoreResponse,
) -> ReadinessScoreExplainResponse:
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        msg = "LLM features are disabled for this tenant (COMPLIANCEHUB_FEATURE_LLM_ENABLED)."
        raise PermissionError(msg)

    facts = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False)
    prompt = _SYSTEM + "\n\nJSON-Fakten:\n" + facts

    router = LLMRouter(session=session)
    resp = router.route_and_call(
        LLMTaskType.READINESS_SCORE_EXPLAIN,
        prompt,
        tenant_id,
    )
    return ReadinessScoreExplainResponse(
        explanation=(resp.text or "").strip(),
        provider=str(resp.provider.value),
        model_id=resp.model_id,
    )
