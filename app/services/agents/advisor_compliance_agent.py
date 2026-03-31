"""AdvisorComplianceAgent — LangGraph agent for compliance advisory queries.

Graph structure (small, explicit, no self-modifying loops):

    START → classify_intent
                │
        ┌───────┼───────┐
        ▼       ▼       ▼
   run_rag   escalate  END (out_of_scope)
        │
        ▼
   check_confidence
        │
    ┌───┴───┐
    ▼       ▼
 synthesize escalate
    │       │
    ▼       ▼
   END     END

All LLM calls go through safe_llm_call_sync with LlmCallContext.
Agent decisions are logged as structured events for AI Act evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from app.services.rag.corpus import RetrievalResponse
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallable, LlmCallContext, LlmResponse, safe_llm_call_sync
from app.services.rag.logging import log_advisor_agent_event, log_rag_query_event
from app.services.rag.prompt_builder import build_rag_prompt

logger = logging.getLogger(__name__)


class IntentType(StrEnum):
    informational = "informational"
    action_oriented = "action_oriented"
    out_of_scope = "out_of_scope"


@dataclass
class AdvisorState:
    """Immutable-style state passed through the graph."""

    query: str = ""
    tenant_id: str = ""
    intent: IntentType = IntentType.informational
    retrieval_response: RetrievalResponse | None = None
    answer: str = ""
    escalation_reason: str = ""
    is_escalated: bool = False
    confidence_level: str = "low"
    agent_trace: list[dict[str, Any]] = field(default_factory=list)
    """Ordered list of node executions + decisions for audit trail."""


_INTENT_KEYWORDS_OUT_OF_SCOPE = frozenset(
    {
        "wetter",
        "fussball",
        "rezept",
        "urlaub",
        "sport",
        "kino",
        "musik",
    }
)

_INTENT_KEYWORDS_ACTION = frozenset(
    {
        "erstelle",
        "generiere",
        "berechne",
        "aktualisiere",
        "sende",
        "melde",
        "exportiere",
        "registriere",
        "lösche",
    }
)


def classify_intent(state: AdvisorState) -> AdvisorState:
    """Simple keyword-based intent classifier (no LLM needed).

    Categorizes as informational, action_oriented, or out_of_scope.
    """
    import re

    query_lower = state.query.lower()
    tokens = set(re.findall(r"\w+", query_lower))

    if tokens & _INTENT_KEYWORDS_OUT_OF_SCOPE:
        state.intent = IntentType.out_of_scope
    elif tokens & _INTENT_KEYWORDS_ACTION:
        state.intent = IntentType.action_oriented
    else:
        state.intent = IntentType.informational

    state.agent_trace.append(
        {
            "node": "classify_intent",
            "intent": state.intent.value,
        }
    )
    return state


def run_rag_query(
    state: AdvisorState,
    retriever: HybridRetriever,
) -> AdvisorState:
    """Execute RAG retrieval using the configured pipeline."""
    response = retriever.retrieve(state.query)
    state.retrieval_response = response
    state.confidence_level = response.confidence_level

    log_rag_query_event(
        response=response,
        tenant_id=state.tenant_id,
        query_text=state.query,
        persist_evidence=True,
    )

    state.agent_trace.append(
        {
            "node": "run_rag_query",
            "retrieval_mode": response.retrieval_mode,
            "confidence_level": response.confidence_level,
            "confidence_score": response.confidence_score,
            "result_count": len(response.results),
            "has_tenant_guidance": response.has_tenant_guidance,
        }
    )
    return state


def check_confidence(
    state: AdvisorState,
    tenant_has_guidance: bool = False,
) -> Literal["synthesize", "escalate"]:
    """Policy gate: decide whether to auto-answer or escalate.

    Forces escalation when:
    - Tenant has guidance docs but retrieval returned only global law
    - confidence_level == "low"
    Tenant guidance check runs first so the escalation reason is specific.
    """
    if (
        tenant_has_guidance
        and state.retrieval_response
        and not state.retrieval_response.has_tenant_guidance
    ):
        state.escalation_reason = (
            "Mandantenspezifische Guidance vorhanden, aber nicht in den "
            "Retrievalergebnissen — menschliche Prüfung empfohlen."
        )
        return "escalate"

    if state.confidence_level == "low":
        state.escalation_reason = (
            "Geringe Konfidenz der Quellenübereinstimmung — menschliche Prüfung empfohlen."
        )
        return "escalate"

    return "synthesize"


def synthesize_answer(
    state: AdvisorState,
    llm_fn: LlmCallable | None = None,
) -> AdvisorState:
    """LLM node: generate a structured German advisory answer from RAG citations."""
    if not state.retrieval_response:
        state.answer = "Keine Quellen verfügbar."
        state.agent_trace.append({"node": "synthesize_answer", "status": "no_sources"})
        return state

    prompt = build_rag_prompt(state.query, state.retrieval_response)
    context = LlmCallContext(
        tenant_id=state.tenant_id,
        role="advisor",
        action="advisor_rag_answer_synthesis",
    )

    response: LlmResponse = safe_llm_call_sync(prompt, context, llm_fn=llm_fn)
    state.answer = response.text

    log_rag_query_event(
        response=state.retrieval_response,
        tenant_id=state.tenant_id,
        agent_action="synthesize_answer",
        query_text=state.query,
        persist_evidence=False,
    )

    state.agent_trace.append(
        {
            "node": "synthesize_answer",
            "status": "success" if not response.error else "fallback",
            "model_id": response.model_id,
            "latency_ms": response.latency_ms,
        }
    )
    return state


def escalate_to_human(state: AdvisorState) -> AdvisorState:
    """Terminal node: recommend human review."""
    state.is_escalated = True
    if not state.escalation_reason:
        state.escalation_reason = "Thema außerhalb des automatisierten Beratungsbereichs."

    state.answer = (
        f"⚠️ Menschliche Prüfung empfohlen.\n\n"
        f"Grund: {state.escalation_reason}\n\n"
        f"Ihre Anfrage wurde zur Überprüfung durch einen Compliance-Berater markiert."
    )

    log_entry = {
        "node": "escalate_to_human",
        "reason": state.escalation_reason,
        "confidence_level": state.confidence_level,
    }
    state.agent_trace.append(log_entry)

    logger.info(
        "agent_escalation",
        extra={"escalation": log_entry, "tenant_id": state.tenant_id},
    )
    log_advisor_agent_event(
        tenant_id=state.tenant_id,
        decision="escalate_to_human",
        reason=state.escalation_reason,
        intent=str(state.intent),
    )
    return state


class AdvisorComplianceAgent:
    """Orchestrator that runs the advisor graph nodes in sequence.

    Same semantics as ``build_advisor_compliance_langgraph`` in
    ``advisor_langgraph.py`` (optional ``langgraph`` dependency).
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        llm_fn: LlmCallable | None = None,
        tenant_has_guidance: bool = False,
    ) -> None:
        self.retriever = retriever
        self.llm_fn = llm_fn
        self.tenant_has_guidance = tenant_has_guidance

    def run(self, query: str, tenant_id: str = "", trace_id: str | None = None) -> AdvisorState:
        state = AdvisorState(query=query, tenant_id=tenant_id)
        if trace_id:
            state.agent_trace.append({"node": "workflow_context", "trace_id": trace_id})

        state = classify_intent(state)

        if state.intent == IntentType.out_of_scope:
            state.escalation_reason = "Anfrage liegt außerhalb des Compliance-Beratungsbereichs."
            state = escalate_to_human(state)
            return state

        state = run_rag_query(state, self.retriever)

        decision = check_confidence(state, self.tenant_has_guidance)

        if decision == "escalate":
            state = escalate_to_human(state)
        else:
            state = synthesize_answer(state, llm_fn=self.llm_fn)

        return state
