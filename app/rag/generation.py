"""Guardrailed LLM generation step for EU regulatory RAG."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.llm.client_wrapped import safe_llm_call_sync
from app.llm.context import LlmCallContext
from app.llm_models import LLMTaskType
from app.rag.models import EuRegRagLlmOutput

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def generate_eu_reg_rag_llm_output(
    prompt: str,
    *,
    tenant_id: str,
    user_role: str,
    session: Session | None,
) -> EuRegRagLlmOutput:
    ctx = LlmCallContext(
        tenant_id=tenant_id.strip(),
        user_role=(user_role or "").strip(),
        action_name="advisor_rag_eu_ai_act_nis2_query",
    )
    try:
        return safe_llm_call_sync(
            prompt,
            EuRegRagLlmOutput,
            context=ctx,
            session=session,
            task_type=LLMTaskType.ADVISOR_REGULATORY_RAG,
        )
    except Exception as exc:
        logger.exception(
            "eu_reg_rag_generator_failed tenant=%s err=%s",
            tenant_id,
            type(exc).__name__,
        )
        return EuRegRagLlmOutput(
            answer_de=(
                "Die KI-Antwort konnte nicht verlässlich erzeugt werden. "
                "Bitte LLM-Konfiguration prüfen."
            ),
            citations=[],
        )
