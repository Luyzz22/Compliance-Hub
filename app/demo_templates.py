"""Statische Demo-Mandanten-Templates für Pilot- und Demo-Umgebungen (nicht produktiv)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DemoTenantTemplate(BaseModel):
    """Leichtgewichtige Template-Metadaten für UI und Doku."""

    key: str = Field(..., description="Stabiler Schlüssel, z. B. kritis_energy")
    name: str
    description: str
    industry: str
    segment: str
    country: str = "DE"
    nis2_scope: bool = Field(
        default=True,
        description="Template enthält NIS2-/KRITIS-KPI-Szenario.",
    )
    ai_act_high_risk_focus: bool = Field(
        default=True,
        description="Mindestens ein Hochrisiko-/Anhang-III-Fokus im Register.",
    )


DEMO_TENANT_TEMPLATES: tuple[DemoTenantTemplate, ...] = (
    DemoTenantTemplate(
        key="kritis_energy",
        name="KRITIS-Energieversorger",
        description=(
            "Netzlast-Prognose-KI, Ausfallvorhersage und Supplier-Risk-Fokus – "
            "bewusst Lücken bei OT/IT und Lieferanten-KPIs für Board-Alerts."
        ),
        industry="Energie / Versorgung",
        segment="KRITIS",
        country="DE",
        nis2_scope=True,
        ai_act_high_risk_focus=True,
    ),
    DemoTenantTemplate(
        key="industrial_sme",
        name="Industrie-Mittelstand",
        description=(
            "Qualitätskontrolle (Vision), vorausschauende Instandhaltung und "
            "interne Wissens-KI – Mix aus High-Risk-Produktion und begleitenden Systemen."
        ),
        industry="Manufacturing",
        segment="Mittelstand",
        country="DE",
        nis2_scope=True,
        ai_act_high_risk_focus=True,
    ),
    DemoTenantTemplate(
        key="tax_advisor",
        name="WP- / Steuerkanzlei",
        description=(
            "AI-gestützte Dokumentenprüfung, Umsatzsteuer-Assistenz und Mandanten-Chatbot – "
            "Fokus DSGVO/GoBD und EU-AI-Act-Transparenz."
        ),
        industry="Professional Services",
        segment="Steuerberatung",
        country="DE",
        nis2_scope=False,
        ai_act_high_risk_focus=True,
    ),
)


def list_demo_tenant_templates() -> list[DemoTenantTemplate]:
    return list(DEMO_TENANT_TEMPLATES)


def get_demo_template(key: str) -> DemoTenantTemplate | None:
    k = key.strip()
    for t in DEMO_TENANT_TEMPLATES:
        if t.key == k:
            return t
    return None
