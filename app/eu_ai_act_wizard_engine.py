"""EU AI Act Wizard Engine: Entscheidungsbaum entlang Art. 5/6/51 + Pflichten-Mapping."""

from __future__ import annotations

from app.classification_models import ANNEX_III_DOMAIN_TO_CATEGORY
from app.eu_ai_act_wizard_models import (
    AIActRiskCategory,
    AIActRole,
    ArticleReference,
    WizardQuestionnaireRequest,
    WizardResult,
)

# ── Artikel-Pflichten-Katalog ───────────────────────────────────────────

_PROVIDER_HIGH_RISK_ARTICLES: list[ArticleReference] = [
    ArticleReference(
        article="Art. 9",
        title="Risikomanagementsystem",
        obligation_summary=(
            "Provider müssen ein Risikomanagementsystem einrichten und aufrechterhalten, "
            "das den gesamten Lebenszyklus des KI-Systems abdeckt."
        ),
    ),
    ArticleReference(
        article="Art. 10",
        title="Daten und Datengovernance",
        obligation_summary=(
            "Trainings-, Validierungs- und Testdaten müssen relevant, repräsentativ, "
            "fehlerfrei und vollständig sein (Daten-Provenance dokumentieren)."
        ),
    ),
    ArticleReference(
        article="Art. 11",
        title="Technische Dokumentation",
        obligation_summary=(
            "Technische Dokumentation gemäß Anhang IV erstellen und aktuell halten."
        ),
    ),
    ArticleReference(
        article="Art. 12",
        title="Aufzeichnungspflichten (Logging)",
        obligation_summary=(
            "Automatische Protokollierung von Ereignissen während des Betriebs sicherstellen."
        ),
    ),
    ArticleReference(
        article="Art. 13",
        title="Transparenz und Bereitstellung von Informationen",
        obligation_summary=("Betreibern transparente Gebrauchsanweisungen bereitstellen."),
    ),
    ArticleReference(
        article="Art. 14",
        title="Menschliche Aufsicht",
        obligation_summary=(
            "Das System so gestalten, dass eine wirksame menschliche Aufsicht möglich ist."
        ),
    ),
    ArticleReference(
        article="Art. 15",
        title="Genauigkeit, Robustheit und Cybersicherheit",
        obligation_summary=(
            "Angemessene Genauigkeit, Robustheit und Cybersicherheit gewährleisten."
        ),
    ),
    ArticleReference(
        article="Art. 72",
        title="Post-Market-Surveillance",
        obligation_summary=(
            "Provider richten ein Post-Market-Surveillance-System ein und dokumentieren "
            "die Überwachung über den gesamten Lebenszyklus."
        ),
    ),
]

_DEPLOYER_HIGH_RISK_ARTICLES: list[ArticleReference] = [
    ArticleReference(
        article="Art. 29",
        title="Pflichten der Betreiber (Deployer)",
        obligation_summary=(
            "Betreiber müssen geeignete technische und organisatorische Maßnahmen treffen, "
            "um das System gemäß Gebrauchsanweisung zu nutzen, und die menschliche Aufsicht "
            "durch qualifiziertes Personal sicherstellen."
        ),
    ),
    ArticleReference(
        article="Art. 29(6)",
        title="Grundrechte-Folgenabschätzung (FRIA)",
        obligation_summary=(
            "Deployer von Hochrisiko-KI-Systemen in bestimmten Bereichen müssen vor "
            "Inbetriebnahme eine Grundrechte-Folgenabschätzung durchführen."
        ),
    ),
    ArticleReference(
        article="Art. 13",
        title="Transparenz-Informationen nutzen",
        obligation_summary=(
            "Deployer müssen die vom Provider bereitgestellten Informationen "
            "verstehen und umsetzen."
        ),
    ),
]

_GPAI_ARTICLES: list[ArticleReference] = [
    ArticleReference(
        article="Art. 53",
        title="Pflichten für Anbieter von GPAI-Modellen",
        obligation_summary=(
            "Technische Dokumentation erstellen, Downstream-Provider informieren, "
            "Urheberrechtsrichtlinie einhalten, Trainings-Zusammenfassung veröffentlichen."
        ),
    ),
    ArticleReference(
        article="Art. 55",
        title="Pflichten bei systemischem Risiko",
        obligation_summary=(
            "Modell-Evaluation, Risikobewertung und -minderung bei systemischem Risiko, "
            "Meldung schwerwiegender Vorfälle an das AI Office."
        ),
    ),
]

_TRANSPARENCY_ARTICLES: list[ArticleReference] = [
    ArticleReference(
        article="Art. 50",
        title="Transparenzpflichten",
        obligation_summary=(
            "Nutzer über die Interaktion mit einem KI-System informieren; "
            "Deepfakes und KI-generierte Inhalte kennzeichnen."
        ),
    ),
]


def run_wizard(questionnaire: WizardQuestionnaireRequest) -> WizardResult:
    """Entscheidungsbaum für EU AI Act Klassifikation + Pflichten-Mapping."""

    # Step 1: Prohibited (Art. 5)
    prohibited_reasons = _check_prohibited(questionnaire)
    if prohibited_reasons:
        return WizardResult(
            ai_system_id=questionnaire.ai_system_id,
            role=questionnaire.role,
            risk_category=AIActRiskCategory.UNACCEPTABLE,
            classification_rationale=(
                f"Verbotene Praxis gemäß Art. 5: {'; '.join(prohibited_reasons)}"
            ),
            applicable_articles=[
                ArticleReference(
                    article="Art. 5",
                    title="Verbotene Praktiken",
                    obligation_summary="Dieses KI-System darf nicht in Betrieb genommen werden.",
                )
            ],
            obligations_summary="System darf NICHT eingesetzt werden (Art. 5 EU AI Act).",
            confidence_score=1.0,
        )

    # Step 2: GPAI (Art. 51-55)
    if questionnaire.is_general_purpose_ai:
        articles = list(_GPAI_ARTICLES)
        rationale = "General-Purpose AI Model gemäß Art. 51 EU AI Act."
        if questionnaire.gpai_has_systemic_risk:
            rationale += " Systemisches Risiko identifiziert (Art. 55)."
        return WizardResult(
            ai_system_id=questionnaire.ai_system_id,
            role=questionnaire.role,
            risk_category=AIActRiskCategory.GPAI,
            classification_rationale=rationale,
            applicable_articles=articles,
            obligations_summary=(
                "GPAI-Modell: Dokumentation, Downstream-Information, "
                "Urheberrechts-Compliance erforderlich."
            ),
            confidence_score=1.0,
        )

    # Step 3: High-risk via Annex I (Safety component)
    if (
        questionnaire.is_product_or_safety_component
        and questionnaire.covered_by_eu_harmonisation_legislation
        and questionnaire.requires_third_party_conformity
    ):
        articles = _articles_for_role(questionnaire.role)
        return WizardResult(
            ai_system_id=questionnaire.ai_system_id,
            role=questionnaire.role,
            risk_category=AIActRiskCategory.HIGH_RISK,
            classification_rationale=(
                "Hochrisiko via Anhang I (Art. 6 Abs. 1): Sicherheitskomponente unter "
                f"EU-Harmonisierungsrecht ({questionnaire.legislation_reference or 'k. A.'})."
            ),
            applicable_articles=articles,
            obligations_summary=_obligations_summary_for_role(questionnaire.role),
            confidence_score=1.0,
        )

    # Step 4: High-risk via Annex III (Use-case)
    domain = questionnaire.use_case_domain
    if domain and domain in ANNEX_III_DOMAIN_TO_CATEGORY:
        category = ANNEX_III_DOMAIN_TO_CATEGORY[domain]

        # Check Art. 6(3) exception
        exception_applies = _has_exception(questionnaire)

        if exception_applies and not questionnaire.profiles_natural_persons:
            return WizardResult(
                ai_system_id=questionnaire.ai_system_id,
                role=questionnaire.role,
                risk_category=AIActRiskCategory.LOW,
                classification_rationale=(
                    f"Anhang III Kategorie {category} ({domain}), "
                    "aber Art. 6(3) Ausnahme greift (kein Profiling)."
                ),
                applicable_articles=[],
                obligations_summary="Minimales Risiko – freiwillige Verhaltenskodizes empfohlen.",
                confidence_score=0.9,
            )

        articles = _articles_for_role(questionnaire.role)
        return WizardResult(
            ai_system_id=questionnaire.ai_system_id,
            role=questionnaire.role,
            risk_category=AIActRiskCategory.HIGH_RISK,
            classification_rationale=(
                f"Hochrisiko via Anhang III (Art. 6 Abs. 2): Kategorie {category} ({domain})."
            ),
            applicable_articles=articles,
            obligations_summary=_obligations_summary_for_role(questionnaire.role),
            confidence_score=1.0,
        )

    # Step 5: Transparency obligations -> LIMITED
    if (
        questionnaire.is_chatbot_or_conversational
        or questionnaire.generates_deepfakes
        or questionnaire.involves_emotion_recognition
    ):
        return WizardResult(
            ai_system_id=questionnaire.ai_system_id,
            role=questionnaire.role,
            risk_category=AIActRiskCategory.LIMITED,
            classification_rationale="Begrenztes Risiko mit Transparenzpflichten (Art. 50).",
            applicable_articles=list(_TRANSPARENCY_ARTICLES),
            obligations_summary=(
                "Transparenzpflichten: Nutzer über KI-Interaktion informieren, "
                "Deepfakes kennzeichnen."
            ),
            confidence_score=1.0,
        )

    # Step 6: Default -> LOW
    return WizardResult(
        ai_system_id=questionnaire.ai_system_id,
        role=questionnaire.role,
        risk_category=AIActRiskCategory.LOW,
        classification_rationale="Minimales Risiko – keine spezifischen Pflichten.",
        applicable_articles=[],
        obligations_summary="Minimales Risiko – freiwillige Verhaltenskodizes empfohlen.",
        confidence_score=1.0,
    )


# ── Helpers ──────────────────────────────────────────────────────────────


def _check_prohibited(q: WizardQuestionnaireRequest) -> list[str]:
    reasons: list[str] = []
    if q.involves_social_scoring:
        reasons.append("Sozialkreditsystem (Social Scoring)")
    if q.involves_subliminal_manipulation:
        reasons.append("Unterschwellige Manipulation")
    if q.exploits_vulnerabilities:
        reasons.append("Ausnutzung von Schwachstellen")
    if q.involves_realtime_biometric_public:
        reasons.append("Biometrische Echtzeit-Fernidentifizierung im öffentlichen Raum")
    return reasons


def _has_exception(q: WizardQuestionnaireRequest) -> bool:
    return any(
        [
            q.is_narrow_procedural_task,
            q.improves_prior_human_activity,
            q.detects_patterns_without_replacing_human,
            q.is_preparatory_task_only,
        ]
    )


def _articles_for_role(role: AIActRole) -> list[ArticleReference]:
    if role == AIActRole.deployer:
        return list(_DEPLOYER_HIGH_RISK_ARTICLES)
    # Provider, Importer, Distributor all share provider-level obligations
    return list(_PROVIDER_HIGH_RISK_ARTICLES)


def _obligations_summary_for_role(role: AIActRole) -> str:
    if role == AIActRole.deployer:
        return (
            "Deployer-Pflichten: System gemäß Gebrauchsanweisung nutzen, "
            "menschliche Aufsicht sicherstellen, FRIA bei Bedarf durchführen (Art. 29)."
        )
    if role == AIActRole.importer:
        return (
            "Importer-Pflichten: Konformitätsbewertung und CE-Kennzeichnung prüfen, "
            "Provider-Pflichten sicherstellen (Art. 26)."
        )
    if role == AIActRole.distributor:
        return (
            "Distributor-Pflichten: CE-Kennzeichnung und Konformität vor Bereitstellung "
            "prüfen (Art. 27)."
        )
    return (
        "Provider-Pflichten: Risikomanagementsystem, Datengovernance, technische "
        "Dokumentation, Logging, Transparenz, menschliche Aufsicht, "
        "Genauigkeit/Robustheit/Cybersicherheit, Post-Market-Surveillance (Art. 9-15, 72)."
    )
