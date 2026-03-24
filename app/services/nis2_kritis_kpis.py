from __future__ import annotations

from app.ai_system_models import AISystem
from app.config.norm_evidence_defaults import HIGH_RISK_SCENARIO_PROFILES
from app.nis2_kritis_models import Nis2KritisKpiRecommended
from app.services.nis2_kritis_scenario_map import scenario_profile_id_for_ai_system


def recommended_kpis_for_ai_system(system: AISystem) -> Nis2KritisKpiRecommended | None:
    profile_id = scenario_profile_id_for_ai_system(system)
    if profile_id is None:
        return None
    raw = next((p for p in HIGH_RISK_SCENARIO_PROFILES if p["id"] == profile_id), None)
    if raw is None:
        return None
    return Nis2KritisKpiRecommended(
        scenario_profile_id=raw["id"],
        scenario_label=raw["label"],
        incident_response_maturity_percent=raw.get(
            "recommended_incident_response_maturity_percent",
        ),
        supplier_risk_coverage_percent=raw.get(
            "recommended_supplier_risk_coverage_percent",
        ),
        ot_it_segregation_percent=raw.get("recommended_ot_it_segregation_percent"),
    )
