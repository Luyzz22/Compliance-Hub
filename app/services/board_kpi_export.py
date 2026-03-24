"""Board-/NIS2-KPI-Export für DMS, DATEV, SAP BTP (JSON/CSV)."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from app.ai_governance_models import BoardKpiExportEnvelope, BoardKpiExportSystemRow
from app.datetime_compat import UTC
from app.nis2_kritis_models import Nis2KritisKpiType
from app.repositories.ai_systems import AISystemRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.services.nis2_kritis_scenario_map import scenario_profile_id_for_ai_system


def build_board_kpi_export_envelope(
    tenant_id: str,
    ai_repo: AISystemRepository,
    nis2_repo: Nis2KritisKpiRepository,
) -> BoardKpiExportEnvelope:
    systems = ai_repo.list_for_tenant(tenant_id)
    rows: list[BoardKpiExportSystemRow] = []
    for s in systems:
        kpis = nis2_repo.list_for_ai_system(tenant_id, s.id)
        inc: int | None = None
        sup: int | None = None
        ot: int | None = None
        for k in kpis:
            if k.kpi_type == Nis2KritisKpiType.INCIDENT_RESPONSE_MATURITY:
                inc = k.value_percent
            elif k.kpi_type == Nis2KritisKpiType.SUPPLIER_RISK_COVERAGE:
                sup = k.value_percent
            elif k.kpi_type == Nis2KritisKpiType.OT_IT_SEGREGATION:
                ot = k.value_percent
        scenario_id = scenario_profile_id_for_ai_system(s)
        rows.append(
            BoardKpiExportSystemRow(
                ai_system_id=s.id,
                name=s.name,
                business_unit=s.business_unit,
                risk_level=s.risk_level.value,
                ai_act_category=s.ai_act_category.value,
                high_risk_scenario_profile_id=scenario_id,
                nis2_kritis_incident_response_maturity_percent=inc,
                nis2_kritis_supplier_risk_coverage_percent=sup,
                nis2_kritis_ot_it_segregation_percent=ot,
            )
        )
    return BoardKpiExportEnvelope(
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        systems=rows,
        regulatory_scope=["EU_AI_ACT", "NIS2", "ISO_42001"],
        generated_by="board_kpi_export_v1",
    )


def board_kpi_export_csv(envelope: BoardKpiExportEnvelope) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "tenant_id",
            "ai_system_id",
            "name",
            "business_unit",
            "risk_level",
            "ai_act_category",
            "high_risk_scenario_profile_id",
            "nis2_kritis_incident_response_maturity_percent",
            "nis2_kritis_supplier_risk_coverage_percent",
            "nis2_kritis_ot_it_segregation_percent",
            "export_generated_at",
            "format_version",
            "regulatory_scope",
            "generated_by",
        ]
    )
    gen = envelope.generated_at.isoformat() if envelope.generated_at else ""
    scope = "|".join(envelope.regulatory_scope)
    for r in envelope.systems:
        writer.writerow(
            [
                envelope.tenant_id,
                r.ai_system_id,
                r.name,
                r.business_unit,
                r.risk_level,
                r.ai_act_category,
                r.high_risk_scenario_profile_id or "",
                r.nis2_kritis_incident_response_maturity_percent
                if r.nis2_kritis_incident_response_maturity_percent is not None
                else "",
                r.nis2_kritis_supplier_risk_coverage_percent
                if r.nis2_kritis_supplier_risk_coverage_percent is not None
                else "",
                r.nis2_kritis_ot_it_segregation_percent
                if r.nis2_kritis_ot_it_segregation_percent is not None
                else "",
                gen,
                envelope.format_version,
                scope,
                envelope.generated_by,
            ]
        )
    return out.getvalue()
