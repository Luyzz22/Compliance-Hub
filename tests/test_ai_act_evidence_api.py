from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.main import app


def _query_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _headers(tenant_id: str = "evidence-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


client = TestClient(app)


def test_rag_retrieve_records_evidence_without_echoing_query() -> None:
    body = {
        "query": "NIS2 Meldefrist 72 Stunden",
        "retrieval_mode": "hybrid",
        "k": 5,
        "trace_id": "t-ev-1",
        "tenant_expects_guidance": False,
    }
    r = client.post("/api/v1/advisor/rag-retrieve", json=body, headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["query_sha256"] == _query_sha256(body["query"])
    assert "query" not in data
    assert data["retrieval_mode"] in ("hybrid", "bm25")
    assert data["top_doc_ids"]
    assert "confidence_level" in data

    listed = client.get("/api/v1/ai-act-evidence/rag-events", headers=_headers())
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) >= 1
    assert rows[0]["query_sha256"] == data["query_sha256"]
    assert rows[0]["trace_id"] == "t-ev-1"
    assert "query" not in rows[0]


def test_rag_evidence_tenant_isolation() -> None:
    q = "Hochrisiko EU AI Act"
    client.post(
        "/api/v1/advisor/rag-retrieve",
        json={"query": q, "retrieval_mode": "bm25"},
        headers=_headers("tenant-alpha"),
    )
    other = client.get("/api/v1/ai-act-evidence/rag-events", headers=_headers("tenant-beta"))
    assert other.json() == []
    own = client.get("/api/v1/ai-act-evidence/rag-events", headers=_headers("tenant-alpha"))
    assert len(own.json()) == 1


def test_rag_stats_endpoint() -> None:
    client.post(
        "/api/v1/advisor/rag-retrieve",
        json={"query": "test stats", "retrieval_mode": "hybrid"},
        headers=_headers("stats-tenant"),
    )
    s = client.get("/api/v1/ai-act-evidence/rag-stats", headers=_headers("stats-tenant"))
    assert s.status_code == 200
    body = s.json()
    assert body["tenant_id"] == "stats-tenant"
    assert body["rag_events"] >= 1


def test_advisor_agent_events_list_ok() -> None:
    r = client.get("/api/v1/ai-act-evidence/advisor-agent-events", headers=_headers())
    assert r.status_code == 200
    assert r.json() == []
