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

from app.advisor.sensitive_topics import SensitiveTopicResult, check_sensitive_topic
from app.advisor.templates import (
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PROHIBITED_TOPIC,
    format_escalation,
    format_normal_answer,
    format_sensitive_refusal,
)
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
    sensitive_topic: SensitiveTopicResult | None = None
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


def check_sensitive_topics(state: AdvisorState) -> AdvisorState:
    """Rule-based check for sensitive / prohibited AI Act topics."""
    result = check_sensitive_topic(state.query)
    state.sensitive_topic = result
    state.agent_trace.append(
        {
            "node": "check_sensitive_topics",
            "is_sensitive": result.is_sensitive,
            "is_prohibited": result.is_prohibited,
            "matched_rule_id": result.matched_rule_id,
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
    - Sensitive topic + low or medium confidence
    - Tenant has guidance docs but retrieval returned only global law
    - confidence_level == "low"
    Sensitive topic check runs first (most conservative).
    Tenant guidance check runs before general low-confidence.
    """
    st = state.sensitive_topic
    if st and st.is_sensitive and state.confidence_level in ("low", "medium"):
        state.escalation_reason = (
            f"Sensibles Thema erkannt (Regel: {st.matched_rule_id}) "
            f"bei unzureichender Konfidenz ({state.confidence_level})."
        )
        return "escalate"

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
    state.answer = format_normal_answer(response.text)

    log_rag_query_event(
        response=state.retrieval_response,
        tenant_id=state.tenant_id,
        agent_action="synthesize_answer",
        query_text=state.query,
        persist_evidence=False,
    )

    synth_status = "success" if not response.error else "fallback"
    state.agent_trace.append(
        {
            "node": "synthesize_answer",
            "status": synth_status,
            "model_id": response.model_id,
            "latency_ms": response.latency_ms,
        }
    )
    log_advisor_agent_event(
        tenant_id=state.tenant_id,
        decision="answered",
        intent=str(state.intent),
        extra={"synthesis_status": synth_status},
    )
    return state


def escalate_to_human(state: AdvisorState) -> AdvisorState:
    """Terminal node: recommend human review."""
    state.is_escalated = True
    if not state.escalation_reason:
        state.escalation_reason = "Thema außerhalb des automatisierten Beratungsbereichs."

    st = state.sensitive_topic
    if st and st.is_prohibited:
        state.answer = REFUSAL_PROHIBITED_TOPIC
        policy_rule_id = "prohibited_topic"
    elif st and st.is_sensitive:
        state.answer = format_sensitive_refusal(state.escalation_reason)
        policy_rule_id = f"sensitive_{st.matched_rule_id}"
    elif state.intent == IntentType.out_of_scope:
        state.answer = REFUSAL_OUT_OF_SCOPE
        policy_rule_id = "out_of_scope"
    else:
        state.answer = format_escalation(state.escalation_reason)
        policy_rule_id = "low_confidence"

    log_entry: dict[str, Any] = {
        "node": "escalate_to_human",
        "reason": state.escalation_reason,
        "confidence_level": state.confidence_level,
        "policy_rule_id": policy_rule_id,
    }
    if st and st.is_sensitive:
        log_entry["sensitive_matched_term"] = st.matched_term
        log_entry["sensitive_rule_id"] = st.matched_rule_id
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
        extra={"policy_rule_id": policy_rule_id},
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

        state = check_sensitive_topics(state)

        if state.sensitive_topic and state.sensitive_topic.is_prohibited:
            state.escalation_reason = (
                f"Verbotenes Thema erkannt: {state.sensitive_topic.matched_term}"
            )
            state = escalate_to_human(state)
            return state

        state = run_rag_query(state, self.retriever)

        decision = check_confidence(state, self.tenant_has_guidance)

        if decision == "escalate":
            state = escalate_to_human(state)
        else:
            state = synthesize_answer(state, llm_fn=self.llm_fn)

        return state
