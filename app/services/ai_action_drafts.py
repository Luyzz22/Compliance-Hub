"""Governance-Action-Entwürfe aus Lücken/Requirements (LLM, nicht persistiert)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from app.ai_governance_action_models import (
    AIGovernanceActionDraft,
    AIGovernanceActionDraftRequest,
    AIGovernanceActionDraftResponse,
)
from app.llm_models import LLMTaskType
from app.services.llm_json_utils import LLMJsonParseError, extract_json_object
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def generate_action_drafts(
    request: AIGovernanceActionDraftRequest,
    tenant_id: str,
    *,
    session: Session | None,
) -> AIGovernanceActionDraftResponse:
    if not request.requirements:
        raise ValueError("requirements must not be empty")

    reqs = json.dumps([r.model_dump() for r in request.requirements], ensure_ascii=False)
    prompt = (
        "Du erstellst Entwürfe für AI-Governance-Maßnahmen (EU AI Act, NIS2). "
        "Antworte NUR mit JSON (kein Markdown), Schema:\n"
        '{"drafts": [\n'
        '  {"title": "...", "description": "...", "framework": "EU_AI_ACT|NIS2|ISO_42001", '
        '   "reference": "z.B. Art. 9", "priority": "high|medium|low", '
        '   "suggested_role": "CISO|AI Owner|IT Ops|…"}\n'
        "]}\n"
        "2–4 sinnvolle, nicht redundante Entwürfe. Deutsch. Keine finale Rechtsbewertung.\n\n"
        f"Optional ai_system_id: {request.ai_system_id!r}\n"
        f"Requirements:\n{reqs}\n"
    )

    router = LLMRouter(session=session)
    resp = router.route_and_call(LLMTaskType.ACTION_DRAFT_GENERATION, prompt, tenant_id)

    try:
        data = extract_json_object(resp.text)
    except LLMJsonParseError as exc:
        raise ValueError(f"LLM output not valid JSON: {exc}") from exc

    raw = data.get("drafts")
    if not isinstance(raw, list):
        raise ValueError("missing drafts array")

    drafts = TypeAdapter(list[AIGovernanceActionDraft]).validate_python(raw)
    return AIGovernanceActionDraftResponse(ai_system_id=request.ai_system_id, drafts=drafts)
