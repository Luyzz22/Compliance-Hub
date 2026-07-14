"""GoBD-compliant (§14) XML export for audit trail entries."""

from __future__ import annotations

from datetime import UTC, datetime

from app.audit_models import AuditLog
from app.xml_security import append_xml_element, new_xml_root, serialize_xml

_NAMESPACE = "urn:compliancehub:gobd:audit:v1"


def generate_gobd_xml(entries: list[AuditLog]) -> str:
    """Return a UTF-8 XML string representing the GoBD audit trail."""
    root = new_xml_root("AuditTrail")
    root.set("xmlns", _NAMESPACE)
    root.set("exportDate", datetime.now(UTC).isoformat())

    for entry in entries:
        attrs = {
            "id": str(entry.id),
            "tenantId": entry.tenant_id,
            "actor": entry.actor,
            "action": entry.action,
            "entityType": entry.entity_type,
            "entityId": entry.entity_id,
            "createdAt": entry.created_at_utc.isoformat(),
            "entryHash": entry.entry_hash or "",
            "previousHash": entry.previous_hash or "",
            "actorRole": entry.actor_role or "",
            "outcome": entry.outcome or "",
            "correlationId": entry.correlation_id or "",
        }
        el = append_xml_element(root, "Entry", attributes=attrs)
        append_xml_element(el, "Before", text=entry.before or "")
        append_xml_element(el, "After", text=entry.after or "")

    xml_str = serialize_xml(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
