"""Shared GovernanceMaturityResponse fixtures for advisor brief golden scenarios (A–D)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.governance_maturity_models import (
    GovernanceActivityBlock,
    GovernanceMaturityResponse,
    GovernanceReadinessBlock,
    OperationalAiMonitoringBlock,
)

_FIXED_NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)


def governance_maturity_snapshot_scenario_a() -> GovernanceMaturityResponse:
    """A: basic / low / low — Grundlagen aufbauen."""
    return GovernanceMaturityResponse(
        tenant_id="golden-advisor-scenario-a",
        computed_at=_FIXED_NOW,
        readiness=GovernanceReadinessBlock(
            score=35,
            level="basic",
            interpretation="Struktureller Aufbau steht am Anfang.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=32,
            level="low",
            window_days=90,
            last_computed_at=_FIXED_NOW,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=30,
            level="low",
            window_days=90,
            message_de="Wenige belastbare Laufzeit-Signale im Fenster.",
            drivers_de=[],
        ),
    )


def governance_maturity_snapshot_scenario_b() -> GovernanceMaturityResponse:
    """B: managed / high / low — Monitoring nachziehen."""
    return GovernanceMaturityResponse(
        tenant_id="golden-advisor-scenario-b",
        computed_at=_FIXED_NOW,
        readiness=GovernanceReadinessBlock(
            score=58,
            level="managed",
            interpretation="Solide strukturelle Basis mit verbleibenden Lücken.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=78,
            level="high",
            window_days=90,
            last_computed_at=_FIXED_NOW,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=34,
            level="low",
            window_days=90,
            message_de="Laufzeit-Signale noch dünn; Monitoring ausbaufähig.",
            drivers_de=[],
        ),
    )


def governance_maturity_snapshot_scenario_c() -> GovernanceMaturityResponse:
    """C: embedded / medium / medium — Nutzung verbreitern."""
    return GovernanceMaturityResponse(
        tenant_id="golden-advisor-scenario-c",
        computed_at=_FIXED_NOW,
        readiness=GovernanceReadinessBlock(
            score=82,
            level="embedded",
            interpretation="Strukturell weit fortgeschritten.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=55,
            level="medium",
            window_days=90,
            last_computed_at=_FIXED_NOW,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=52,
            level="medium",
            window_days=90,
            message_de="Monitoring etabliert; Abdeckung ausbaufähig.",
            drivers_de=[],
        ),
    )


def governance_maturity_snapshot_scenario_d() -> GovernanceMaturityResponse:
    """D: embedded / high / high — Feintuning & Skalierung."""
    return GovernanceMaturityResponse(
        tenant_id="golden-advisor-scenario-d",
        computed_at=_FIXED_NOW,
        readiness=GovernanceReadinessBlock(
            score=90,
            level="embedded",
            interpretation="Integrierte KI-Governance.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=82,
            level="high",
            window_days=90,
            last_computed_at=_FIXED_NOW,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=76,
            level="high",
            window_days=90,
            message_de="Belastbare Laufzeit-Signale und Trends verfügbar.",
            drivers_de=[],
        ),
    )


SCENARIO_SNAPSHOTS: dict[str, GovernanceMaturityResponse] = {
    "a": governance_maturity_snapshot_scenario_a(),
    "b": governance_maturity_snapshot_scenario_b(),
    "c": governance_maturity_snapshot_scenario_c(),
    "d": governance_maturity_snapshot_scenario_d(),
}
