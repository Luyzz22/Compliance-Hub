"""Temporal activity wrapper for the Advisor LangGraph agent.

Encapsulates LLM calls inside a Temporal activity to maintain workflow
determinism.  Propagates trace_id so agent spans join existing OTel traces.

This module is optional — it gracefully degrades if temporalio is not installed.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from app.services.agents.advisor_compliance_agent import (
    AdvisorComplianceAgent,
    AdvisorState,
)
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallable

logger = logging.getLogger(__name__)


@dataclass
class AdvisorActivityInput:
    query: str
    tenant_id: str
    trace_id: str = ""
    retrieval_mode: str = "hybrid"
    tenant_has_guidance: bool = False


@dataclass
class AdvisorActivityOutput:
    answer: str
    is_escalated: bool
    escalation_reason: str
    confidence_level: str
    agent_trace: list[dict[str, Any]]


def run_advisor_agent_activity(
    input_data: AdvisorActivityInput,
    documents: list[Document],
    llm_fn: LlmCallable | None = None,
    config: RAGConfig | None = None,
) -> AdvisorActivityOutput:
    """Core activity logic — can be called from Temporal or directly.

    Deterministic: all non-deterministic work (LLM, retrieval) happens
    inside this activity boundary.
    """
    config = config or RAGConfig(retrieval_mode=input_data.retrieval_mode)
    retriever = HybridRetriever(documents, config)

    agent = AdvisorComplianceAgent(
        retriever=retriever,
        llm_fn=llm_fn,
        tenant_has_guidance=input_data.tenant_has_guidance,
    )

    state: AdvisorState = agent.run(
        query=input_data.query,
        tenant_id=input_data.tenant_id,
        trace_id=input_data.trace_id or None,
    )

    return AdvisorActivityOutput(
        answer=state.answer,
        is_escalated=state.is_escalated,
        escalation_reason=state.escalation_reason,
        confidence_level=state.confidence_level,
        agent_trace=state.agent_trace,
    )


def _check_temporal_available() -> bool:
    try:
        import temporalio  # noqa: F401

        return True
    except ImportError:
        return False


if _check_temporal_available():
    from temporalio import activity

    @activity.defn(name="run_advisor_compliance_agent")
    async def temporal_advisor_activity(
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Temporal activity definition wrapping the advisor agent.

        Accepts/returns plain dicts for Temporal serialization.
        In production, the document corpus and LLM callable would be
        resolved from the activity's execution context.
        """
        parsed = AdvisorActivityInput(**input_data)

        logger.info(
            "temporal_advisor_activity_start",
            extra={"tenant_id": parsed.tenant_id, "trace_id": parsed.trace_id},
        )

        result = run_advisor_agent_activity(
            input_data=parsed,
            documents=[],
            llm_fn=None,
        )

        return asdict(result)
