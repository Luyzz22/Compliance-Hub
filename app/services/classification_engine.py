from __future__ import annotations

from app.classification_models import (
    ANNEX_III_DOMAIN_TO_CATEGORY,
    ClassificationPath,
    ClassificationQuestionnaire,
    RiskClassification,
    RiskLevel,
)


def classify_ai_system(
    ai_system_id: str,
    questionnaire: ClassificationQuestionnaire,
) -> RiskClassification:
    """Decision-tree classification per EU AI Act Art. 6.

    Optional LLM-gestützte Freitext-Hinweise (ohne Ersetzung dieser Logik):
    ``app.services.llm_compliance_tasks.draft_classification_assist``.

    Order:
    1. Prohibited check
    2. Annex I (safety component) path
    3. Annex III (use-case) path with Art. 6(3) exception
    4. Transparency obligations → limited_risk
    5. Default → minimal_risk
    """

    # Step 1: Prohibited
    prohibited_reasons = _check_prohibited(questionnaire)
    if prohibited_reasons:
        return RiskClassification(
            ai_system_id=ai_system_id,
            risk_level=RiskLevel.prohibited,
            classification_path=ClassificationPath.none,
            classification_rationale=f"Verbotene Praxis: {'; '.join(prohibited_reasons)}",
            profiles_natural_persons=questionnaire.profiles_natural_persons,
            confidence_score=1.0,
        )

    # Step 2: Annex I path
    if (
        questionnaire.is_product_or_safety_component
        and questionnaire.covered_by_eu_harmonisation_legislation
        and questionnaire.requires_third_party_conformity
    ):
        return RiskClassification(
            ai_system_id=ai_system_id,
            risk_level=RiskLevel.high_risk,
            classification_path=ClassificationPath.annex_i,
            annex_i_legislation=questionnaire.legislation_reference,
            is_safety_component=True,
            requires_third_party_assessment=True,
            profiles_natural_persons=questionnaire.profiles_natural_persons,
            classification_rationale=(
                "Hochrisiko via Anhang I (Art. 6 Abs. 1): Sicherheitskomponente unter "
                f"EU-Harmonisierungsrecht "
                f"({questionnaire.legislation_reference or 'nicht angegeben'}), "
                "Drittanbieter-Konformitätsbewertung erforderlich."
            ),
            confidence_score=1.0,
        )

    # Step 3: Annex III path
    domain = questionnaire.use_case_domain
    if domain and domain in ANNEX_III_DOMAIN_TO_CATEGORY:
        category = ANNEX_III_DOMAIN_TO_CATEGORY[domain]

        # Check Art. 6(3) exception
        exception_applies, exception_reason = _check_exception(questionnaire)

        if exception_applies and not questionnaire.profiles_natural_persons:
            return RiskClassification(
                ai_system_id=ai_system_id,
                risk_level=RiskLevel.minimal_risk,
                classification_path=ClassificationPath.annex_iii,
                annex_iii_category=category,
                exception_applies=True,
                exception_reason=exception_reason,
                profiles_natural_persons=False,
                classification_rationale=(
                    f"Anhang III Kategorie {category} ({domain}), aber Art. 6 Abs. 3 "
                    f"Ausnahme greift: {exception_reason}. "
                    "Kein Profiling natürlicher Personen."
                ),
                confidence_score=0.9,
            )

        # High risk via Annex III
        profiling_note = ""
        if questionnaire.profiles_natural_persons and exception_applies:
            profiling_note = (
                " Obwohl Art. 6(3) Ausnahmekriterien vorliegen, greift die Ausnahme "
                "nicht, da natürliche Personen profiliert werden."
            )
        return RiskClassification(
            ai_system_id=ai_system_id,
            risk_level=RiskLevel.high_risk,
            classification_path=ClassificationPath.annex_iii,
            annex_iii_category=category,
            profiles_natural_persons=questionnaire.profiles_natural_persons,
            classification_rationale=(
                "Hochrisiko via Anhang III (Art. 6 Abs. 2): Kategorie "
                f"{category} ({domain}).{profiling_note}"
            ),
            confidence_score=1.0,
        )

    # Step 4: Transparency obligations → limited_risk
    if (
        questionnaire.is_chatbot_or_conversational
        or questionnaire.generates_deepfakes
        or questionnaire.involves_emotion_recognition
    ):
        reasons = []
        if questionnaire.is_chatbot_or_conversational:
            reasons.append("Chatbot/Konversations-KI")
        if questionnaire.generates_deepfakes:
            reasons.append("Deepfake-Erzeugung")
        if questionnaire.involves_emotion_recognition:
            reasons.append("Emotionserkennung")
        return RiskClassification(
            ai_system_id=ai_system_id,
            risk_level=RiskLevel.limited_risk,
            classification_path=ClassificationPath.transparency,
            profiles_natural_persons=questionnaire.profiles_natural_persons,
            classification_rationale=(
                f"Begrenztes Risiko mit Transparenzpflichten: {', '.join(reasons)}."
            ),
            confidence_score=1.0,
        )

    # Step 5: Default → minimal_risk
    return RiskClassification(
        ai_system_id=ai_system_id,
        risk_level=RiskLevel.minimal_risk,
        classification_path=ClassificationPath.none,
        profiles_natural_persons=questionnaire.profiles_natural_persons,
        classification_rationale=(
            "Minimales Risiko: Keine der Hochrisiko- oder Transparenzkriterien erfüllt."
        ),
        confidence_score=1.0,
    )


def _check_prohibited(q: ClassificationQuestionnaire) -> list[str]:
    reasons: list[str] = []
    if q.involves_social_scoring:
        reasons.append("Sozialkreditsystem (Social Scoring)")
    if q.involves_subliminal_manipulation:
        reasons.append("Unterschwellige Manipulation")
    if q.exploits_vulnerabilities:
        reasons.append("Ausnutzung von Schwachstellen (Alter, Behinderung)")
    if q.involves_realtime_biometric_public:
        reasons.append(
            "Biometrische Echtzeit-Fernidentifizierung in öffentlich zugänglichen Räumen"
        )
    return reasons


def _check_exception(q: ClassificationQuestionnaire) -> tuple[bool, str | None]:
    """Check Art. 6(3) exception conditions."""
    reasons: list[str] = []
    if q.is_narrow_procedural_task:
        reasons.append("enge verfahrensbezogene Aufgabe")
    if q.improves_prior_human_activity:
        reasons.append(
            "Verbesserung eines zuvor abgeschlossenen menschlichen Tätigkeitsergebnisses"
        )
    if q.detects_patterns_without_replacing_human:
        reasons.append("Mustererkennung ohne Ersatz menschlicher Bewertung")
    if q.is_preparatory_task_only:
        reasons.append("rein vorbereitende Aufgabe")

    if reasons:
        return True, "; ".join(reasons)
    return False, None
