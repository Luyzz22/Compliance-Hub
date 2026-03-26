"""Strukturierte OAMI-Kurztexte (ohne LLM), deutsch, für UI und Reportings."""

from __future__ import annotations

from app.operational_monitoring_models import (
    OamiExplanationOut,
    SystemMonitoringIndexOut,
    TenantOperationalMonitoringIndexOut,
)


def explain_system_oami_de(result: SystemMonitoringIndexOut) -> OamiExplanationOut:
    """Haupttreiber aus Teilscores und Zählern (Tenant-System)."""
    if not result.has_data:
        return OamiExplanationOut(
            summary_de=(
                "Im gewählten Fenster liegen keine Laufzeit-Monitoring-Events vor. "
                "Operative Überwachung (z. B. SAP AI Core) ist nicht sichtbar "
                "oder noch nicht angebunden."
            ),
            drivers_de=[
                "Keine Signale zu Datenaktualität, Vorfällen oder "
                "Schwellenverletzungen im Fenster.",
            ],
            monitoring_gap_de=(
                "Anbindung von Laufzeit-Events oder Heartbeats empfehlen, um Post-Market-Signale "
                "zu dokumentieren."
            ),
        )

    c = result.components
    drivers: list[str] = []

    if c.freshness >= 0.7:
        drivers.append("Aktuelle Laufzeit-Signale (gute Datenaktualität).")
    elif c.freshness <= 0.35:
        drivers.append("Stagnierende oder veraltete Monitoring-Signale (Freshness niedrig).")

    if c.activity_days >= 0.5:
        drivers.append("Über viele Tage verteilte Aktivität im Fenster.")
    elif c.activity_days <= 0.2:
        drivers.append("Wenige aktive Tage – mögliche Lücke in der kontinuierlichen Überwachung.")

    sv = int(result.incident_count_by_subtype.get("safety_violation", 0))
    if sv > 0:
        drivers.append(
            f'{sv} sicherheitsrelevante Vorfälle (event_subtype "safety_violation") — '
            "stärkerer Einfluss auf den OAMI-Stabilitätsanteil."
        )

    if result.high_severity_incident_count > 0:
        drivers.append(
            f"{result.high_severity_incident_count} schwerwiegende Vorfälle (high/critical) "
            f"im Fenster ({result.incident_count} Vorfälle gesamt)."
        )
    elif result.incident_count > 0:
        drivers.append(
            f"{result.incident_count} Vorfälle ohne hohe Schwere – "
            "Stabilität wirkt begrenzt belastet."
        )
    else:
        drivers.append("Keine klassifizierten Vorfälle im Fenster.")

    if result.metric_threshold_breach_count > 0:
        drivers.append(
            f"{result.metric_threshold_breach_count} Schwellenverletzungen bei Metriken "
            "(Drift/Leistung)."
        )
    else:
        drivers.append("Keine Metrik-Schwellenverletzungen erfasst.")

    if c.metric_stability >= 0.75:
        drivers.append("Metrik-Stabilität aus Sicht der Schwellenwerte günstig.")

    level_de = {"low": "niedrig", "medium": "mittel", "high": "hoch"}[result.level]
    summary_de = (
        f"Operativer Monitoring-Index: {result.operational_monitoring_index}/100 ({level_de}). "
        f"Letztes Event: {'bekannt' if result.last_event_at else 'unbekannt'}."
    )

    gap: str | None = None
    if c.freshness <= 0.35 or c.activity_days <= 0.2:
        gap = "Kontinuität der Überwachung verbessern (regelmäßige Heartbeats oder KPI-Snapshots)."

    return OamiExplanationOut(
        summary_de=summary_de,
        drivers_de=drivers[:8],
        monitoring_gap_de=gap,
    )


def explain_tenant_oami_de(result: TenantOperationalMonitoringIndexOut) -> OamiExplanationOut:
    """Portfolio-/Tenant-Aggregat."""
    if not result.has_any_runtime_data or result.components is None:
        return OamiExplanationOut(
            summary_de=(
                "Mandantenweit keine Laufzeit-Events im Fenster – operatives KI-Monitoring "
                "ist nicht sichtbar."
            ),
            drivers_de=["Keine Systeme mit Monitoring-Signalen im gewählten Zeitraum."],
            monitoring_gap_de=(
                "SAP AI Core / BTP oder andere Quellen anbinden oder Seeds für Pilot nutzen."
            ),
        )

    c = result.components
    drivers: list[str] = [
        f"{result.systems_scored} KI-System(e) mit Laufzeitdaten im Fenster.",
    ]
    if c.incident_stability < 0.5:
        drivers.append("Erhöhte Vorfälle oder Schwellenbelastung in gewichteten Systemen.")
    if c.freshness < 0.5:
        drivers.append("Teils veraltete Signale – Prüfung der Datenpipelines sinnvoll.")
    if c.metric_stability >= 0.7:
        drivers.append("Metriken überwiegend stabil (wenige Schwellenverletzungen).")

    level_de = {"low": "niedrig", "medium": "mittel", "high": "hoch"}[result.level]
    summary_de = (
        f"Mandanten-OAMI: {result.operational_monitoring_index}/100 ({level_de}), "
        f"risikogewichtet über {result.systems_scored} System(e)."
    )
    return OamiExplanationOut(
        summary_de=summary_de,
        drivers_de=drivers[:8],
        monitoring_gap_de=None,
    )
