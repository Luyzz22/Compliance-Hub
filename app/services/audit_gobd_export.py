"""GoBD-compliant (§14) XML export for audit trail entries."""

from __future__ import annotations

from datetime import UTC, datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from app.audit_models import AuditLog

_NAMESPACE = "urn:compliancehub:gobd:audit:v1"


def generate_gobd_xml(entries: list[AuditLog]) -> str:
    """Return a UTF-8 XML string representing the GoBD audit trail."""
    root = Element("AuditTrail")
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
        }
        el = SubElement(root, "Entry", attrs)
        before_el = SubElement(el, "Before")
        before_el.text = entry.before or ""
        after_el = SubElement(el, "After")
        after_el.text = entry.after or ""

    xml_bytes: bytes = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
