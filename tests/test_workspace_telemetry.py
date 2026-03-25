"""Unit-Tests: workspace_telemetry Payload und actor_type (ohne HTTP)."""

from __future__ import annotations

from app.services.workspace_telemetry import (
    actor_type_for_request_path,
    build_workspace_event_payload,
)


def test_actor_type_advisor_path() -> None:
    assert actor_type_for_request_path("/api/v1/advisors/a@x/tenants/t1/report") == "advisor"


def test_actor_type_tenant_path() -> None:
    assert actor_type_for_request_path("/api/v1/workspace/tenant-meta") == "tenant"


def test_build_payload_includes_only_known_keys() -> None:
    p = build_workspace_event_payload(
        workspace_mode="demo",
        actor_type="tenant",
        result="success",
        feature_name="wizard",
        route="/api/v1/x",
        method="GET",
    )
    assert p == {
        "workspace_mode": "demo",
        "actor_type": "tenant",
        "result": "success",
        "feature_name": "wizard",
        "route": "/api/v1/x",
        "method": "GET",
    }
