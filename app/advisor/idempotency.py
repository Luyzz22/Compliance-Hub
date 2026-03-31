"""Request-level idempotency for advisor endpoints.

Clients (especially SAP/DATEV via network retries) can supply a `request_id`.
If the same request_id is seen within the TTL window, the cached result is
returned and the duplicate is logged in metrics.

Uses an in-process LRU-style dict (no external dependency for beta).
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_MAX = 500
_CACHE_TTL_SECONDS = 300.0

_lock = Lock()
_cache: dict[str, tuple[float, Any]] = {}


def get_cached_response(request_id: str | None) -> Any | None:
    if not request_id:
        return None
    with _lock:
        entry = _cache.get(request_id)
    if entry is None:
        return None
    ts, result = entry
    if (time.monotonic() - ts) > _CACHE_TTL_SECONDS:
        with _lock:
            _cache.pop(request_id, None)
        return None
    logger.info("idempotency_cache_hit", extra={"request_id": request_id})
    return result


def store_response(request_id: str | None, result: Any) -> None:
    if not request_id:
        return
    with _lock:
        if len(_cache) >= _CACHE_MAX:
            oldest_key = min(_cache, key=lambda k: _cache[k][0])
            _cache.pop(oldest_key, None)
        _cache[request_id] = (time.monotonic(), result)


def clear_for_tests() -> None:
    with _lock:
        _cache.clear()
