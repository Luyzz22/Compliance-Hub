"""Zentrale Schwellenkonfiguration für NIS2-/KRITIS-KPI-Board-Alerts.

Diese Werte steuern Alerts, die aus den tabellarisch gepflegten NIS2-/KRITIS-KPIs
(INCIDENT_RESPONSE_MATURITY, SUPPLIER_RISK_COVERAGE, OT_IT_SEGREGATION) abgeleitet werden.
Sie ergänzen die runbook-/register-basierten Board-Ratios (z. B. Anteil Systeme mit
Incident-Runbook), die direkt aus dem KI-System-Register kommen.

Normativer Kontext (Auszug):
- **NIS2 Art. 21** – Incident Handling, Krisenreaktion und betriebliche Widerstandsfähigkeit;
  die Incident-Response-Maturity-KPI adressiert die Reife dokumentierter Incident-Prozesse
  auf KI-Systemebene (KRITIS-/OT-Bezug über Fokus-Systeme).
- **NIS2 Art. 23** – Melde- und Benachrichtigungspflichten; niedrige Incident-Reife ist ein
  Hinweis auf Nachholbedarf vor meldepflichtigen Ereignissen.
- **NIS2 Art. 24** – Lieferketten-/Dienstleister-Risiken; Supplier-Risk-Coverage und
  „volle“ KPI-Erfassung je System unterstützen die Nachweisbarkeit gegenüber Aufsicht und WP.

Die konkreten Prozent-Schwellen sind betrieblich kalibrierbar; fachliche Begründungen stehen
an den jeweiligen Dataclass-Feldern.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncidentKpiAlertThresholds:
    """INCIDENT_RESPONSE_MATURITY – Mittelwert je Tenant (0–100)."""

    mean_percent_warning: int = 50
    mean_warning_rationale: str = (
        "Liegt der Mittelwert unter diesem Wert, besteht Nachholbedarf bei dokumentierter "
        "Incident-Response-Reife (NIS2 Art. 21 / operative Resilienz)."
    )


@dataclass(frozen=True)
class SupplierKpiAlertThresholds:
    """SUPPLIER_RISK_COVERAGE + KPI-Vollständigkeit (alle drei Typen je System)."""

    mean_percent_warning: int = 50
    mean_warning_rationale: str = (
        "Mittelwert Supplier-Risk-KPI unter diesem Wert deutet auf Lücken in der "
        "Supply-Chain-Absicherung hin (NIS2 Art. 24)."
    )
    full_coverage_ratio_warning: float = 0.5
    full_coverage_rationale: str = (
        "Anteil der KI-Systeme mit allen drei NIS2-/KRITIS-KPI-Typen; unter diesem Wert "
        "fehlen häufig Nachweise für Board- und Aufsichtsreporting."
    )


@dataclass(frozen=True)
class OtItKpiAlertThresholds:
    """OT_IT_SEGREGATION für Fokus-Systeme (High-Risk / hohe Criticality)."""

    focus_system_value_below_percent: int = 60
    value_rationale: str = (
        "OT/IT-Segmentierung unter diesem Wert bei Fokus-Systemen erhöht "
        "KRITIS-/Schnittstellenrisiken."
    )
    min_affected_systems_for_critical_alert: int = 2
    count_rationale: str = (
        "Erst ab dieser Anzahl betroffener Fokus-Systeme wird ein kritischer Alert ausgelöst "
        "(Häufung statt Einzelfall)."
    )


@dataclass(frozen=True)
class Nis2KritisThresholdConfig:
    """Alle NIS2-/KRITIS-KPI-Alertschwellen an einer Stelle (typsicher)."""

    incident_maturity: IncidentKpiAlertThresholds = IncidentKpiAlertThresholds()
    supplier_coverage: SupplierKpiAlertThresholds = SupplierKpiAlertThresholds()
    ot_it_segmentation: OtItKpiAlertThresholds = OtItKpiAlertThresholds()


DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG = Nis2KritisThresholdConfig()

# Rückwärtskompatible Modul-Konstanten (bestehende Imports)
_cfg = DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG
NIS2_KRITIS_INCIDENT_MATURITY_MEAN_ALERT_PCT = _cfg.incident_maturity.mean_percent_warning
NIS2_KRITIS_SUPPLIER_COVERAGE_MEAN_ALERT_PCT = _cfg.supplier_coverage.mean_percent_warning
NIS2_KRITIS_FULL_COVERAGE_RATIO_ALERT = _cfg.supplier_coverage.full_coverage_ratio_warning
NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT = _cfg.ot_it_segmentation.focus_system_value_below_percent
NIS2_KRITIS_OT_IT_ALERT_MIN_AFFECTED_SYSTEMS = (
    _cfg.ot_it_segmentation.min_affected_systems_for_critical_alert
)
