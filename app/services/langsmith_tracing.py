"""LangSmith observability integration — env-gated tracing for LLM operations.

All functions are no-ops when LANGSMITH_API_KEY is not set.
NEVER includes personal data (PII) in traces.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_LANGSMITH_API_KEY_VAR = "LANGSMITH_API_KEY"
_LANGSMITH_PROJECT_VAR = "LANGSMITH_PROJECT"

# In-memory trace store for when LangSmith SDK is not available.
# Maps run_id → trace dict.  Used by create/end helpers.
_trace_store: dict[str, dict] = {}


@dataclass
class LangSmithMetrics:
    """Structured metrics for a single LLM trace."""

    latency_ms: float
    token_estimate: int
    model: str
    prompt_version: str = ""
    success: bool = True
    error_message: str = ""


def _is_configured() -> bool:
    """Return True when the required LangSmith env vars are present."""
    return bool(os.getenv(_LANGSMITH_API_KEY_VAR))


def configure_langsmith() -> bool:
    """Check whether LangSmith environment variables are set.

    Returns True when both LANGSMITH_API_KEY and LANGSMITH_PROJECT are
    available, False otherwise.  This function does **not** make network
    calls.
    """
    api_key = os.getenv(_LANGSMITH_API_KEY_VAR)
    project = os.getenv(_LANGSMITH_PROJECT_VAR)
    configured = bool(api_key and project)
    if configured:
        logger.info("langsmith_configured project=%s", project)
    else:
        logger.debug("langsmith_not_configured (env vars missing)")
    return configured


def create_langsmith_run(
    name: str,
    run_type: str = "chain",
    inputs: dict | None = None,
    metadata: dict | None = None,
) -> str | None:
    """Create a LangSmith trace run.

    Returns a run_id string when configured, or None when LangSmith is
    not available.  Inputs and metadata must NOT contain PII.
    """
    if not _is_configured():
        return None

    run_id = str(uuid.uuid4())
    _trace_store[run_id] = {
        "run_id": run_id,
        "name": name,
        "run_type": run_type,
        "inputs": inputs or {},
        "metadata": metadata or {},
        "start_time": datetime.now(UTC).isoformat(),
        "outputs": None,
        "error": None,
        "end_time": None,
    }
    logger.debug("langsmith_run_created run_id=%s name=%s", run_id, name)
    return run_id


def end_langsmith_run(
    run_id: str,
    outputs: dict | None = None,
    error: str | None = None,
) -> None:
    """End a previously created LangSmith trace run.

    No-op when LangSmith is not configured or *run_id* is unknown.
    """
    if not _is_configured():
        return

    trace = _trace_store.get(run_id)
    if trace is None:
        logger.warning("langsmith_run_not_found run_id=%s", run_id)
        return

    trace["end_time"] = datetime.now(UTC).isoformat()
    trace["outputs"] = outputs
    trace["error"] = error
    logger.debug("langsmith_run_ended run_id=%s error=%s", run_id, error)


def trace_gap_analysis(
    tenant_id: str,
    norms: list[str],
    latency_ms: float,
    token_estimate: int,
    model: str,
    success: bool,
) -> dict:
    """Log gap-analysis metrics to LangSmith (no PII).

    Returns the metrics dict regardless of whether LangSmith is active,
    so callers can use it for local logging too.
    """
    metrics = {
        "event": "gap_analysis",
        "tenant_id": tenant_id,
        "norms": norms,
        "latency_ms": latency_ms,
        "token_estimate": token_estimate,
        "model": model,
        "success": success,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if _is_configured():
        run_id = create_langsmith_run(
            name="gap_analysis",
            run_type="chain",
            inputs={"tenant_id": tenant_id, "norms": norms, "model": model},
            metadata={"latency_ms": latency_ms, "token_estimate": token_estimate},
        )
        if run_id:
            end_langsmith_run(
                run_id,
                outputs={"success": success, "norms_analysed": len(norms)},
                error=None if success else "gap_analysis_failed",
            )

    logger.info(
        "gap_analysis_traced tenant=%s norms=%s latency=%.1fms tokens=%d model=%s ok=%s",
        tenant_id,
        ",".join(norms),
        latency_ms,
        token_estimate,
        model,
        success,
    )
    return metrics
