"""In-memory GRC record store.

Thread-safe, idempotent upsert based on entity idempotency keys.
Designed as a thin layer that can be swapped for a database later.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from app.grc.models import (
    AiRiskAssessment,
    Iso42001GapRecord,
    Nis2ObligationRecord,
    _now_iso,
)

logger = logging.getLogger(__name__)

_lock = Lock()
_risks: dict[str, AiRiskAssessment] = {}
_nis2: dict[str, Nis2ObligationRecord] = {}
_gaps: dict[str, Iso42001GapRecord] = {}
_idem_index: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Upsert (idempotent create-or-update)
# ---------------------------------------------------------------------------


def upsert_risk(record: AiRiskAssessment) -> AiRiskAssessment:
    """Create or update an AI risk assessment. Returns the persisted record."""
    key = record.idempotency_key()
    with _lock:
        existing_id = _idem_index.get(key)
        if existing_id and existing_id in _risks:
            existing = _risks[existing_id]
            record.id = existing.id
            record.created_at = existing.created_at
            if existing.status != record.status:
                record.status = existing.status
            record.updated_at = _now_iso()
            _risks[existing.id] = record
            logger.info("grc_risk_updated", extra={"id": record.id, "key": key})
            return record
        _risks[record.id] = record
        _idem_index[key] = record.id
        logger.info("grc_risk_created", extra={"id": record.id, "key": key})
        return record


def upsert_nis2(record: Nis2ObligationRecord) -> Nis2ObligationRecord:
    key = record.idempotency_key()
    with _lock:
        existing_id = _idem_index.get(key)
        if existing_id and existing_id in _nis2:
            existing = _nis2[existing_id]
            record.id = existing.id
            record.created_at = existing.created_at
            if existing.status != record.status:
                record.status = existing.status
            record.updated_at = _now_iso()
            _nis2[existing.id] = record
            logger.info("grc_nis2_updated", extra={"id": record.id, "key": key})
            return record
        _nis2[record.id] = record
        _idem_index[key] = record.id
        logger.info("grc_nis2_created", extra={"id": record.id, "key": key})
        return record


def upsert_gap(record: Iso42001GapRecord) -> Iso42001GapRecord:
    key = record.idempotency_key()
    with _lock:
        existing_id = _idem_index.get(key)
        if existing_id and existing_id in _gaps:
            existing = _gaps[existing_id]
            record.id = existing.id
            record.created_at = existing.created_at
            if existing.status != record.status:
                record.status = existing.status
            record.updated_at = _now_iso()
            _gaps[existing.id] = record
            logger.info("grc_gap_updated", extra={"id": record.id, "key": key})
            return record
        _gaps[record.id] = record
        _idem_index[key] = record.id
        logger.info("grc_gap_created", extra={"id": record.id, "key": key})
        return record


# ---------------------------------------------------------------------------
# Read / list
# ---------------------------------------------------------------------------


def list_risks(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
    system_id: str | None = None,
) -> list[AiRiskAssessment]:
    with _lock:
        out = list(_risks.values())
    return _filter(out, tenant_id, client_id, system_id)


def list_nis2_obligations(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
    entity_type: str | None = None,
) -> list[Nis2ObligationRecord]:
    with _lock:
        out = list(_nis2.values())
    filtered = _filter(out, tenant_id, client_id, None)
    if entity_type:
        filtered = [r for r in filtered if r.nis2_entity_type == entity_type]
    return filtered


def list_iso42001_gaps(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
    control_family: str | None = None,
) -> list[Iso42001GapRecord]:
    with _lock:
        out = list(_gaps.values())
    filtered = _filter(out, tenant_id, client_id, None)
    if control_family:
        filtered = [r for r in filtered if control_family in r.control_families]
    return filtered


def get_risk(record_id: str) -> AiRiskAssessment | None:
    with _lock:
        return _risks.get(record_id)


def get_nis2(record_id: str) -> Nis2ObligationRecord | None:
    with _lock:
        return _nis2.get(record_id)


def get_gap(record_id: str) -> Iso42001GapRecord | None:
    with _lock:
        return _gaps.get(record_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter(
    records: list[Any],
    tenant_id: str | None,
    client_id: str | None,
    system_id: str | None,
) -> list[Any]:
    if tenant_id:
        records = [r for r in records if r.tenant_id == tenant_id]
    if client_id:
        records = [r for r in records if r.client_id == client_id]
    if system_id:
        records = [r for r in records if r.system_id == system_id]
    return records


def clear_for_tests() -> None:
    with _lock:
        _risks.clear()
        _nis2.clear()
        _gaps.clear()
        _idem_index.clear()
