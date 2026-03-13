from __future__ import annotations

from pydantic import BaseModel

from app.enum_compat import StrEnum


class GapRequirement(BaseModel):
    id: str
    article: str
    name: str
    description: str
    applies_to: list[str]
    weight: float = 1.0

class ComplianceRequirement(BaseModel):
    id: str
    article: str
    name: str
    description: str
    weight: float = 1.0

class ComplianceStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"

class ComplianceStatusEntry(BaseModel):
    tenant_id: str
    ai_system_id: str
    requirement_id: str
    status: ComplianceStatus
    updated_by: str | None = None


class ComplianceStatusUpdate(BaseModel):
    status: ComplianceStatus

class SystemReadiness(BaseModel):
    ai_system_id: str
    ai_system_name: str
    risk_level: str
    readiness_score: float
    total_requirements: int
    completed: int
    in_progress: int
    not_started: int

class ComplianceDashboard(BaseModel):
    tenant_id: str
    overall_readiness: float
    systems: list[SystemReadiness]
    days_remaining: int
    urgent_gaps: list[dict[str, str]]

GAP_REQUIREMENTS: list[GapRequirement] = [
    GapRequirement(
        id="art9_risk_management",
        article="Art. 9",
        name="Risikomanagementsystem",
        description=(
            "Implementierung und Aufrechterhaltung eines "
            "Risikomanagementsystems gemäß Art. 9 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art10_data_governance",
        article="Art. 10",
        name="Datengovernance",
        description=(
            "Anforderungen an Trainings-, Validierungs- und "
            "Testdatensätze gemäß Art. 10 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art11_technical_documentation",
        article="Art. 11",
        name="Technische Dokumentation",
        description=(
            "Erstellung der technischen Dokumentation gemäß Art. 11 "
            "und Anhang IV EU AI Act."
        ),
        applies_to=["high_risk"],
        weight=2.0,
    ),
    GapRequirement(
        id="art12_logging",
        article="Art. 12",
        name="Aufzeichnungspflicht",
        description=(
            "Automatische Aufzeichnung von Ereignissen (Logging) "
            "während des Betriebs gemäß Art. 12 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art13_transparency",
        article="Art. 13",
        name="Transparenz / Gebrauchsanweisung",
        description=(
            "Bereitstellung hinreichend transparenter Informationen "
            "für Betreiber gemäß Art. 13 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art14_human_oversight",
        article="Art. 14",
        name="Menschliche Aufsicht",
        description=(
            "Konzeption für wirksame menschliche Aufsicht während der "
            "Nutzung gemäß Art. 14 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art15_robustness_cybersecurity",
        article="Art. 15",
        name="Genauigkeit, Robustheit, Cybersicherheit",
        description=(
            "Sicherstellung von Genauigkeit, Robustheit und "
            "Cybersicherheit gemäß Art. 15 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art43_conformity_assessment",
        article="Art. 43",
        name="Konformitätsbewertung",
        description=(
            "Durchführung einer Konformitätsbewertung vor dem "
            "Inverkehrbringen gemäß Art. 43 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
    GapRequirement(
        id="art49_eu_database",
        article="Art. 49",
        name="EU-Datenbankregistrierung",
        description=(
            "Registrierung des Hochrisiko-KI-Systems in der "
            "EU-Datenbank gemäß Art. 49 EU AI Act."
        ),
        applies_to=["high_risk"],
    ),
]

REQUIREMENTS: list[ComplianceRequirement] = [
    ComplianceRequirement(
        id=req.id,
        article=req.article,
        name=req.name,
        description=req.description,
        weight=req.weight,
    )
    for req in GAP_REQUIREMENTS
]

REQUIREMENTS_BY_ID: dict[str, ComplianceRequirement] = {
    req.id: req for req in REQUIREMENTS
}

