"""Versioned canonical hashing for the tenant audit chain.

The chain detects in-database mutation of covered fields. It is not an external timestamp,
qualified signature, or independently controlled immutable archive.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

AUDIT_INTEGRITY_V1 = "sha256-v1"
AUDIT_INTEGRITY_V2 = "sha256-v2"
CURRENT_AUDIT_INTEGRITY_VERSION = AUDIT_INTEGRITY_V2


def _normalized_timestamp(created_at: datetime) -> str:
    # Audit writes use UTC. Removing tzinfo preserves compatibility with v1 rows read back
    # from database drivers that omit the UTC offset.
    return created_at.replace(tzinfo=None).isoformat()


def compute_audit_entry_hash(
    *,
    integrity_version: str,
    tenant_id: str,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: str | None,
    after: str | None,
    ip_address: str | None,
    user_agent: str | None,
    created_at: datetime,
    actor_role: str | None,
    outcome: str | None,
    correlation_id: str | None,
    metadata_json: str | None,
    previous_hash: str | None,
) -> str:
    if integrity_version == AUDIT_INTEGRITY_V1:
        payload = (
            f"{tenant_id}|{action}|{entity_type}|{entity_id}"
            f"|{before or ''}|{after or ''}"
            f"|{_normalized_timestamp(created_at)}|{previous_hash or ''}"
        )
    elif integrity_version == AUDIT_INTEGRITY_V2:
        payload = json.dumps(
            {
                "action": action,
                "actor": actor,
                "actor_role": actor_role,
                "after": after,
                "before": before,
                "correlation_id": correlation_id,
                "created_at_utc": _normalized_timestamp(created_at),
                "entity_id": entity_id,
                "entity_type": entity_type,
                "integrity_version": integrity_version,
                "ip_address": ip_address,
                "metadata_json": metadata_json,
                "outcome": outcome,
                "previous_hash": previous_hash,
                "tenant_id": tenant_id,
                "user_agent": user_agent,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    else:
        raise ValueError(f"Unsupported audit integrity version: {integrity_version}")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
