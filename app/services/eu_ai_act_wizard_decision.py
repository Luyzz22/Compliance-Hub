from __future__ import annotations

from app.ai_inventory_models import WizardDecisionResponse
from app.classification_models import ClassificationQuestionnaire
from app.services.classification_engine import classify_ai_system

DECISION_VERSION = "eu_ai_act_v1"


def evaluate_wizard_decision(
    ai_system_id: str,
    questionnaire: ClassificationQuestionnaire,
) -> WizardDecisionResponse:
    classification = classify_ai_system(ai_system_id, questionnaire)
    minimum_complete = bool(
        questionnaire.use_case_domain
        or questionnaire.is_product_or_safety_component
        or questionnaire.is_chatbot_or_conversational
        or questionnaire.generates_deepfakes
    )
    mapped_scope = {
        "eu_ai_act_scope": (
            "in_scope"
            if classification.risk_level.value in {"prohibited", "high_risk", "limited_risk"}
            else "review_needed"
        ),
        "iso_42001_scope": "in_scope",
        "nis2_scope": "review_needed",
        "dsgvo_special_risk": "review_needed",
    }
    return WizardDecisionResponse(
        decision_version=DECISION_VERSION,
        classification=classification,
        minimum_question_set_complete=minimum_complete,
        advisory_note_de=(
            "Vorläufige, regelbasierte Einstufung zur Governance-Steuerung. "
            "Keine verbindliche Rechtsauskunft und keine Rechtsberatung; "
            "finale Bewertung durch Fachberatung erforderlich."
        ),
        mapped_inventory_scope=mapped_scope,
    )
