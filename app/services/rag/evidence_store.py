from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

_MAX_EVENTS = 2000

_lock = Lock()
_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def record_event(payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        **payload,
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    with _lock:
        _events.append(row)
    return row


def list_rag_events(tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        snap = list(_events)
    out = [
        e
        for e in reversed(snap)
        if e.get("event_type") == "rag_query" and e.get("tenant_id") == tenant_id
    ]
    return out[:limit]


def list_advisor_agent_events(tenant_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        snap = list(_events)
    out = [
        e
        for e in reversed(snap)
        if e.get("event_type") == "advisor_agent" and e.get("tenant_id") == tenant_id
    ]
    return out[:limit]


def clear_for_tests() -> None:
    with _lock:
        _events.clear()


def aggregate_rag_hybrid_stats(tenant_id: str, *, limit: int = 500) -> dict[str, Any]:
    events = list_rag_events(tenant_id, limit=limit)
    total = len(events)
    if total == 0:
        return {
            "tenant_id": tenant_id,
            "rag_events": 0,
            "hybrid_differs_ratio": None,
            "dense_rescue_top_ratio": None,
        }
    differs = sum(1 for e in events if e.get("hybrid_differs_from_bm25_top") is True)
    dense_rescue = sum(1 for e in events if e.get("top_doc_primary_source") == "dense_rescue")
    return {
        "tenant_id": tenant_id,
        "rag_events": total,
        "hybrid_differs_ratio": round(differs / total, 4),
        "dense_rescue_top_ratio": round(dense_rescue / total, 4),
    }
