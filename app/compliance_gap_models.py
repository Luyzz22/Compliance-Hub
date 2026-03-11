from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComplianceStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    not_applicable = "not_applicable"


class ComplianceRequirement(BaseModel):
    id: str
    article: str
    name: str
    description: str
    applies_to: list[str]  # ["high_risk"]
    weight: float = 1.0


class ComplianceStatusEntry(BaseModel):
    ai_system_id: str
    requirement_id: str
    status: ComplianceStatus = ComplianceStatus.not_started
    evidence_notes: str | None = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = "system"


class ComplianceStatusUpdate(BaseModel):
    status: ComplianceStatus
    evidence_notes: str | None = None


class SystemReadiness(BaseModel):
    ai_system_id: str
    ai_system_name: str
    risk_level: str
    readiness_score: float  # 0.0 - 1.0
    total_requirements: int
    completed: int
    in_progress: int
    not_started: int


class ComplianceDashboard(BaseModel):
    tenant_id: str
    overall_readiness: float
    systems: list[SystemReadiness]
    deadline: str = "2026-08-02"
    days_remaining: int = 0
    urgent_gaps: list[dict[str, str]] = []


# --- Static requirement definitions ---

REQUIREMENTS: list[ComplianceRequirement] = [
    ComplianceRequirement(
        id="art_9",
        article="Art. 9",
        name="Risikomanagement-System",
        description="Einrichtung, Durchführung, Dokumentation und Aufrechterhaltung eines Risikomanagementsystems gemäß Art. 9 EU AI Act.",
        applies_to=["high_risk"],
        weight=2.0,
    ),
    ComplianceRequirement(
        id="art_10",
        article="Art. 10",
        name="Datengovernance",
        description="Anforderungen an Trainings-, Validierungs- und Testdatensätze gemäß Art. 10 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_11",
        article="Art. 11",
        name="Technische Dokumentation",
        description="Erstellung der technischen Dokumentation gemäß Art. 11 und Anhang IV EU AI Act.",
        applies_to=["high_risk"],
        weight=2.0,
    ),
    ComplianceRequirement(
        id="art_12",
        article="Art. 12",
        name="Aufzeichnungspflicht",
        description="Automatische Aufzeichnung von Ereignissen (Logging) während des Betriebs gemäß Art. 12 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_13",
        article="Art. 13",
        name="Transparenz / Gebrauchsanweisung",
        description="Bereitstellung hinreichend transparenter Informationen für Betreiber gemäß Art. 13 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_14",
        article="Art. 14",
        name="Menschliche Aufsicht",
        description="Konzeption für wirksame menschliche Aufsicht während der Nutzung gemäß Art. 14 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_15",
        article="Art. 15",
        name="Genauigkeit, Robustheit, Cybersicherheit",
        description="Sicherstellung von Genauigkeit, Robustheit und Cybersicherheit gemäß Art. 15 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_17",
        article="Art. 17",
        name="Qualitätsmanagementsystem",
        description="Einrichtung eines Qualitätsmanagementsystems gemäß Art. 17 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_43",
        article="Art. 43",
        name="Konformitätsbewertung",
        description="Durchführung einer Konformitätsbewertung vor dem Inverkehrbringen gemäß Art. 43 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_47",
        article="Art. 47",
        name="CE-Kennzeichnung",
        description="Anbringung der CE-Kennzeichnung gemäß Art. 47 EU AI Act.",
        applies_to=["high_risk"],
    ),
    ComplianceRequirement(
        id="art_49",
        article="Art. 49",
        name="EU-Datenbankregistrierung",
        description="Registrierung des Hochrisiko-KI-Systems in der EU-Datenbank gemäß Art. 49 EU AI Act.",
        applies_to=["high_risk"],
    ),
]

REQUIREMENTS_BY_ID: dict[str, ComplianceRequirement] = {r.id: r for r in REQUIREMENTS}
