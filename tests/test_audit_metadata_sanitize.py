from __future__ import annotations

import json

from app.services.audit_metadata_sanitize import metadata_json_safe, sanitize_audit_metadata


def test_sanitize_redacts_sensitive_keys() -> None:
    raw = {"incident_id": "x", "api_key": "secret", "nested": {"password": "p"}}
    clean = sanitize_audit_metadata(raw)
    assert clean["incident_id"] == "x"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["nested"]["password"] == "[REDACTED]"


def test_metadata_json_safe_roundtrip() -> None:
    s = metadata_json_safe({"ok": "value", "refresh_token": "nope"})
    assert s is not None
    data = json.loads(s)
    assert data["ok"] == "value"
    assert data["refresh_token"] == "[REDACTED]"
