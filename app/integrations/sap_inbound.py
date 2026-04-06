"""SAP S/4HANA + BTP inbound handler.

Validates CloudEvents envelopes from SAP Event Mesh / Integration Suite
and maps them to AiSystem stubs.  This is the receiving side of the
reference flow: S/4 publishes events → BTP transforms → ComplianceHub.

For this wave: validation + AiSystem creation only, no real BTP wiring.
"""

from __future__ import annotations

import logging
from typing import Any

from app.grc.store import get_or_create_ai_system, upsert_ai_system
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)

REQUIRED_ENVELOPE_FIELDS = frozenset(
    {
        "specversion",
        "type",
        "source",
        "id",
        "tenantid",
        "data",
    }
)

SAP_EXPECTED_TYPES = frozenset(
    {
        "sap.s4.ai.system.created",
        "sap.s4.ai.system.updated",
        "sap.s4.ai.deployment.requested",
    }
)


def validate_sap_envelope(
    envelope: dict[str, Any],
) -> list[str]:
    """Validate a CloudEvents envelope from SAP.

    Returns a list of validation errors (empty = valid).
    """
    errors: list[str] = []
    for field in REQUIRED_ENVELOPE_FIELDS:
        if not envelope.get(field):
            errors.append(f"Missing required field: {field}")

    spec = envelope.get("specversion", "")
    if spec and spec != "1.0":
        errors.append(f"Unsupported specversion: {spec}")

    event_type = envelope.get("type", "")
    if event_type and event_type not in SAP_EXPECTED_TYPES:
        errors.append(f"Unrecognised event type: {event_type}")

    data = envelope.get("data")
    if isinstance(data, dict):
        if not data.get("system_id"):
            errors.append("data.system_id is required")
    elif data is not None:
        errors.append("data must be a JSON object")

    return errors


def process_sap_ai_system_event(
    envelope: dict[str, Any],
) -> dict[str, Any]:
    """Process a validated SAP envelope and create/update an AiSystem.

    Returns a result dict with the created/updated system info.
    """
    tenant_id = envelope.get("tenantid", "")
    client_id = envelope.get("clientid", "")
    system_id_from_data = envelope["data"].get("system_id", "")
    event_type = envelope.get("type", "")
    trace_id = envelope.get("traceid", "")
    sap_source = envelope.get("source", "")
    envelope_id = envelope.get("id", "")

    ai_sys = get_or_create_ai_system(
        tenant_id=tenant_id,
        system_id=system_id_from_data,
        client_id=client_id,
    )

    data = envelope["data"]
    updated = False
    if data.get("name") and (not ai_sys.name or ai_sys.auto_created):
        ai_sys.name = data["name"]
        updated = True
    if data.get("description") and not ai_sys.description:
        ai_sys.description = data["description"]
        updated = True
    if data.get("business_owner") and not ai_sys.business_owner:
        ai_sys.business_owner = data["business_owner"]
        updated = True

    if updated:
        ai_sys = upsert_ai_system(ai_sys)

    _log_sap_inbound_evidence(
        tenant_id=tenant_id,
        client_id=client_id,
        system_id=system_id_from_data,
        ai_system_id=ai_sys.id,
        event_type=event_type,
        sap_source=sap_source,
        envelope_id=envelope_id,
        trace_id=trace_id,
    )

    return {
        "status": "accepted",
        "ai_system_id": ai_sys.id,
        "system_id": ai_sys.system_id,
        "tenant_id": tenant_id,
        "auto_created": ai_sys.auto_created,
        "event_type": event_type,
    }


def _log_sap_inbound_evidence(
    *,
    tenant_id: str,
    client_id: str,
    system_id: str,
    ai_system_id: str,
    event_type: str,
    sap_source: str,
    envelope_id: str,
    trace_id: str,
) -> None:
    record_event(
        {
            "event_type": "sap_btp_ai_system_event",
            "tenant_id": tenant_id,
            "client_id": client_id,
            "system_id": system_id,
            "ai_system_id": ai_system_id,
            "sap_event_type": event_type,
            "sap_source": sap_source,
            "envelope_id": envelope_id,
            "trace_id": trace_id,
        }
    )
