"""Tests for the EU AI Act risk classification decision tree logic."""

from __future__ import annotations

import pytest

from app.classification_models import (
    ClassificationPath,
    ClassificationQuestionnaire,
    RiskLevel,
)
from app.services.classification_engine import classify_ai_system

# ─── Step 1: Prohibited practices ───────────────────────────────────────────────


class TestProhibitedClassification:
    def test_social_scoring(self) -> None:
        q = ClassificationQuestionnaire(involves_social_scoring=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited
        assert "Sozialkreditsystem" in result.classification_rationale

    def test_subliminal_manipulation(self) -> None:
        q = ClassificationQuestionnaire(involves_subliminal_manipulation=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited
        assert "Unterschwellige Manipulation" in result.classification_rationale

    def test_exploits_vulnerabilities(self) -> None:
        q = ClassificationQuestionnaire(exploits_vulnerabilities=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited

    def test_realtime_biometric_public(self) -> None:
        q = ClassificationQuestionnaire(involves_realtime_biometric_public=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited
        assert "Echtzeit-Fernidentifizierung" in result.classification_rationale

    def test_multiple_prohibited(self) -> None:
        q = ClassificationQuestionnaire(
            involves_social_scoring=True,
            involves_subliminal_manipulation=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited
        assert "Sozialkreditsystem" in result.classification_rationale
        assert "Unterschwellige Manipulation" in result.classification_rationale

    def test_prohibited_takes_precedence_over_annex_i(self) -> None:
        q = ClassificationQuestionnaire(
            involves_social_scoring=True,
            is_product_or_safety_component=True,
            covered_by_eu_harmonisation_legislation=True,
            requires_third_party_conformity=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited


# ─── Step 2: Annex I (safety component) path ────────────────────────────────────


class TestAnnexIClassification:
    def test_full_annex_i_path(self) -> None:
        q = ClassificationQuestionnaire(
            is_product_or_safety_component=True,
            covered_by_eu_harmonisation_legislation=True,
            requires_third_party_conformity=True,
            legislation_reference="Machinery Regulation 2023/1230",
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.classification_path == ClassificationPath.annex_i
        assert result.is_safety_component is True
        assert result.requires_third_party_assessment is True
        assert result.annex_i_legislation == "Machinery Regulation 2023/1230"

    def test_missing_third_party_not_high_risk_via_annex_i(self) -> None:
        q = ClassificationQuestionnaire(
            is_product_or_safety_component=True,
            covered_by_eu_harmonisation_legislation=True,
            requires_third_party_conformity=False,
        )
        result = classify_ai_system("sys-1", q)
        # Falls through to minimal risk (no annex III, no transparency)
        assert result.risk_level == RiskLevel.minimal_risk

    def test_missing_legislation_not_high_risk_via_annex_i(self) -> None:
        q = ClassificationQuestionnaire(
            is_product_or_safety_component=True,
            covered_by_eu_harmonisation_legislation=False,
            requires_third_party_conformity=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.minimal_risk


# ─── Step 3: Annex III (use case) path ──────────────────────────────────────────


class TestAnnexIIIClassification:
    @pytest.mark.parametrize(
        "domain,expected_category",
        [
            ("biometrics", 1),
            ("critical_infra", 2),
            ("education", 3),
            ("employment", 4),
            ("essential_services", 5),
            ("law_enforcement", 6),
            ("migration", 7),
            ("justice", 8),
        ],
    )
    def test_all_annex_iii_domains(self, domain: str, expected_category: int) -> None:
        q = ClassificationQuestionnaire(use_case_domain=domain)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.classification_path == ClassificationPath.annex_iii
        assert result.annex_iii_category == expected_category

    def test_unknown_domain_not_high_risk(self) -> None:
        q = ClassificationQuestionnaire(use_case_domain="entertainment")
        result = classify_ai_system("sys-1", q)
        assert result.risk_level != RiskLevel.high_risk


# ─── Step 3b: Art. 6(3) exception ───────────────────────────────────────────────


class TestArt6_3Exception:
    def test_narrow_procedural_task_exception(self) -> None:
        q = ClassificationQuestionnaire(
            use_case_domain="employment",
            is_narrow_procedural_task=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.minimal_risk
        assert result.exception_applies is True
        assert "enge verfahrensbezogene Aufgabe" in (result.exception_reason or "")

    def test_improves_prior_human_activity_exception(self) -> None:
        q = ClassificationQuestionnaire(
            use_case_domain="education",
            improves_prior_human_activity=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.minimal_risk
        assert result.exception_applies is True

    def test_exception_overridden_by_profiling(self) -> None:
        """Art. 6(3): exception does NOT apply if it profiles natural persons."""
        q = ClassificationQuestionnaire(
            use_case_domain="employment",
            is_narrow_procedural_task=True,
            profiles_natural_persons=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.profiles_natural_persons is True
        assert "profiliert" in result.classification_rationale

    def test_no_exception_without_criteria(self) -> None:
        q = ClassificationQuestionnaire(use_case_domain="law_enforcement")
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.exception_applies is False

    def test_multiple_exception_criteria(self) -> None:
        q = ClassificationQuestionnaire(
            use_case_domain="essential_services",
            is_narrow_procedural_task=True,
            is_preparatory_task_only=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.minimal_risk
        assert result.exception_applies is True


# ─── Step 4: Transparency / limited risk ─────────────────────────────────────────


class TestLimitedRiskClassification:
    def test_chatbot(self) -> None:
        q = ClassificationQuestionnaire(is_chatbot_or_conversational=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.limited_risk
        assert result.classification_path == ClassificationPath.transparency

    def test_deepfakes(self) -> None:
        q = ClassificationQuestionnaire(generates_deepfakes=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.limited_risk

    def test_emotion_recognition(self) -> None:
        q = ClassificationQuestionnaire(involves_emotion_recognition=True)
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.limited_risk


# ─── Step 5: Minimal risk (default) ─────────────────────────────────────────────


class TestMinimalRiskClassification:
    def test_empty_questionnaire(self) -> None:
        q = ClassificationQuestionnaire()
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.minimal_risk
        assert result.classification_path == ClassificationPath.none

    def test_confidence_score(self) -> None:
        q = ClassificationQuestionnaire()
        result = classify_ai_system("sys-1", q)
        assert result.confidence_score == 1.0
        assert result.classified_by == "auto"


# ─── Priority ordering ──────────────────────────────────────────────────────────


class TestClassificationPriority:
    def test_prohibited_over_high_risk_annex_iii(self) -> None:
        q = ClassificationQuestionnaire(
            involves_social_scoring=True,
            use_case_domain="biometrics",
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.prohibited

    def test_annex_i_over_annex_iii(self) -> None:
        q = ClassificationQuestionnaire(
            is_product_or_safety_component=True,
            covered_by_eu_harmonisation_legislation=True,
            requires_third_party_conformity=True,
            use_case_domain="employment",
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.classification_path == ClassificationPath.annex_i

    def test_annex_iii_over_transparency(self) -> None:
        q = ClassificationQuestionnaire(
            use_case_domain="biometrics",
            involves_emotion_recognition=True,
        )
        result = classify_ai_system("sys-1", q)
        assert result.risk_level == RiskLevel.high_risk
        assert result.classification_path == ClassificationPath.annex_iii
