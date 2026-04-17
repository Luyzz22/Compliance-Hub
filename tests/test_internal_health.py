"""Gated internal deep-health endpoint (monitoring agents)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_internal_health_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_HEALTH_API_KEY", raising=False)
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "ignored"},
    )
    assert resp.status_code == 503


def test_internal_health_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    resp = client.get("/api/internal/health")
    assert resp.status_code == 401


def test_internal_health_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "wrong"},
    )
    assert resp.status_code == 401


def test_internal_health_ok_with_valid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "up"
    assert body["db"] == "up"
    assert body["external_ai_provider"] == "up"
    assert "timestamp" in body


def test_internal_health_ip_allowlist_blocks_unknown_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    monkeypatch.setenv("INTERNAL_HEALTH_ALLOWED_IPS", "203.0.113.10")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 403


def test_internal_health_ip_allowlist_allows_testclient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    monkeypatch.setenv("INTERNAL_HEALTH_ALLOWED_IPS", "testclient")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 200
