"""Board-KPI-Alerting: Schwellenwerte für NIS2 / EU AI Act / ISO 42001."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.ai_governance_models import AIBoardKpiSummary, AIKpiAlert, AIKpiAlertMetadata
from app.compliance_gap_models import AIComplianceOverview
from app.config.nis2_kritis_board_alert_thresholds import DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG
from app.datetime_compat import UTC
from app.services.nis2_kritis_alert_signals import Nis2KritisAlertSignals

_cfg = DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG


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
        alert_metadata: AIKpiAlertMetadata | None = None,
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
                alert_metadata=alert_metadata,
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
        inc_thr = float(_cfg.incident_maturity.mean_percent_warning)
        if inc is not None and inc < inc_thr:
            add(
                "nis2_kritis_incident_maturity_low",
                "warning",
                f"NIS2/KRITIS Incident-Response-Reife (KPI-Mittel) {round(inc, 1)} % "
                f"unter {int(inc_thr)} %.",
                AIKpiAlertMetadata(
                    current_percent=round(inc, 2),
                    threshold_percent=inc_thr,
                    kpi_type="INCIDENT_RESPONSE_MATURITY",
                    affected_system_ids=list(nis2_kritis_signals.incident_worst_system_ids),
                ),
            )

        sup_mean = nis2_kritis_signals.supplier_mean_percent
        cov_ratio = board_kpis.nis2_kritis_systems_full_coverage_ratio
        thr_sup = float(_cfg.supplier_coverage.mean_percent_warning)
        cov_thr = _cfg.supplier_coverage.full_coverage_ratio_warning
        supplier_gap = sup_mean is not None and sup_mean < thr_sup
        coverage_gap = cov_ratio < cov_thr
        if supplier_gap or coverage_gap:
            parts: list[str] = []
            if supplier_gap and sup_mean is not None:
                parts.append(f"Supplier-KPI-Mittel {round(sup_mean, 1)} %")
            if coverage_gap:
                parts.append(
                    f"KPI-Vollständigkeit je System {int(cov_ratio * 100)} % "
                    f"(Ziel mindestens {int(cov_thr * 100)} %)",
                )
            add(
                "nis2_kritis_supplier_coverage_gap",
                "warning",
                "NIS2/KRITIS Supplier-Risiko: " + "; ".join(parts) + ".",
                AIKpiAlertMetadata(
                    current_percent=round(sup_mean, 2) if sup_mean is not None else None,
                    threshold_percent=thr_sup if supplier_gap else None,
                    kpi_type="SUPPLIER_RISK_COVERAGE",
                    affected_system_ids=list(nis2_kritis_signals.supplier_worst_system_ids),
                    coverage_ratio_current=cov_ratio if coverage_gap else None,
                    coverage_ratio_threshold=cov_thr if coverage_gap else None,
                ),
            )

        ot_thr = float(_cfg.ot_it_segmentation.focus_system_value_below_percent)
        ot_min = _cfg.ot_it_segmentation.min_affected_systems_for_critical_alert
        ot_n = nis2_kritis_signals.high_risk_focus_low_ot_it_count
        if ot_n >= ot_min:
            add(
                "nis2_kritis_ot_it_segmentation_risk",
                "critical",
                f"{ot_n} High-Risk-/Fokus-KI-Systeme mit OT/IT-Segmentierung "
                f"unter {int(ot_thr)} % – "
                "Handlungsbedarf KRITIS/OT-Schnittstellen.",
                AIKpiAlertMetadata(
                    threshold_percent=ot_thr,
                    kpi_type="OT_IT_SEGREGATION",
                    affected_system_ids=list(nis2_kritis_signals.ot_it_worst_focus_system_ids),
                ),
            )

    return alerts
