"""Unit-Tests: workspace_telemetry Schema, Sanitizing, actor_type (ohne HTTP)."""

from __future__ import annotations

import json
import logging

import pytest

from app.db import SessionLocal
from app.services import usage_event_logger
from app.services.workspace_telemetry import (
    actor_type_for_request_path,
    build_workspace_event_body,
    emit_workspace_event,
)


def test_actor_type_advisor_path() -> None:
    assert actor_type_for_request_path("/api/v1/advisors/a@x/tenants/t1/report") == "advisor"


def test_actor_type_tenant_path() -> None:
    assert actor_type_for_request_path("/api/v1/workspace/tenant-meta") == "tenant"


def test_build_workspace_event_body_core_schema() -> None:
    p = build_workspace_event_body(
        event_type=usage_event_logger.WORKSPACE_FEATURE_USED,
        tenant_id="t-1",
        workspace_mode="demo",
        actor_type="tenant",
        result="success",
        feature_name="ai_governance_playbook",
        route="/api/v1/x",
        method="get",
    )
    assert p["event_type"] == usage_event_logger.WORKSPACE_FEATURE_USED
    assert p["tenant_id"] == "t-1"
    assert p["workspace_mode"] == "demo"
    assert p["actor_type"] == "tenant"
    assert p["result"] == "success"
    assert p["feature_name"] == "ai_governance_playbook"
    assert p["route"] == "/api/v1/x"
    assert p["method"] == "GET"
    assert "timestamp" in p and p["timestamp"].endswith("Z")


def test_build_body_extra_sanitizes_keys_and_values() -> None:
    p = build_workspace_event_body(
        event_type=usage_event_logger.WORKSPACE_FEATURE_USED,
        tenant_id="t1",
        workspace_mode="demo",
        actor_type="tenant",
        extra={
            "framework_key": "eu_ai_act",
            "owner_email": "x@y.com",
            "user_message": "hello",
            "ai_system_id": "sys-uuid-001",
            "note": "contains spaces bad",
        },
    )
    assert p.get("framework_key") == "eu_ai_act"
    assert p.get("ai_system_id") == "sys-uuid-001"
    assert "owner_email" not in p
    assert "user_message" not in p
    assert "note" not in p


def test_build_body_extra_drops_unknown_whitelist_keys() -> None:
    p = build_workspace_event_body(
        event_type=usage_event_logger.WORKSPACE_FEATURE_USED,
        tenant_id="t1",
        workspace_mode="production",
        actor_type="tenant",
        extra={"malicious_key": "safe_looking", "framework_key": "iso_42001"},
    )
    assert p.get("framework_key") == "iso_42001"
    assert "malicious_key" not in p


def test_build_body_extra_drops_non_matching_string_values() -> None:
    p = build_workspace_event_body(
        event_type=usage_event_logger.WORKSPACE_FEATURE_USED,
        tenant_id="t1",
        workspace_mode="production",
        actor_type="tenant",
        extra={"framework_key": "has illegal spaces"},
    )
    assert "framework_key" not in p


def test_emit_workspace_event_structured_log_json(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_WORKSPACE_TELEMETRY_STRUCTURED_LOG", "1")
    s = SessionLocal()
    try:
        with caplog.at_level(logging.INFO, logger="app.services.workspace_telemetry"):
            emit_workspace_event(
                s,
                usage_event_logger.WORKSPACE_FEATURE_USED,
                "t-struct",
                workspace_mode="production",
                actor_type="tenant",
                feature_name="probe",
                result="success",
                route="/api/v1/probe",
                method="GET",
            )
    finally:
        s.close()

    recs = [r for r in caplog.records if r.name == "app.services.workspace_telemetry"]
    assert recs
    suffix = recs[-1].getMessage().split("workspace_telemetry ", 1)[-1]
    blob = json.loads(suffix)
    assert blob["event_type"] == usage_event_logger.WORKSPACE_FEATURE_USED
    assert blob["tenant_id"] == "t-struct"
    assert blob["timestamp"].endswith("Z")
