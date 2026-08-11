"""Evidence-led DSFA/DPIA and fundamental-rights impact assessment models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class ImpactAssessmentScope(StrEnum):
    undetermined = "undetermined"
    required = "required"
    not_required = "not_required"


class ImpactAssessmentLifecycle(StrEnum):
    draft = "draft"
    in_review = "in_review"
    remediation_required = "remediation_required"
    approved = "approved"


class ImpactDeployerContext(StrEnum):
    unknown = "unknown"
    public_authority = "public_authority"
    public_service_provider = "public_service_provider"
    essential_private_service = "essential_private_service"
    other = "other"


class ImpactResidualRisk(StrEnum):
    unknown = "unknown"
    low = "low"
    medium = "medium"
    high = "high"


class PriorConsultationStatus(StrEnum):
    not_assessed = "not_assessed"
    not_required = "not_required"
    required = "required"
    planned = "planned"
    submitted = "submitted"
    closed = "closed"


class StakeholderViewsStatus(StrEnum):
    not_assessed = "not_assessed"
    not_applicable = "not_applicable"
    planned = "planned"
    obtained = "obtained"


class ImpactSectionStatus(StrEnum):
    not_started = "not_started"
    drafted = "drafted"
    evidenced = "evidenced"
    reviewed = "reviewed"
    not_applicable = "not_applicable"


class ImpactSectionKey(StrEnum):
    processing_description_and_purpose = "processing_description_and_purpose"
    necessity_and_proportionality = "necessity_and_proportionality"
    deployment_period_and_frequency = "deployment_period_and_frequency"
    affected_persons_and_groups = "affected_persons_and_groups"
    rights_and_freedoms_risks = "rights_and_freedoms_risks"
    safeguards_security_and_mitigations = "safeguards_security_and_mitigations"
    human_oversight_and_governance = "human_oversight_and_governance"
    incident_complaint_and_redress = "incident_complaint_and_redress"


SECTION_DEFINITIONS: dict[ImpactSectionKey, dict[str, str]] = {
    ImpactSectionKey.processing_description_and_purpose: {
        "title_de": "Verarbeitung, Einsatzprozess und Zwecke",
        "description_de": (
            "Beschreibt Datenverarbeitung, vorgesehenen KI-Einsatz, fachliche Zwecke und die "
            "konkreten Prozesse, in denen das System verwendet wird."
        ),
        "legal_basis": "DSGVO Art. 35(7)(a); EU AI Act Art. 27(1)(a)",
    },
    ImpactSectionKey.necessity_and_proportionality: {
        "title_de": "Erforderlichkeit und Verhältnismäßigkeit",
        "description_de": (
            "Bewertet, warum der Einsatz für den dokumentierten Zweck erforderlich ist, welche "
            "Alternativen geprüft wurden und wie Daten- und Funktionsumfang begrenzt werden."
        ),
        "legal_basis": "DSGVO Art. 35(7)(b)",
    },
    ImpactSectionKey.deployment_period_and_frequency: {
        "title_de": "Einsatzzeitraum und Häufigkeit",
        "description_de": (
            "Dokumentiert Start, Dauer, Nutzungshäufigkeit, Reichweite und relevante "
            "Änderungsereignisse des vorgesehenen Einsatzes."
        ),
        "legal_basis": "EU AI Act Art. 27(1)(b)",
    },
    ImpactSectionKey.affected_persons_and_groups: {
        "title_de": "Betroffene Personen und Gruppen",
        "description_de": (
            "Erfasst Kategorien betroffener Personen und Gruppen einschließlich möglicher "
            "besonderer Schutzbedarfe, ohne unnötige personenbezogene Einzeldaten."
        ),
        "legal_basis": "EU AI Act Art. 27(1)(c); DSGVO Art. 35(9)",
    },
    ImpactSectionKey.rights_and_freedoms_risks: {
        "title_de": "Risiken für Rechte und Freiheiten",
        "description_de": (
            "Beschreibt plausible Datenschutz- und Grundrechtsbeeinträchtigungen, Ursachen, "
            "Betroffenheit und fachlich begründete Risikobewertung."
        ),
        "legal_basis": "DSGVO Art. 35(7)(c); EU AI Act Art. 27(1)(d)",
    },
    ImpactSectionKey.safeguards_security_and_mitigations: {
        "title_de": "Garantien, Sicherheit und Abhilfen",
        "description_de": (
            "Verknüpft technische und organisatorische Maßnahmen, Sicherheitskontrollen und "
            "Abhilfen mit den identifizierten Risiken."
        ),
        "legal_basis": "DSGVO Art. 35(7)(d)",
    },
    ImpactSectionKey.human_oversight_and_governance: {
        "title_de": "Human Oversight und Governance",
        "description_de": (
            "Legt kompetente menschliche Aufsicht, Eingriffsrechte, Eskalation, Rollen und "
            "Entscheidungsgrenzen für den Einsatz fest."
        ),
        "legal_basis": "EU AI Act Art. 27(1)(e)",
    },
    ImpactSectionKey.incident_complaint_and_redress: {
        "title_de": "Vorfall, Beschwerde und Abhilfe",
        "description_de": (
            "Dokumentiert Reaktion bei Risikoeintritt sowie interne Governance-, Beschwerde- "
            "und Abhilfemechanismen für betroffene Personen."
        ),
        "legal_basis": "EU AI Act Art. 27(1)(f); DSGVO Art. 36",
    },
}


class ImpactAssessmentSectionInput(BaseModel):
    section_key: ImpactSectionKey
    status: ImpactSectionStatus = ImpactSectionStatus.not_started
    summary: str | None = Field(default=None, max_length=8000)
    evidence_reference: str | None = Field(default=None, max_length=1024)
    rationale: str | None = Field(default=None, max_length=4000)

    @field_validator("summary", "evidence_reference", "rationale", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class ImpactAssessmentSectionRead(ImpactAssessmentSectionInput):
    title_de: str
    description_de: str
    legal_basis: str
    updated_at_utc: datetime | None = None


class AIImpactAssessmentUpsert(BaseModel):
    expected_version: int = Field(default=0, ge=0)
    dpia_scope: ImpactAssessmentScope = ImpactAssessmentScope.undetermined
    fria_scope: ImpactAssessmentScope = ImpactAssessmentScope.undetermined
    deployer_context: ImpactDeployerContext = ImpactDeployerContext.unknown
    scope_rationale: str | None = Field(default=None, max_length=4000)
    lifecycle_status: ImpactAssessmentLifecycle = ImpactAssessmentLifecycle.draft
    residual_risk: ImpactResidualRisk = ImpactResidualRisk.unknown
    assessment_owner: str | None = Field(default=None, max_length=255)
    independent_reviewer: str | None = Field(default=None, max_length=255)
    dpo_involved: bool = False
    stakeholder_views_status: StakeholderViewsStatus = StakeholderViewsStatus.not_assessed
    prior_consultation_status: PriorConsultationStatus = PriorConsultationStatus.not_assessed
    prior_consultation_reference: str | None = Field(default=None, max_length=1024)
    reviewed_at_utc: datetime | None = None
    approved_at_utc: datetime | None = None
    review_due_at_utc: datetime | None = None
    sections: list[ImpactAssessmentSectionInput] = Field(min_length=8, max_length=8)

    @field_validator(
        "scope_rationale",
        "assessment_owner",
        "independent_reviewer",
        "prior_consultation_reference",
        mode="before",
    )
    @classmethod
    def normalize_optional_identity(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("reviewed_at_utc", "approved_at_utc", "review_due_at_utc")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("assessment timestamps must include a UTC offset")
        return value

    @model_validator(mode="after")
    def validate_impact_assessment(self) -> AIImpactAssessmentUpsert:
        expected_keys = set(ImpactSectionKey)
        actual_keys = [section.section_key for section in self.sections]
        if set(actual_keys) != expected_keys or len(set(actual_keys)) != len(actual_keys):
            raise ValueError("sections must contain every impact-assessment section exactly once")

        missing_review_evidence = [
            section.section_key.value
            for section in self.sections
            if section.status == ImpactSectionStatus.reviewed
            and (not section.summary or not section.evidence_reference)
        ]
        if missing_review_evidence:
            raise ValueError(
                "reviewed sections require summary and evidence_reference: "
                + ", ".join(missing_review_evidence)
            )
        missing_na_rationale = [
            section.section_key.value
            for section in self.sections
            if section.status == ImpactSectionStatus.not_applicable and not section.rationale
        ]
        if missing_na_rationale:
            raise ValueError(
                "not_applicable sections require a rationale: " + ", ".join(missing_na_rationale)
            )

        if (
            self.dpia_scope == ImpactAssessmentScope.not_required
            or self.fria_scope == ImpactAssessmentScope.not_required
        ) and not self.scope_rationale:
            raise ValueError("a not_required scope requires scope_rationale")

        if (
            self.assessment_owner
            and self.independent_reviewer
            and self.assessment_owner.casefold() == self.independent_reviewer.casefold()
        ):
            raise ValueError(
                "independent_reviewer must differ from assessment_owner (four-eyes principle)"
            )

        if (
            self.prior_consultation_status
            in {PriorConsultationStatus.submitted, PriorConsultationStatus.closed}
            and not self.prior_consultation_reference
        ):
            raise ValueError(
                "submitted or closed prior consultation requires prior_consultation_reference"
            )

        if (
            self.reviewed_at_utc is not None
            and self.review_due_at_utc is not None
            and self.review_due_at_utc < self.reviewed_at_utc
        ):
            raise ValueError("review_due_at_utc cannot be before reviewed_at_utc")
        if (
            self.reviewed_at_utc is not None
            and self.approved_at_utc is not None
            and self.approved_at_utc < self.reviewed_at_utc
        ):
            raise ValueError("approved_at_utc cannot be before reviewed_at_utc")

        if (
            self.lifecycle_status
            in {
                ImpactAssessmentLifecycle.in_review,
                ImpactAssessmentLifecycle.remediation_required,
                ImpactAssessmentLifecycle.approved,
            }
            and not self.assessment_owner
        ):
            raise ValueError("in-review assessments require assessment_owner")

        if self.lifecycle_status != ImpactAssessmentLifecycle.approved:
            return self

        if (
            self.dpia_scope == ImpactAssessmentScope.undetermined
            or self.fria_scope == ImpactAssessmentScope.undetermined
        ):
            raise ValueError("approved assessments require resolved DPIA and FRIA scope")
        if (
            not self.assessment_owner
            or not self.independent_reviewer
            or self.reviewed_at_utc is None
            or self.approved_at_utc is None
            or self.review_due_at_utc is None
        ):
            raise ValueError(
                "approved assessments require assessment_owner, independent_reviewer, "
                "reviewed_at_utc, approved_at_utc and review_due_at_utc"
            )
        if self.dpia_scope == ImpactAssessmentScope.required and not self.dpo_involved:
            raise ValueError("approved DPIA assessments require documented DPO involvement")

        required_scope = (
            self.dpia_scope == ImpactAssessmentScope.required
            or self.fria_scope == ImpactAssessmentScope.required
        )
        if required_scope:
            incomplete = [
                section.section_key.value
                for section in self.sections
                if section.status != ImpactSectionStatus.reviewed
            ]
            if incomplete:
                raise ValueError(
                    "approved in-scope assessments require every section reviewed: "
                    + ", ".join(incomplete)
                )
            if self.residual_risk == ImpactResidualRisk.unknown:
                raise ValueError("approved in-scope assessments require a residual_risk")
        if (
            self.residual_risk == ImpactResidualRisk.high
            and self.prior_consultation_status != PriorConsultationStatus.closed
        ):
            raise ValueError(
                "high residual risk cannot be approved before prior consultation is closed"
            )
        return self


class AIImpactAssessmentRead(BaseModel):
    id: str | None = None
    tenant_id: str
    ai_system_id: str
    dpia_scope: ImpactAssessmentScope
    fria_scope: ImpactAssessmentScope
    deployer_context: ImpactDeployerContext
    scope_rationale: str | None = None
    lifecycle_status: ImpactAssessmentLifecycle
    residual_risk: ImpactResidualRisk
    assessment_owner: str | None = None
    independent_reviewer: str | None = None
    dpo_involved: bool = False
    stakeholder_views_status: StakeholderViewsStatus
    prior_consultation_status: PriorConsultationStatus
    prior_consultation_reference: str | None = None
    reviewed_at_utc: datetime | None = None
    approved_at_utc: datetime | None = None
    review_due_at_utc: datetime | None = None
    version: int = 0
    sections: list[ImpactAssessmentSectionRead]
    created_at_utc: datetime | None = None
    updated_at_utc: datetime | None = None
    updated_by: str | None = None


class AIImpactAssessmentSystemRow(BaseModel):
    ai_system_id: str
    ai_system_name: str
    business_unit: str
    risk_level: str
    ai_act_category: str
    registry_dpia_signal: bool
    assessment: AIImpactAssessmentRead
    readiness_score_pct: int = Field(ge=0, le=100)
    posture: str
    blockers: list[str]
    applicable_sections: int = Field(ge=0)
    reviewed_sections: int = Field(ge=0)
    review_overdue: bool = False


class AIImpactAssessmentSummary(BaseModel):
    total_systems: int = Field(ge=0)
    assessed_systems: int = Field(ge=0)
    scope_open_count: int = Field(ge=0)
    in_review_count: int = Field(ge=0)
    approved_count: int = Field(ge=0)
    high_residual_risk_count: int = Field(ge=0)
    consultation_open_count: int = Field(ge=0)
    overdue_review_count: int = Field(ge=0)


class AIImpactAssessmentPortfolioResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    readiness_score_pct: int = Field(ge=0, le=100)
    posture: str
    framework_version: str = "gdpr-35-36-eu-ai-act-27-v1"
    source_urls: dict[str, str] = {
        "gdpr": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
        "eu_ai_act": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
    }
    legal_disclaimer_de: str = (
        "Operative Assessment- und Evidenzunterstützung; keine Rechtsberatung, keine "
        "automatische Pflichtfeststellung und keine automatische Einsatzfreigabe."
    )
    summary: AIImpactAssessmentSummary
    systems: list[AIImpactAssessmentSystemRow]


def default_impact_sections() -> list[ImpactAssessmentSectionRead]:
    return [
        ImpactAssessmentSectionRead(
            section_key=key,
            status=ImpactSectionStatus.not_started,
            **definition,
        )
        for key, definition in SECTION_DEFINITIONS.items()
    ]
