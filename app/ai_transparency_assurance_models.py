"""Typed evidence model for EU AI Act Article 50 and GDPR transparency assurance."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class AIValueChainRole(StrEnum):
    unknown = "unknown"
    provider = "provider"
    deployer = "deployer"
    both = "both"


class TransparencyControlStatus(StrEnum):
    not_assessed = "not_assessed"
    not_applicable = "not_applicable"
    planned = "planned"
    implemented = "implemented"
    verified = "verified"


class TransparencyControlKey(StrEnum):
    ai_interaction_disclosure = "ai_interaction_disclosure"
    synthetic_content_marking = "synthetic_content_marking"
    emotion_biometric_notice = "emotion_biometric_notice"
    deepfake_disclosure = "deepfake_disclosure"
    public_interest_text_review_or_disclosure = "public_interest_text_review_or_disclosure"
    gdpr_transparency_notice = "gdpr_transparency_notice"


CONTROL_DEFINITIONS: dict[TransparencyControlKey, dict[str, str]] = {
    TransparencyControlKey.ai_interaction_disclosure: {
        "title_de": "KI-Interaktion offenlegen",
        "description_de": (
            "Betroffene Personen werden spätestens bei der ersten Interaktion klar und "
            "barrierearm darüber informiert, dass sie mit einem KI-System interagieren."
        ),
        "legal_basis": "EU AI Act Art. 50(1)",
        "accountable_role": "Provider",
    },
    TransparencyControlKey.synthetic_content_marking: {
        "title_de": "Synthetische Inhalte maschinenlesbar kennzeichnen",
        "description_de": (
            "KI-generierte oder manipulierte Ausgaben werden in einem maschinenlesbaren "
            "Format markiert und als künstlich erzeugt oder verändert erkennbar gemacht."
        ),
        "legal_basis": "EU AI Act Art. 50(2)",
        "accountable_role": "Provider",
    },
    TransparencyControlKey.emotion_biometric_notice: {
        "title_de": "Emotionserkennung und biometrische Kategorisierung anzeigen",
        "description_de": (
            "Betroffene Personen werden über den Betrieb eines Systems zur Emotionserkennung "
            "oder biometrischen Kategorisierung informiert."
        ),
        "legal_basis": "EU AI Act Art. 50(3)",
        "accountable_role": "Deployer",
    },
    TransparencyControlKey.deepfake_disclosure: {
        "title_de": "Deepfakes offenlegen",
        "description_de": (
            "Künstlich erzeugte oder manipulierte Bild-, Audio- oder Videoinhalte werden "
            "klar als solche offengelegt."
        ),
        "legal_basis": "EU AI Act Art. 50(4)",
        "accountable_role": "Deployer",
    },
    TransparencyControlKey.public_interest_text_review_or_disclosure: {
        "title_de": "Public-Interest-Texte prüfen oder offenlegen",
        "description_de": (
            "Bei KI-generiertem Text zu Angelegenheiten von öffentlichem Interesse wird die "
            "Offenlegung oder eine nachweislich substanzielle menschliche Prüfung mit "
            "redaktioneller Verantwortung dokumentiert."
        ),
        "legal_basis": "EU AI Act Art. 50(4)",
        "accountable_role": "Deployer",
    },
    TransparencyControlKey.gdpr_transparency_notice: {
        "title_de": "DSGVO-Transparenzinformation verknüpfen",
        "description_de": (
            "Die einschlägige Datenschutzinformation, Zwecke, Rechtsgrundlagen, Empfänger, "
            "Speicherdauer und Betroffenenrechte sind referenziert und geprüft."
        ),
        "legal_basis": "DSGVO Art. 12–14; ggf. Art. 22",
        "accountable_role": "Verantwortlicher",
    },
}


class TransparencyControlInput(BaseModel):
    control_key: TransparencyControlKey
    status: TransparencyControlStatus = TransparencyControlStatus.not_assessed
    evidence_reference: str | None = Field(default=None, max_length=1024)
    rationale: str | None = Field(default=None, max_length=4000)

    @field_validator("evidence_reference", "rationale", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class TransparencyControlRead(TransparencyControlInput):
    title_de: str
    description_de: str
    legal_basis: str
    accountable_role: str
    updated_at_utc: datetime | None = None


class AITransparencyAssessmentUpsert(BaseModel):
    expected_version: int = Field(default=0, ge=0)
    role_scope: AIValueChainRole = AIValueChainRole.unknown
    control_owner: str | None = Field(default=None, max_length=255)
    reviewer: str | None = Field(default=None, max_length=255)
    reviewed_at_utc: datetime | None = None
    review_due_at_utc: datetime | None = None
    controls: list[TransparencyControlInput] = Field(min_length=6, max_length=6)

    @field_validator("control_owner", "reviewer", mode="before")
    @classmethod
    def normalize_optional_identity(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("reviewed_at_utc", "review_due_at_utc")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("review timestamps must include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_assurance_evidence(self) -> AITransparencyAssessmentUpsert:
        expected_keys = set(TransparencyControlKey)
        actual_keys = [control.control_key for control in self.controls]
        if set(actual_keys) != expected_keys or len(set(actual_keys)) != len(actual_keys):
            raise ValueError("controls must contain every transparency control exactly once")

        verified = [
            control
            for control in self.controls
            if control.status == TransparencyControlStatus.verified
        ]
        missing_evidence = [
            control.control_key.value for control in verified if not control.evidence_reference
        ]
        if missing_evidence:
            raise ValueError(
                "verified controls require an evidence_reference: " + ", ".join(missing_evidence)
            )
        missing_rationale = [
            control.control_key.value
            for control in self.controls
            if control.status == TransparencyControlStatus.not_applicable and not control.rationale
        ]
        if missing_rationale:
            raise ValueError(
                "not_applicable controls require a rationale: " + ", ".join(missing_rationale)
            )
        if verified and (
            not self.control_owner
            or not self.reviewer
            or self.reviewed_at_utc is None
            or self.review_due_at_utc is None
        ):
            raise ValueError(
                "verified controls require control_owner, reviewer, reviewed_at_utc and "
                "review_due_at_utc"
            )
        if verified and self.role_scope == AIValueChainRole.unknown:
            raise ValueError("role_scope must be resolved before controls can be verified")
        if (
            self.control_owner
            and self.reviewer
            and self.control_owner.casefold() == self.reviewer.casefold()
        ):
            raise ValueError("reviewer must differ from control_owner (four-eyes principle)")
        if (
            self.reviewed_at_utc is not None
            and self.review_due_at_utc is not None
            and self.review_due_at_utc < self.reviewed_at_utc
        ):
            raise ValueError("review_due_at_utc cannot be before reviewed_at_utc")
        return self


class AITransparencyAssessmentRead(BaseModel):
    id: str | None = None
    tenant_id: str
    ai_system_id: str
    role_scope: AIValueChainRole
    control_owner: str | None = None
    reviewer: str | None = None
    reviewed_at_utc: datetime | None = None
    review_due_at_utc: datetime | None = None
    version: int = 0
    controls: list[TransparencyControlRead]
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None
    updated_by: str | None = None


class AITransparencySystemRow(BaseModel):
    ai_system_id: str
    ai_system_name: str
    business_unit: str
    risk_level: str
    ai_act_category: str
    assessment: AITransparencyAssessmentRead
    readiness_score_pct: int = Field(ge=0, le=100)
    posture: str
    applicable_controls: int = Field(ge=0)
    verified_controls: int = Field(ge=0)
    review_overdue: bool = False


class AITransparencyAssuranceSummary(BaseModel):
    total_systems: int = Field(ge=0)
    assessed_systems: int = Field(ge=0)
    requires_scope_count: int = Field(ge=0)
    verified_systems: int = Field(ge=0)
    overdue_review_count: int = Field(ge=0)
    applicable_controls: int = Field(ge=0)
    verified_controls: int = Field(ge=0)


class AITransparencyAssuranceResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    article_50_application_at_utc: datetime
    days_until_application: int
    readiness_score_pct: int = Field(ge=0, le=100)
    posture: str
    framework_version: str = "ec-article-50-guidelines-2026-07-20"
    source_url: str = (
        "https://digital-strategy.ec.europa.eu/en/faqs/"
        "transparency-obligations-under-article-50-ai-act"
    )
    legal_disclaimer_de: str = (
        "Operative Kontroll- und Evidenzunterstützung; keine Rechtsberatung und keine "
        "automatische Konformitätsfeststellung."
    )
    summary: AITransparencyAssuranceSummary
    systems: list[AITransparencySystemRow]


def default_transparency_controls() -> list[TransparencyControlRead]:
    return [
        TransparencyControlRead(
            control_key=key,
            status=TransparencyControlStatus.not_assessed,
            **definition,
        )
        for key, definition in CONTROL_DEFINITIONS.items()
    ]
