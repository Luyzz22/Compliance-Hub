"""High-Risk-AI-Szenario-Profile (Manufacturing, KRITIS) – nur Konfiguration, keine Persistenz."""

from __future__ import annotations

from app.ai_governance_models import HighRiskScenarioProfile, NormEvidenceLinkCreate
from app.config.norm_evidence_defaults import HIGH_RISK_SCENARIO_PROFILES


def list_high_risk_scenarios() -> list[HighRiskScenarioProfile]:
    """Liefert statische High-Risk-Szenario-Profile mit empfohlenen Norm-Nachweisen."""
    profiles: list[HighRiskScenarioProfile] = []
    for raw in HIGH_RISK_SCENARIO_PROFILES:
        recommended = [
            NormEvidenceLinkCreate(
                framework=item["framework"],  # type: ignore[arg-type]
                reference=item["reference"],
                evidence_type=item["evidence_type"],  # type: ignore[arg-type]
                note=item.get("note"),
            )
            for item in raw["recommended_evidence"]
        ]
        profiles.append(
            HighRiskScenarioProfile(
                id=raw["id"],
                label=raw["label"],
                description=raw["description"],
                recommended_evidence=recommended,
                recommended_incident_response_maturity_percent=raw.get(
                    "recommended_incident_response_maturity_percent",
                ),
                recommended_supplier_risk_coverage_percent=raw.get(
                    "recommended_supplier_risk_coverage_percent",
                ),
                recommended_ot_it_segregation_percent=raw.get(
                    "recommended_ot_it_segregation_percent",
                ),
            ),
        )
    return profiles
