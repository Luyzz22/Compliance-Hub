"""LLM-gestützte Cross-Regulation-Gap-Empfehlungen (strukturierter JSON-Output)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from app.cross_regulation_models import (
    CrossRegLlmGapAssistantResponse,
    CrossRegLlmGapSuggestion,
    CrossRegulationGapsPayload,
)
from app.llm_models import LLMTaskType
from app.services.llm_json_utils import LLMJsonParseError, extract_json_object
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Hinterlegbar auch in n8n: System-Prompt für Cross-Regulation-Gap-Analyse (Teil B).
CROSS_REGULATION_GAP_ASSIST_SYSTEM_DE = (
    "Du bist ein erfahrener GRC-/AI-Governance-Berater für DACH (DE/AT/CH) mit Fokus auf "
    "EU AI Act, ISO 42001, ISO 27001/27701, NIS2/KRITIS-Dachgesetz und DSGVO. Deine Aufgabe "
    "ist es, Cross-Framework-Gaps für einen Mandanten zu analysieren und priorisierte, "
    "pragmatische Maßnahmen vorzuschlagen. Schreibe knapp, board-fähig, ohne Marketing-Sprache. "
    "Primär Claude-Sonnet-Niveau für Normenbezug; strukturierter JSON-Output wie gefordert."
)


def _build_user_prompt(payload: CrossRegulationGapsPayload, *, max_suggestions: int) -> str:
    compact = {
        "max_suggestions": max_suggestions,
        "tenant_industry_hint": payload.tenant_industry_hint,
        "coverage_by_framework": [c.model_dump() for c in payload.coverage],
        "gaps": [
            {
                "requirement_id": g.requirement_id,
                "framework_key": g.framework_key,
                "code": g.code,
                "title": g.title,
                "criticality": g.criticality,
                "requirement_type": g.requirement_type,
                "coverage_status": g.coverage_status,
                "linked_controls": [lc.model_dump() for lc in g.linked_controls],
            }
            for g in payload.gaps
        ],
    }
    schema_hint = (
        '{"suggestions": [\n'
        "  {\n"
        '    "requirement_ids": [1],\n'
        '    "frameworks": ["eu_ai_act"],\n'
        '    "recommendation_type": "new_control|strengthen_control|process|governance",\n'
        '    "suggested_control_name": "…",\n'
        '    "suggested_control_description": "…",\n'
        '    "rationale": "1–2 Sätze, normenreferenziert ohne Vollzitat",\n'
        '    "priority": "hoch|mittel|niedrig",\n'
        '    "suggested_owner_role": "z. B. CISO, AI Owner, Geschäftsführung",\n'
        '    "suggested_actions": ["konkrete nächste Schritte"]\n'
        "  }\n"
        "]}\n"
    )
    return (
        "Analysiere die folgende JSON-Eingabe (nur Compliance-Metadaten, keine personenbezogenen "
        "Daten, keine Dokumentinhalte).\n"
        f"Erzeuge höchstens {max_suggestions} nicht-redundante Empfehlungen; gruppiere sinnvoll "
        "über Frameworks hinweg.\n"
        "Antworte NUR mit JSON (kein Markdown), exakt mit einem Top-Level-Key suggestions:\n"
        f"{schema_hint}\n"
        f"Eingabe:\n{json.dumps(compact, ensure_ascii=False)}"
    )


def generate_cross_regulation_llm_gap_suggestions(
    payload: CrossRegulationGapsPayload,
    tenant_id: str,
    *,
    session: Session | None,
    max_suggestions: int,
) -> CrossRegLlmGapAssistantResponse:
    if not payload.gaps:
        return CrossRegLlmGapAssistantResponse(
            tenant_id=tenant_id,
            suggestions=[],
            gap_count_used=0,
        )

    user_prompt = _build_user_prompt(payload, max_suggestions=max_suggestions)
    full_prompt = f"{CROSS_REGULATION_GAP_ASSIST_SYSTEM_DE}\n\n{user_prompt}"

    router = LLMRouter(session=session)
    resp = router.route_and_call(LLMTaskType.CROSS_REGULATION_GAP_ASSIST, full_prompt, tenant_id)

    try:
        data = extract_json_object(resp.text)
    except LLMJsonParseError as exc:
        logger.warning("cross_reg_gap_llm_json_parse_failed tenant=%s err=%s", tenant_id, exc)
        raise ValueError(f"LLM output not valid JSON: {exc}") from exc

    raw = data.get("suggestions")
    if not isinstance(raw, list):
        raise ValueError("missing suggestions array")

    adapter = TypeAdapter(list[CrossRegLlmGapSuggestion])
    suggestions = adapter.validate_python(raw[:max_suggestions])

    return CrossRegLlmGapAssistantResponse(
        tenant_id=tenant_id,
        suggestions=suggestions,
        gap_count_used=len(payload.gaps),
    )
