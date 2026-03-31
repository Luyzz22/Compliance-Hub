"""Kurzerklärungen zu Board-KPIs und Alerts (LLM, nicht persistiert)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from app.explain_models import ExplainRequest, ExplainResponse
from app.llm_models import LLMTaskType
from app.services.llm_json_utils import LLMJsonParseError, extract_json_object
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def explain_kpi_or_alert(
    request: ExplainRequest,
    tenant_id: str,
    *,
    session: Session | None,
) -> ExplainResponse:
    ctx = request.tenant_context.model_dump(exclude_none=True) if request.tenant_context else {}
    prompt = (
        "Du erklärst Governance-KPIs für Vorstand und Compliance (DACH). "
        "Antworte NUR mit JSON (kein Markdown), Schema:\n"
        '{"title": "...", "summary": "2-3 Sätze deutsch", '
        '"why_it_matters": ["Bullet 1", "Bullet 2"], '
        '"suggested_actions": ["kurze Maßnahme 1", "…"]}\n'
        "Bezug: NIS2 (z.B. Art. 21 Meldepflichten), EU AI Act High-Risk-Pflichten, ISO 42001 "
        "AI-Management wo passend. Keine Rechtsberatung; sachlich und vorsichtig formulieren.\n\n"
        f"kpi_key: {request.kpi_key}\n"
        f"current_value: {request.current_value}\n"
        f"value_is_percent: {request.value_is_percent}\n"
        f"alert_key: {request.alert_key}\n"
        f"threshold_warning: {request.threshold_warning}\n"
        f"threshold_critical: {request.threshold_critical}\n"
        f"tenant_context: {ctx}\n"
    )

    router = LLMRouter(session=session)
    resp = router.route_and_call(LLMTaskType.EXPLAIN_KPI_ALERT, prompt, tenant_id)

    try:
        data = extract_json_object(resp.text)
    except LLMJsonParseError as exc:
        raise ValueError(f"LLM output not valid JSON: {exc}") from exc

    return TypeAdapter(ExplainResponse).validate_python(data)
