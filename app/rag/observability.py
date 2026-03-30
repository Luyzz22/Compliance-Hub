"""Structured RAG observability (hashed queries, no raw PII in logs)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Literal

logger = logging.getLogger(__name__)

RagQueryPhase = Literal["retrieval_complete", "response_complete"]


def query_sha256_hex(question_de: str) -> str:
    return hashlib.sha256(question_de.strip().encode("utf-8")).hexdigest()


def redacted_query_preview(question_de: str, *, max_len: int = 120) -> str:
    """Short preview with long digit runs masked (IBANs, IDs)."""
    s = question_de.strip().replace("\n", " ")[:max_len]
    return re.sub(r"\d{4,}", "[#]", s)


def log_rag_query_event(
    *,
    phase: RagQueryPhase,
    tenant_id: str,
    user_role: str,
    advisor_id: str | None,
    query_sha256: str,
    query_length_chars: int,
    query_redacted_preview: str,
    top_k_effective: int,
    retrieved_doc_ids: list[str],
    retrieval_scores: list[float],
    latency_ms_retrieval: float | None = None,
    latency_ms_llm: float | None = None,
    latency_ms_total: float | None = None,
    confidence_level: str | None = None,
    llm_action_name: str = "advisor_rag_eu_ai_act_nis2_query",
    extra: dict[str, Any] | None = None,
) -> None:
    """
    One normalized log line per phase (retrieval vs full response).

    Does not log raw ``question_de``; only hash, length, and redacted preview.
    """
    record: dict[str, Any] = {
        "event": "rag_query",
        "phase": phase,
        "tenant_id": tenant_id,
        "user_role": user_role,
        "advisor_id": advisor_id,
        "query_sha256": query_sha256,
        "query_length_chars": query_length_chars,
        "query_redacted_preview": query_redacted_preview,
        "top_k_effective": top_k_effective,
        "retrieved_doc_ids": retrieved_doc_ids,
        "retrieval_scores": [round(x, 6) for x in retrieval_scores],
        "llm_context": {
            "action_name": llm_action_name,
        },
    }
    if latency_ms_retrieval is not None:
        record["latency_ms_retrieval"] = round(latency_ms_retrieval, 2)
    if latency_ms_llm is not None:
        record["latency_ms_llm"] = round(latency_ms_llm, 2)
    if latency_ms_total is not None:
        record["latency_ms_total"] = round(latency_ms_total, 2)
    if confidence_level is not None:
        record["confidence_level"] = confidence_level
    if extra:
        record["extra"] = extra
    logger.info("rag_query_event %s", json.dumps(record, ensure_ascii=False))


class RagTimingSpan:
    """Simple perf counter slice for retrieval vs LLM."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self.retrieval_end: float | None = None
        self.llm_end: float | None = None

    def mark_retrieval_end(self) -> None:
        self.retrieval_end = time.perf_counter()

    def mark_llm_end(self) -> None:
        self.llm_end = time.perf_counter()

    def ms_retrieval(self) -> float | None:
        if self.retrieval_end is None:
            return None
        return (self.retrieval_end - self._t0) * 1000.0

    def ms_llm(self) -> float | None:
        if self.retrieval_end is None or self.llm_end is None:
            return None
        return (self.llm_end - self.retrieval_end) * 1000.0

    def ms_total(self) -> float | None:
        if self.llm_end is None:
            return None
        return (self.llm_end - self._t0) * 1000.0
