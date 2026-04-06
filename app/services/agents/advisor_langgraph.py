"""LangGraph ``StateGraph`` for AdvisorComplianceAgent (Wave 6.1).

Mirrors the explicit control flow in ``advisor_compliance_agent`` with the same
node functions — no unbounded loops.
Requires ``langgraph`` (``pip install 'compliancehub[agents]'``).
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.services.agents import advisor_compliance_agent as aca
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallable


class AdvisorGraphState(TypedDict, total=False):
    query: str
    tenant_id: str
    trace_id: str | None
    _st: aca.AdvisorState


def build_advisor_compliance_langgraph(
    retriever: HybridRetriever,
    llm_fn: LlmCallable | None = None,
    *,
    tenant_has_guidance: bool = False,
) -> Any:
    """Compile a small advisor graph: classify → RAG → (synthesize | escalate)."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "langgraph is not installed. Install with: pip install 'compliancehub[agents]'"
        ) from e

    def n_classify(s: AdvisorGraphState) -> AdvisorGraphState:
        st = s.get("_st")
        if st is None:
            st = aca.AdvisorState(query=s.get("query", ""), tenant_id=s.get("tenant_id", ""))
            tid = s.get("trace_id")
            if tid:
                st.agent_trace.append({"node": "workflow_context", "trace_id": tid})
        st = aca.classify_intent(st)
        return {**s, "_st": st}

    def route_after_classify(s: AdvisorGraphState) -> str:
        if s["_st"].intent == aca.IntentType.out_of_scope:
            return "escalate"
        return "rag"

    def n_rag(s: AdvisorGraphState) -> AdvisorGraphState:
        st = aca.run_rag_query(s["_st"], retriever)
        return {**s, "_st": st}

    def route_after_rag(s: AdvisorGraphState) -> str:
        dec = aca.check_confidence(s["_st"], tenant_has_guidance=tenant_has_guidance)
        return "synthesize" if dec == "synthesize" else "escalate"

    def n_synthesize(s: AdvisorGraphState) -> AdvisorGraphState:
        st = aca.synthesize_answer(s["_st"], llm_fn=llm_fn)
        return {**s, "_st": st}

    def n_escalate(s: AdvisorGraphState) -> AdvisorGraphState:
        st = s["_st"]
        if st.intent == aca.IntentType.out_of_scope and not st.escalation_reason:
            st.escalation_reason = "Anfrage liegt außerhalb des Compliance-Beratungsbereichs."
        st = aca.escalate_to_human(st)
        return {**s, "_st": st}

    graph = StateGraph(AdvisorGraphState)
    graph.add_node("classify_intent", n_classify)
    graph.add_node("run_rag_query", n_rag)
    graph.add_node("synthesize_answer", n_synthesize)
    graph.add_node("escalate_to_human", n_escalate)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {"rag": "run_rag_query", "escalate": "escalate_to_human"},
    )
    graph.add_conditional_edges(
        "run_rag_query",
        route_after_rag,
        {"synthesize": "synthesize_answer", "escalate": "escalate_to_human"},
    )
    graph.add_edge("synthesize_answer", END)
    graph.add_edge("escalate_to_human", END)
    return graph.compile()
