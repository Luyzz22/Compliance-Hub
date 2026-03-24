"""Signale aus Nis2KritisKpiDB für Board-Alerts (Mittelwerte, OT/IT-Fokus)."""

from __future__ import annotations

from dataclasses import dataclass

from app.nis2_kritis_models import Nis2KritisKpiType
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository


@dataclass(frozen=True)
class Nis2KritisAlertSignals:
    incident_mean_percent: float | None
    supplier_mean_percent: float | None
    ot_it_mean_percent: float | None
    high_risk_focus_low_ot_it_count: int


def build_nis2_kritis_alert_signals(
    tenant_id: str,
    nis2_repo: Nis2KritisKpiRepository,
    *,
    ot_it_threshold_percent: int,
) -> Nis2KritisAlertSignals:
    means = nis2_repo.mean_percent_by_kpi_type(tenant_id)
    low_ot = nis2_repo.count_focus_systems_ot_it_below(
        tenant_id,
        threshold_percent=ot_it_threshold_percent,
    )
    return Nis2KritisAlertSignals(
        incident_mean_percent=means.get(Nis2KritisKpiType.INCIDENT_RESPONSE_MATURITY),
        supplier_mean_percent=means.get(Nis2KritisKpiType.SUPPLIER_RISK_COVERAGE),
        ot_it_mean_percent=means.get(Nis2KritisKpiType.OT_IT_SEGREGATION),
        high_risk_focus_low_ot_it_count=low_ot,
    )
