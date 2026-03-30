"""
LangGraph PoC: OAMI explain (deterministic graph, guardrailed LLM + rule fallback).

Linear flow: normalize_input → build_prompt → call_llm → [fallback if needed] → post_process.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.llm.client_wrapped import safe_llm_call_sync
from app.llm.context import LlmCallContext
from app.llm.exceptions import LLMContractViolation
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
    user_role: str
    index_json: dict[str, object] | None
    prompt: str | None
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

    def node_normalize_input(state: OamiExplainPocState) -> dict[str, object]:
        tid = state["tenant_id"]
        sid = state["ai_system_id"]
        wd = int(state.get("window_days") or 90)
        idx = compute_system_monitoring_index(session, tid, sid, window_days=wd)
        payload = idx.model_dump(mode="json")
        payload.pop("explanation", None)
        return {"index_json": payload, "llm_error": None, "prompt": None, "explanation": None}

    def node_build_prompt(state: OamiExplainPocState) -> dict[str, object]:
        raw = state.get("index_json") or {}
        return {"prompt": _build_oami_explain_prompt(raw)}

    def node_call_llm(state: OamiExplainPocState) -> dict[str, object]:
        tid = state["tenant_id"]
        prompt = state.get("prompt") or ""
        ctx = LlmCallContext(
            tenant_id=tid,
            user_role=(state.get("user_role") or "").strip(),
            action_name="call_langgraph_oami_explain",
        )
        try:
            out = safe_llm_call_sync(
                prompt,
                OamiExplanationOut,
                context=ctx,
                session=session,
                task_type=LLMTaskType.STRUCTURED_OUTPUT,
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

    def node_post_process(state: OamiExplainPocState) -> dict[str, object]:
        expl = state.get("explanation")
        if not expl:
            raise RuntimeError("oami_explain_poc_empty_explanation")
        model = OamiExplanationOut.model_validate(expl)
        return {"explanation": model.model_dump(mode="json")}

    def route_after_llm(state: OamiExplainPocState) -> str:
        if state.get("explanation"):
            return "post_process"
        return "fallback"

    g = StateGraph(OamiExplainPocState)
    g.add_node("normalize_input", node_normalize_input)
    g.add_node("build_prompt", node_build_prompt)
    g.add_node("call_llm", node_call_llm)
    g.add_node("fallback", node_fallback)
    g.add_node("post_process", node_post_process)
    g.add_edge(START, "normalize_input")
    g.add_edge("normalize_input", "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_conditional_edges(
        "call_llm",
        route_after_llm,
        {"post_process": "post_process", "fallback": "fallback"},
    )
    g.add_edge("fallback", "post_process")
    g.add_edge("post_process", END)
    return g.compile(checkpointer=MemorySaver())


def run_oami_explain_poc(
    session: Session,
    *,
    tenant_id: str,
    ai_system_id: str,
    window_days: int = 90,
    user_role: str = "",
) -> OamiExplanationOut:
    graph = build_oami_explain_poc_graph(session)
    init: OamiExplainPocState = {
        "tenant_id": tenant_id,
        "ai_system_id": ai_system_id,
        "window_days": window_days,
        "user_role": user_role,
    }
    cfg = {"configurable": {"thread_id": f"{tenant_id}:{ai_system_id}:{window_days}"}}
    out_state = graph.invoke(init, cfg)
    expl = out_state.get("explanation")
    if not expl:
        raise RuntimeError("oami_explain_poc_empty_explanation")
    return OamiExplanationOut.model_validate(expl)


async def run_oami_explain_poc_async(
    session: Session,
    *,
    tenant_id: str,
    ai_system_id: str,
    window_days: int = 90,
    user_role: str = "",
) -> OamiExplanationOut:
    """Async entrypoint: runs the sync graph in a worker thread (non-blocking event loop)."""
    return await asyncio.to_thread(
        run_oami_explain_poc,
        session,
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        window_days=window_days,
        user_role=user_role,
    )
