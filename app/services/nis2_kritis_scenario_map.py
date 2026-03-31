from __future__ import annotations

from app.ai_system_models import AISystem, AISystemRiskLevel


def scenario_profile_id_for_ai_system(system: AISystem) -> str | None:
    """Heuristik: High-Risk-Szenario-Profil aus Geschäftsbereich und Kategorie ableiten."""
    if system.risk_level != AISystemRiskLevel.high:
        return None
    bu = (system.business_unit or "").lower()
    desc = (system.description or "").lower()

    if any(
        x in bu or x in desc
        for x in ("kritisch", "kritis", "infrastruktur", "energie", "versorgung", "ot/")
    ):
        return "critical_infrastructure_predictive_maintenance"
    if any(x in bu or x in desc for x in ("fertig", "produktion", "manufactur", "qualität")):
        return "manufacturing_quality_control"
    if any(x in bu or x in desc for x in ("gesund", "klinik", "medizin", "patient", "clinical")):
        return "clinical_decision_support"
    if any(x in bu or x in desc for x in ("biometr", "überwachung", "grenz", "sicherheit")):
        return "biometric_identification_high_risk"
    if any(x in bu or x in desc for x in ("personal", "hr", "recruit", "bewerb")):
        return "hr_recruitment_screening"
    return "hr_recruitment_screening"
