"""Deterministic rules: health status transitions → incidents (Operational Resilience MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HealthSignal = Literal["up", "degraded", "down"]
IncidentSeverity = Literal["warning", "critical"]


@dataclass(frozen=True)
class OpenIncidentInstruction:
    """When set, caller persists a new open service_health_incidents row + audit."""

    severity: IncidentSeverity
    title_de: str
    summary_de: str


@dataclass(frozen=True)
class TransitionDecision:
    """
    Outcome of comparing the last persisted service status with the new poll result.

    Duplicate polls (previous == current): open_incident is None and resolve_open is False —
    snapshots are still written by the poller for trend charts / audit replay.
    """

    open_incident: OpenIncidentInstruction | None
    resolve_open: bool


def evaluate_health_transition(
    previous_status: HealthSignal | str | None,
    current_status: HealthSignal | str,
) -> TransitionDecision:
    """
    Explainable NIS2 / ISO-style monitoring rules (code is the policy spec).

    Severity & incidents:
    - up -> degraded       → Warning incident (partial degradation; incident readiness review).
    - degraded -> down     → Critical incident (service effectively unavailable / escalation).
    - up -> down           → Critical incident (hard failure; may skip degraded if missed).
    - None -> degraded     → Warning (first observation already degraded — still actionable).
    - None -> down         → Critical (first observation is outage).
    - None -> up           → no incident (healthy baseline at first poll).

    Recovery (closes open monitoring incidents for this service):
    - degraded -> up       → resolve_open (service recovered to healthy).
    - down -> up           → resolve_open.

    Steady unhealthy (no NEW incident row — duplicate snapshot rule):
    - degraded -> degraded → no new incident.
    - down -> down         → no new incident.
    - up -> up             → no new incident.

    Note: resolve_open is independent: any transition *to* "up" from a non-up state triggers
    resolution of existing open incidents for that service (recovery path).
    """
    prev = previous_status
    cur = current_status

    if prev == cur:
        return TransitionDecision(open_incident=None, resolve_open=False)

    resolve_open = cur == "up" and prev is not None and prev != "up"

    if cur == "up":
        return TransitionDecision(open_incident=None, resolve_open=resolve_open)

    if cur == "degraded":
        if prev == "down":
            # down→degraded: partial recovery; keep critical incident open until "up".
            return TransitionDecision(open_incident=None, resolve_open=False)
        if prev is None or prev == "up":
            return TransitionDecision(
                open_incident=OpenIncidentInstruction(
                    severity="warning",
                    title_de="Service-Health: eingeschränkt (degraded)",
                    summary_de="Monitoring meldet eingeschränkten Betrieb. Incident Readiness und "
                    "NIS2-relevante Meldewege prüfen.",
                ),
                resolve_open=resolve_open,
            )

    if cur == "down":
        if prev == "degraded":
            return TransitionDecision(
                open_incident=OpenIncidentInstruction(
                    severity="critical",
                    title_de="Service-Health: Ausfall (degraded → down)",
                    summary_de="Kritischer Übergang — Incident Playbook, Business Continuity und "
                    "behördliche Meldefristen (NIS2/KRITIS-Kontext) prüfen.",
                ),
                resolve_open=False,
            )
        return TransitionDecision(
            open_incident=OpenIncidentInstruction(
                severity="critical",
                title_de="Service-Health: Ausfall",
                summary_de="Direkter oder erster Ausfallzustand — kritische Eskalation und "
                "Dokumentation auslösen.",
            ),
            resolve_open=False,
        )

    return TransitionDecision(open_incident=None, resolve_open=False)
