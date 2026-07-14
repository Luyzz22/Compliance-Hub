from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_api_responses_include_baseline_security_headers() -> None:
    response = TestClient(app).get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
