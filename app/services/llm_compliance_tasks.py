"""
Integration hooks für EU AI Act / NIS2 / ISO-42001-Reasoning über den LLMRouter.

Die Klassifikations-Engine bleibt deterministisch (Entscheidungsbaum); diese Funktionen
dienen optionaler Textanalyse, sobald Features und Provider konfiguriert sind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm.client_wrapped import guardrailed_route_and_call_sync
from app.llm.context import LlmCallContext
from app.llm_models import LLMDataClass, LLMTaskType

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def draft_legal_norm_analysis(
    tenant_id: str,
    source_text: str,
    *,
    session: Session | None = None,
) -> str:
    """Kurzanalyse / Norm-Bezug aus Freitext (LEGAL_REASONING, Claude-first)."""
    prompt = (
        "Analysiere den folgenden Text im Kontext EU AI Act und NIS2-relevanter "
        "Governance-Pflichten. Antwort strukturiert mit kurzen Absätzen, auf Deutsch.\n\n"
        f"{source_text}"
    )
    return guardrailed_route_and_call_sync(
        session,
        LLMTaskType.LEGAL_REASONING,
        prompt,
        tenant_id,
        context=LlmCallContext(
            tenant_id=tenant_id,
            action_name="draft_legal_norm_analysis",
            data_class=LLMDataClass.CONFIDENTIAL,
        ),
        response_format=None,
    ).text


def draft_structured_report_snippet(
    tenant_id: str,
    instruction_and_facts: str,
    *,
    session: Session | None = None,
    response_json: bool = False,
) -> str:
    """JSON/Markdown- oder Berichtsfragmente (STRUCTURED_OUTPUT, GPT-4o-first)."""
    return guardrailed_route_and_call_sync(
        session,
        LLMTaskType.STRUCTURED_OUTPUT,
        instruction_and_facts,
        tenant_id,
        context=LlmCallContext(
            tenant_id=tenant_id,
            action_name="draft_structured_report_snippet",
            data_class=LLMDataClass.CONFIDENTIAL,
        ),
        response_format="json_object" if response_json else None,
    ).text


def draft_classification_assist(
    tenant_id: str,
    system_description: str,
    *,
    session: Session | None = None,
) -> str:
    """Heuristische Tags/Vorschläge – ersetzt nicht die deterministische Klassifikation."""
    prompt = (
        "Schlage kompakte Stichworte und Risiko-Hinweise vor (keine finale Rechtsbewertung). "
        "Antwort als kurze Bullet-Liste, Deutsch.\n\n"
        f"{system_description}"
    )
    return guardrailed_route_and_call_sync(
        session,
        LLMTaskType.CLASSIFICATION_TAGGING,
        prompt,
        tenant_id,
        context=LlmCallContext(
            tenant_id=tenant_id,
            action_name="draft_classification_assist",
            data_class=LLMDataClass.CONFIDENTIAL,
        ),
        response_format=None,
    ).text
