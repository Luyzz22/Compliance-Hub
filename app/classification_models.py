from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RiskLevel(str, Enum):
    prohibited = "prohibited"
    high_risk = "high_risk"
    limited_risk = "limited_risk"
    minimal_risk = "minimal_risk"


class ClassificationPath(str, Enum):
    none = "none"
    annex_i = "annex_i"
    annex_iii = "annex_iii"
    transparency = "transparency"


class ClassificationQuestionnaire(BaseModel):
    # Step 1: Prohibited practices
    involves_social_scoring: bool = False
    involves_subliminal_manipulation: bool = False
    exploits_vulnerabilities: bool = False
    involves_realtime_biometric_public: bool = False

    # Step 2: Annex I (Safety Component) check
    is_product_or_safety_component: bool = False
    covered_by_eu_harmonisation_legislation: bool = False
    legislation_reference: str | None = None
    requires_third_party_conformity: bool = False

    # Step 3: Annex III (Use Case) check
    use_case_domain: str | None = None
    # biometrics, critical_infra, education, employment,
    # essential_services, law_enforcement, migration, justice
    specific_use_case: str | None = None

    # Step 4: Exception check (Art. 6(3))
    is_narrow_procedural_task: bool = False
    improves_prior_human_activity: bool = False
    detects_patterns_without_replacing_human: bool = False
    is_preparatory_task_only: bool = False
    profiles_natural_persons: bool = False

    # Step 5: Transparency obligations
    is_chatbot_or_conversational: bool = False
    generates_deepfakes: bool = False
    involves_emotion_recognition: bool = False


ANNEX_III_DOMAIN_TO_CATEGORY: dict[str, int] = {
    "biometrics": 1,
    "critical_infra": 2,
    "education": 3,
    "employment": 4,
    "essential_services": 5,
    "law_enforcement": 6,
    "migration": 7,
    "justice": 8,
}


class RiskClassification(BaseModel):
    ai_system_id: str
    risk_level: RiskLevel
    classification_path: ClassificationPath
    annex_i_legislation: str | None = None
    is_safety_component: bool = False
    requires_third_party_assessment: bool = False
    annex_iii_category: int | None = None
    profiles_natural_persons: bool = False
    exception_applies: bool = False
    exception_reason: str | None = None
    classification_rationale: str | None = None
    confidence_score: float = 1.0
    classified_by: str = "auto"
