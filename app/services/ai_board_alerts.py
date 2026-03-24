"""Board-KPI-Alerting: Schwellenwerte für NIS2 / EU AI Act / ISO 42001."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.ai_governance_models import AIBoardKpiSummary, AIKpiAlert
from app.compliance_gap_models import AIComplianceOverview
from app.config.nis2_kritis_board_alert_thresholds import (
    NIS2_KRITIS_FULL_COVERAGE_RATIO_ALERT,
    NIS2_KRITIS_INCIDENT_MATURITY_MEAN_ALERT_PCT,
    NIS2_KRITIS_OT_IT_ALERT_MIN_AFFECTED_SYSTEMS,
    NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT,
    NIS2_KRITIS_SUPPLIER_COVERAGE_MEAN_ALERT_PCT,
)
from app.datetime_compat import UTC
from app.services.nis2_kritis_alert_signals import Nis2KritisAlertSignals


def compute_board_alerts(
    tenant_id: str,
    board_kpis: AIBoardKpiSummary,
    compliance_overview: AIComplianceOverview | None,
    nis2_kritis_signals: Nis2KritisAlertSignals | None = None,
) -> list[AIKpiAlert]:
    """
    Leitet aus Board-KPIs und Compliance-Overview Alerts ab (on-the-fly, keine Persistenz).
    """
    now = datetime.now(UTC)
    alerts: list[AIKpiAlert] = []

    def add(
        kpi_key: str,
        severity: Literal["info", "warning", "critical"],
        msg: str,
    ) -> None:
        alerts.append(
            AIKpiAlert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                kpi_key=kpi_key,
                severity=severity,
                message=msg,
                created_at=now,
                resolved_at=None,
            )
        )

    # nis2_incident_readiness_ratio < 0.5 → critical
    if board_kpis.nis2_incident_readiness_ratio < 0.5:
        pct = int(board_kpis.nis2_incident_readiness_ratio * 100)
        add(
            "nis2_incident_readiness_ratio",
            "critical",
            f"NIS2 Incident Readiness < 50% ({pct}%) – akuter Handlungsbedarf bei Runbooks.",
        )

    # nis2_supplier_risk_coverage_ratio < 0.5 → warning; < 0.3 → critical
    r = board_kpis.nis2_supplier_risk_coverage_ratio
    if r < 0.3:
        pct = int(r * 100)
        add(
            "nis2_supplier_risk_coverage_ratio",
            "critical",
            f"NIS2 Supplier Risk Coverage {pct}% – Lieferanten-Risikoregister dringend ausbauen.",
        )
    elif r < 0.5:
        pct = int(r * 100)
        add(
            "nis2_supplier_risk_coverage_ratio",
            "warning",
            f"NIS2 Supplier Risk Coverage < 50% ({pct}%) – Handlungsbedarf bei Lieferanten-Risiko.",
        )

    # iso42001_governance_score < 0.4 → critical
    if board_kpis.iso42001_governance_score < 0.4:
        pct = int(board_kpis.iso42001_governance_score * 100)
        add(
            "iso42001_governance_score",
            "critical",
            f"ISO 42001 AI-Governance-Reife {pct}% – kritisches Niveau, Maßnahmen erforderlich.",
        )

    # EU AI Act / Readiness (aus Compliance-Overview)
    if compliance_overview is not None:
        readiness = compliance_overview.overall_readiness
        days = compliance_overview.days_remaining
        if readiness < 0.6:
            pct = int(readiness * 100)
            add(
                "overall_readiness",
                "warning",
                f"EU-AI-Act-/ISO-42001-Readiness {pct}% – unter Zielniveau.",
            )
        elif days < 180 and readiness < 0.8:
            pct = int(readiness * 100)
            add(
                "overall_readiness",
                "warning",
                f"Frist High-Risk in {days} Tagen – Readiness {pct}% unter 80%.",
            )

    # NIS2-/KRITIS-KPI-Tabellenwerte (Incident, Supplier, OT/IT)
    if nis2_kritis_signals is not None:
        inc = nis2_kritis_signals.incident_mean_percent
        if inc is not None and inc < NIS2_KRITIS_INCIDENT_MATURITY_MEAN_ALERT_PCT:
            add(
                "nis2_kritis_incident_maturity_low",
                "warning",
                f"NIS2/KRITIS Incident-Response-Reife (KPI-Mittel) {round(inc, 1)} % "
                f"unter {NIS2_KRITIS_INCIDENT_MATURITY_MEAN_ALERT_PCT} %.",
            )

        sup_mean = nis2_kritis_signals.supplier_mean_percent
        cov_ratio = board_kpis.nis2_kritis_systems_full_coverage_ratio
        thr_sup = NIS2_KRITIS_SUPPLIER_COVERAGE_MEAN_ALERT_PCT
        supplier_gap = sup_mean is not None and sup_mean < thr_sup
        coverage_gap = cov_ratio < NIS2_KRITIS_FULL_COVERAGE_RATIO_ALERT
        if supplier_gap or coverage_gap:
            parts: list[str] = []
            if supplier_gap and sup_mean is not None:
                parts.append(f"Supplier-KPI-Mittel {round(sup_mean, 1)} %")
            if coverage_gap:
                parts.append(
                    f"KPI-Vollständigkeit je System {int(cov_ratio * 100)} % "
                    f"(Ziel mindestens {int(NIS2_KRITIS_FULL_COVERAGE_RATIO_ALERT * 100)} %)",
                )
            add(
                "nis2_kritis_supplier_coverage_gap",
                "warning",
                "NIS2/KRITIS Supplier-Risiko: " + "; ".join(parts) + ".",
            )

        ot_n = nis2_kritis_signals.high_risk_focus_low_ot_it_count
        if ot_n >= NIS2_KRITIS_OT_IT_ALERT_MIN_AFFECTED_SYSTEMS:
            add(
                "nis2_kritis_ot_it_segmentation_risk",
                "critical",
                f"{ot_n} High-Risk-/Fokus-KI-Systeme mit OT/IT-Segmentierung "
                f"unter {NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT} % – "
                "Handlungsbedarf KRITIS/OT-Schnittstellen.",
            )

    return alerts
