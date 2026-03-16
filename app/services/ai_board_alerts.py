"""Board-KPI-Alerting: Schwellenwerte für NIS2 / EU AI Act / ISO 42001."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.ai_governance_models import AIBoardKpiSummary, AIKpiAlert
from app.compliance_gap_models import AIComplianceOverview
from app.datetime_compat import UTC


def compute_board_alerts(
    tenant_id: str,
    board_kpis: AIBoardKpiSummary,
    compliance_overview: AIComplianceOverview | None,
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

    return alerts
