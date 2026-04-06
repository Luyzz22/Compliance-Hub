"""Tests for advisor metrics aggregation (Wave 7).

Validates that the metrics module correctly counts and buckets synthetic
evidence events without accessing PII.
"""

from __future__ import annotations

from app.advisor.metrics import aggregate_advisor_metrics
from app.services.rag.evidence_store import clear_for_tests, record_event


class TestAdvisorMetricsAggregation:
    def setup_method(self) -> None:
        clear_for_tests()

    def teardown_method(self) -> None:
        clear_for_tests()

    def test_empty_store_returns_zeros(self) -> None:
        result = aggregate_advisor_metrics(tenant_id="t-empty")
        assert result.total_queries == 0
        assert result.escalation_rate is None
        assert result.daily == []

    def test_counts_rag_events_by_mode(self) -> None:
        for _ in range(3):
            record_event(
                {
                    "event_type": "rag_query",
                    "tenant_id": "t1",
                    "retrieval_mode": "bm25",
                    "confidence_level": "high",
                }
            )
        for _ in range(2):
            record_event(
                {
                    "event_type": "rag_query",
                    "tenant_id": "t1",
                    "retrieval_mode": "hybrid",
                    "confidence_level": "medium",
                }
            )

        result = aggregate_advisor_metrics(tenant_id="t1")
        assert result.total_queries == 5
        assert result.retrieval_mode_distribution["bm25"] == 3
        assert result.retrieval_mode_distribution["hybrid"] == 2

    def test_counts_confidence_buckets(self) -> None:
        for conf in ["high", "high", "medium", "low"]:
            record_event(
                {
                    "event_type": "rag_query",
                    "tenant_id": "t2",
                    "retrieval_mode": "bm25",
                    "confidence_level": conf,
                }
            )

        result = aggregate_advisor_metrics(tenant_id="t2")
        assert result.confidence_distribution["high"] == 2
        assert result.confidence_distribution["medium"] == 1
        assert result.confidence_distribution["low"] == 1

    def test_agent_decision_distribution(self) -> None:
        for _ in range(4):
            record_event(
                {
                    "event_type": "advisor_agent",
                    "tenant_id": "t3",
                    "decision": "answered",
                }
            )
        record_event(
            {
                "event_type": "advisor_agent",
                "tenant_id": "t3",
                "decision": "escalate_to_human",
            }
        )

        result = aggregate_advisor_metrics(tenant_id="t3")
        assert result.agent_decision_distribution["answered"] == 4
        assert result.agent_decision_distribution["escalated"] == 1
        assert result.escalation_rate == 0.2

    def test_tenant_isolation(self) -> None:
        record_event(
            {
                "event_type": "rag_query",
                "tenant_id": "t-a",
                "retrieval_mode": "bm25",
                "confidence_level": "high",
            }
        )
        record_event(
            {
                "event_type": "rag_query",
                "tenant_id": "t-b",
                "retrieval_mode": "hybrid",
                "confidence_level": "low",
            }
        )

        result_a = aggregate_advisor_metrics(tenant_id="t-a")
        result_b = aggregate_advisor_metrics(tenant_id="t-b")
        assert result_a.total_queries == 1
        assert result_a.retrieval_mode_distribution.get("bm25") == 1
        assert result_b.total_queries == 1
        assert result_b.retrieval_mode_distribution.get("hybrid") == 1

    def test_global_aggregation_across_tenants(self) -> None:
        record_event(
            {
                "event_type": "rag_query",
                "tenant_id": "t-x",
                "retrieval_mode": "bm25",
                "confidence_level": "high",
            }
        )
        record_event(
            {
                "event_type": "rag_query",
                "tenant_id": "t-y",
                "retrieval_mode": "hybrid",
                "confidence_level": "medium",
            }
        )

        result = aggregate_advisor_metrics(tenant_id=None)
        assert result.total_queries == 2
