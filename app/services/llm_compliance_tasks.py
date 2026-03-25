"""
Integration hooks für EU AI Act / NIS2 / ISO-42001-Reasoning über den LLMRouter.

Die Klassifikations-Engine bleibt deterministisch (Entscheidungsbaum); diese Funktionen
dienen optionaler Textanalyse, sobald Features und Provider konfiguriert sind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm_models import LLMTaskType
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def draft_legal_norm_analysis(
    tenant_id: str,
    source_text: str,
    *,
    session: Session | None = None,
) -> str:
    """Kurzanalyse / Norm-Bezug aus Freitext (LEGAL_REASONING, Claude-first)."""
    router = LLMRouter(session=session)
    prompt = (
        "Analysiere den folgenden Text im Kontext EU AI Act und NIS2-relevanter "
        "Governance-Pflichten. Antwort strukturiert mit kurzen Absätzen, auf Deutsch.\n\n"
        f"{source_text}"
    )
    return router.route_and_call(LLMTaskType.LEGAL_REASONING, prompt, tenant_id).text


def draft_structured_report_snippet(
    tenant_id: str,
    instruction_and_facts: str,
    *,
    session: Session | None = None,
    response_json: bool = False,
) -> str:
    """JSON/Markdown- oder Berichtsfragmente (STRUCTURED_OUTPUT, GPT-4o-first)."""
    router = LLMRouter(session=session)
    kwargs: dict = {}
    if response_json:
        kwargs["response_format"] = "json_object"
    return router.route_and_call(
        LLMTaskType.STRUCTURED_OUTPUT,
        instruction_and_facts,
        tenant_id,
        **kwargs,
    ).text


def draft_classification_assist(
    tenant_id: str,
    system_description: str,
    *,
    session: Session | None = None,
) -> str:
    """Heuristische Tags/Vorschläge – ersetzt nicht die deterministische Klassifikation."""
    router = LLMRouter(session=session)
    prompt = (
        "Schlage kompakte Stichworte und Risiko-Hinweise vor (keine finale Rechtsbewertung). "
        "Antwort als kurze Bullet-Liste, Deutsch.\n\n"
        f"{system_description}"
    )
    return router.route_and_call(
        LLMTaskType.CLASSIFICATION_TAGGING,
        prompt,
        tenant_id,
    ).text
