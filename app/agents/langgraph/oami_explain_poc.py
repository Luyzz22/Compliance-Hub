"""
Deterministic OAMI explain PoC: load index → LLM JSON (guardrailed) → optional rule fallback.

Synchronous invocation from FastAPI; MemorySaver checkpointer for LangGraph API compatibility.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.llm.guardrails import LLMContractViolation
from app.llm.safe_llm_invoke import safe_llm_json_call
from app.llm_models import LLMTaskType
from app.operational_monitoring_models import OamiExplanationOut, SystemMonitoringIndexOut
from app.services.oami_explanation import explain_system_oami_de
from app.services.operational_monitoring_index import compute_system_monitoring_index

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OamiExplainPocState(TypedDict, total=False):
    tenant_id: str
    ai_system_id: str
    window_days: int
    index_json: dict[str, object] | None
    explanation: dict[str, object] | None
    llm_error: str | None


def _build_oami_explain_prompt(index: dict[str, object]) -> str:
    return (
        "Du bist ein Compliance-Assistent. Erzeuge ausschließlich ein JSON-Objekt mit den "
        "Schlüsseln: summary_de (string), drivers_de (Liste von Strings, höchstens 12 kurze "
        "Sätze), monitoring_gap_de (string oder null). Nutze nur die folgenden OAMI-Fakten; "
        "erfunde keine neuen Messzahlen außerhalb der Fakten.\n\n"
        f"{json.dumps(index, ensure_ascii=False)}"
    )


def build_oami_explain_poc_graph(session: Session):
    """Compile a small graph bound to a DB session (tenant-scoped callers)."""

    def node_load_index(state: OamiExplainPocState) -> dict[str, object]:
        tid = state["tenant_id"]
        sid = state["ai_system_id"]
        wd = int(state.get("window_days") or 90)
        idx = compute_system_monitoring_index(session, tid, sid, window_days=wd)
        payload = idx.model_dump(mode="json")
        payload.pop("explanation", None)
        return {"index_json": payload, "llm_error": None}

    def node_llm_explain(state: OamiExplainPocState) -> dict[str, object]:
        tid = state["tenant_id"]
        raw_index = state.get("index_json") or {}
        prompt = _build_oami_explain_prompt(raw_index)
        try:
            out = safe_llm_json_call(
                session,
                tid,
                LLMTaskType.STRUCTURED_OUTPUT,
                prompt,
                OamiExplanationOut,
                context="langgraph_oami_explain_poc",
                response_format="json_object",
            )
            return {"explanation": out.model_dump(mode="json"), "llm_error": None}
        except LLMContractViolation as exc:
            logger.info(
                "langgraph_oami_explain_llm_contract_failed tenant=%s system=%s err=%s",
                tid,
                state.get("ai_system_id"),
                exc,
            )
            return {"explanation": None, "llm_error": str(exc)[:500]}

    def node_fallback(state: OamiExplainPocState) -> dict[str, object]:
        raw = state.get("index_json")
        if not raw:
            raise RuntimeError("oami_explain_poc_missing_index")
        idx = SystemMonitoringIndexOut.model_validate(raw)
        out = explain_system_oami_de(idx)
        return {"explanation": out.model_dump(mode="json"), "llm_error": None}

    def node_finalize(state: OamiExplainPocState) -> dict[str, object]:
        return {}

    def route_after_llm(state: OamiExplainPocState) -> str:
        if state.get("explanation"):
            return "finalize"
        return "fallback"

    g = StateGraph(OamiExplainPocState)
    g.add_node("load_index", node_load_index)
    g.add_node("llm_explain", node_llm_explain)
    g.add_node("fallback", node_fallback)
    g.add_node("finalize", node_finalize)
    g.add_edge(START, "load_index")
    g.add_edge("load_index", "llm_explain")
    g.add_conditional_edges(
        "llm_explain",
        route_after_llm,
        {"finalize": "finalize", "fallback": "fallback"},
    )
    g.add_edge("fallback", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=MemorySaver())


def run_oami_explain_poc(
    session: Session,
    *,
    tenant_id: str,
    ai_system_id: str,
    window_days: int = 90,
) -> OamiExplanationOut:
    graph = build_oami_explain_poc_graph(session)
    init: OamiExplainPocState = {
        "tenant_id": tenant_id,
        "ai_system_id": ai_system_id,
        "window_days": window_days,
    }
    cfg = {"configurable": {"thread_id": f"{tenant_id}:{ai_system_id}:{window_days}"}}
    out_state = graph.invoke(init, cfg)
    expl = out_state.get("explanation")
    if not expl:
        raise RuntimeError("oami_explain_poc_empty_explanation")
    return OamiExplanationOut.model_validate(expl)
