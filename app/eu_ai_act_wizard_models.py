"""EU AI Act Wizard: Rollen, erweiterter Fragebogen, Pflichten-Mapping & Klassifikation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AIActRole(StrEnum):
    """Rollen gemäß EU AI Act Art. 3."""

    provider = "provider"
    deployer = "deployer"
    importer = "importer"
    distributor = "distributor"


class AIActRiskCategory(StrEnum):
    """Ergebnis-Klassifikation des Wizards."""

    UNACCEPTABLE = "UNACCEPTABLE"
    HIGH_RISK = "HIGH_RISK"
    GPAI = "GPAI"
    LIMITED = "LIMITED"
    LOW = "LOW"


class WizardQuestionnaireRequest(BaseModel):
    """Erweiterter Fragebogen entlang Anhang III + Art. 6/9/10/13/29."""

    ai_system_id: str = Field(..., min_length=1, max_length=255)

    # Role
    role: AIActRole = AIActRole.provider

    # Step 1: Prohibited practices (Art. 5)
    involves_social_scoring: bool = False
    involves_subliminal_manipulation: bool = False
    exploits_vulnerabilities: bool = False
    involves_realtime_biometric_public: bool = False

    # Step 2: GPAI check (Art. 51-55)
    is_general_purpose_ai: bool = False
    gpai_has_systemic_risk: bool = False

    # Step 3: Annex I (Safety component) check
    is_product_or_safety_component: bool = False
    covered_by_eu_harmonisation_legislation: bool = False
    legislation_reference: str | None = None
    requires_third_party_conformity: bool = False

    # Step 4: Annex III (Use-case) check
    use_case_domain: str | None = None
    specific_use_case: str | None = None

    # Step 5: Exception check (Art. 6(3))
    is_narrow_procedural_task: bool = False
    improves_prior_human_activity: bool = False
    detects_patterns_without_replacing_human: bool = False
    is_preparatory_task_only: bool = False
    profiles_natural_persons: bool = False

    # Step 6: Transparency obligations (Art. 50)
    is_chatbot_or_conversational: bool = False
    generates_deepfakes: bool = False
    involves_emotion_recognition: bool = False

    # Step 7: Deployer-specific (Art. 29)
    deployer_uses_high_risk_system: bool = False
    deployer_has_fria: bool = False


class ArticleReference(BaseModel):
    """Referenzierter EU-AI-Act-Artikel."""

    article: str = Field(..., description="z. B. 'Art. 9'")
    title: str
    obligation_summary: str


class WizardResult(BaseModel):
    """Ergebnis des EU-AI-Act-Wizard-Durchlaufs."""

    ai_system_id: str
    role: AIActRole
    risk_category: AIActRiskCategory
    classification_rationale: str
    applicable_articles: list[ArticleReference]
    obligations_summary: str
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
