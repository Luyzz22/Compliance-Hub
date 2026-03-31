"""SAP BTP Event Mesh–style envelope builder.

Produces CloudEvents-aligned JSON envelopes suitable for SAP Event Mesh
or Integration Suite consumers.  All IDs are stable and traceable.

Envelope spec (v1):
  headers:
    specversion, type, source, id, time, tenantid, clientid, systemid
  body:
    payload_type, payload_version, data

No PII/raw prompts.  Versioned via ``specversion`` + ``payload_version``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

SPEC_VERSION = "1.0"
EVENT_SOURCE = "compliancehub.ai-governance"


def _event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:16]}"


def build_sap_envelope(
    *,
    event_type: str,
    tenant_id: str,
    client_id: str = "",
    system_id: str = "",
    payload_type: str,
    payload_version: str = "v1",
    data: dict[str, Any],
    source: str = EVENT_SOURCE,
    job_id: str = "",
    trace_id: str = "",
) -> dict[str, Any]:
    """Build a CloudEvents-style SAP BTP envelope.

    Returns the full envelope dict, including a stable ``id`` that can
    be used as ``connector_envelope_id`` on the IntegrationJob.
    """
    envelope_id = _event_id()
    return {
        "specversion": SPEC_VERSION,
        "type": f"compliancehub.grc.{event_type}",
        "source": source,
        "id": envelope_id,
        "time": datetime.now(UTC).isoformat(),
        "tenantid": tenant_id,
        "clientid": client_id,
        "systemid": system_id,
        "traceid": trace_id,
        "jobid": job_id,
        "datacontenttype": "application/json",
        "payload_type": payload_type,
        "payload_version": payload_version,
        "data": data,
    }
