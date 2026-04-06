"""German-language copy for in-app messaging, value hints, and error UX.

All text avoids Anglizismen where DACH customers would reject them,
but keeps established Fachbegriffe (Board Report, Evidence, Compliance).

IMPORTANT: Keine Rechtsberatung, keine Konformitätsgarantien.
Formulierungen wie "unterstützt Sie bei …", nicht "garantiert …".
"""

from __future__ import annotations

from app.product.models import Capability

# ---------------------------------------------------------------------------
# Plan / Paketnamen und Kurzbeschreibungen
# ---------------------------------------------------------------------------

TIER_LABELS_DE: dict[str, str] = {
    "starter": "Starter",
    "pro": "Professional",
    "enterprise": "Enterprise",
}

TIER_DESCRIPTIONS_DE: dict[str, str] = {
    "starter": (
        "Ihr Einstieg in die EU-KI-Verordnung: AI Act Advisor und "
        "Evidence-Dokumentation für erste Risikoeinschätzungen."
    ),
    "pro": (
        "Umfassende KI-Governance für Kanzleien und Mittelstand: "
        "GRC-Management, AI-System-Inventar, Mandanten-Board-Reports "
        "und Compliance-Dossiers."
    ),
    "enterprise": (
        "Vollständige Plattform mit Enterprise-Integrationen: "
        "SAP BTP, DATEV-Exporte und automatisierte Synchronisation "
        "in bestehende IT-Landschaften."
    ),
}

BUNDLE_LABELS_DE: dict[str, str] = {
    "ai_act_readiness": "AI Act Readiness",
    "ai_governance_evidence": "AI Governance & Evidence",
    "enterprise_integrations": "Enterprise Connectors (SAP/DATEV)",
}

BUNDLE_DESCRIPTIONS_DE: dict[str, str] = {
    "ai_act_readiness": (
        "Strukturierter Einstieg in die EU-KI-Verordnung mit "
        "AI Act Advisor und Evidence-Dokumentation."
    ),
    "ai_governance_evidence": (
        "GRC-Einträge für Risikobewertungen, NIS2-Pflichten und "
        "ISO 42001-Gaps. AI-System-Inventar mit Lifecycle-Tracking "
        "sowie Mandanten-Board-Reports und Kanzlei-Dossiers."
    ),
    "enterprise_integrations": (
        "DATEV-konforme Mandanten-Exporte und SAP BTP Event-Mesh-"
        "Anbindung für die Einbettung in bestehende Systeme."
    ),
}

# ---------------------------------------------------------------------------
# Value hints (pro Screen/Feature)
# ---------------------------------------------------------------------------

VALUE_HINTS_DE: dict[str, str] = {
    "ai_advisor": (
        "Teil Ihres Pakets: Der AI Act Advisor unterstützt Sie bei der "
        "strukturierten Einschätzung Ihrer KI-Systeme gemäß EU-KI-Verordnung. "
        "Dieses Modul ist typischerweise Bestandteil von „AI Act Readiness“ "
        "(Starter-Tier)."
    ),
    "evidence_views": (
        "Teil Ihres Pakets: AI-Evidence & Audit-Trail — dokumentieren Sie "
        "Nachweise, Prüfschritte und Entscheidungen nachvollziehbar. "
        "Typischerweise Teil von „AI Act Readiness“ (Starter-Tier) oder "
        "erweitert in „AI Governance & Evidence“ (Professional-Tier)."
    ),
    "grc_records": (
        "Teil Ihres Pakets „AI Governance & Evidence“: Risikobewertungen, "
        "NIS2-Pflichten und ISO 42001-Gaps zentral verwalten. "
        "Dieses Modul ist typischerweise Teil des Professional-Tiers "
        "(Paket „AI Governance & Evidence“), nicht des reinen Starter-Pakets."
    ),
    "ai_system_inventory": (
        "Teil Ihres Pakets „AI Governance & Evidence“: Übersicht aller "
        "KI-Systeme mit AI-Act-/NIS2-/ISO-42001-Bezug und Lifecycle-Status. "
        "Typischerweise Professional-Tier; für Kanzleien und Mittelstand der "
        "Kern vor optionalen Enterprise-Connectors."
    ),
    "kanzlei_reports": (
        "Teil Ihres Kanzlei-Pakets: Mandanten-Board-Reports fassen den "
        "KI-Compliance-Status eines Mandanten für Beirat oder Vorstand zusammen. "
        "Typischerweise Paket „AI Governance & Evidence“ (Professional-Tier)."
    ),
    "kanzlei_dossier": (
        "Teil Ihres Kanzlei-Pakets: Mandanten-Compliance-Dossiers eignen sich "
        "als Anlage zur Verfahrensdokumentation oder als strukturierter "
        "Compliance-Nachweis im DATEV-Umfeld. "
        "Ebenfalls typischerweise „AI Governance & Evidence“ (Professional-Tier); "
        "DATEV-nahe Exporte stärker mit Enterprise Connectors kombinierbar."
    ),
    "enterprise_integrations": (
        "Teil Ihres Enterprise-Pakets: Nahtlose Integration in SAP- und "
        "DATEV-Ökosysteme für automatisierte Compliance-Synchronisation. "
        "Enterprise Connectors sind als Zusatzpaket im Enterprise-Tier für "
        "SAP-/DATEV-Integrationen vorgesehen — sinnvoll auf Basis von "
        "Governance & Evidence."
    ),
    "deployment_check": (
        "Deployment-Prüfung: Automatische Prüfung der Compliance-Readiness "
        "eines KI-Systems vor dem Go-live. "
        "Häufig im Umfeld von Governance & Evidence (Professional-Tier) im Einsatz."
    ),
}

# ---------------------------------------------------------------------------
# Feature-not-enabled error copy
# ---------------------------------------------------------------------------

FEATURE_NOT_ENABLED_TEMPLATE_DE = (
    "Diese Funktion ({feature_label}) ist in Ihrem aktuellen Paket ({plan_label}) nicht enthalten."
)

FEATURE_NOT_ENABLED_HINT_DE = (
    "Diese Funktion ist typischerweise im Paket '{upgrade_hint}' verfügbar. "
    "Kontaktieren Sie Ihren ComplianceHub-Ansprechpartner für weitere "
    "Informationen — oder schreiben Sie uns: kontakt@compliancehub.de"
)

FEATURE_NOT_ENABLED_DISCLAIMER_DE = (
    "ComplianceHub unterstützt Sie bei der strukturierten Umsetzung von "
    "KI-Governance-Anforderungen. Die Nutzung der Plattform ersetzt keine "
    "individuelle Rechtsberatung."
)

CAPABILITY_UPGRADE_HINTS_DE: dict[Capability, str] = {
    Capability.ai_advisor_basic: "AI Act Readiness (Starter-Tier)",
    Capability.ai_evidence_basic: "AI Act Readiness (Starter-Tier)",
    Capability.grc_records: "AI Governance & Evidence (Professional-Tier)",
    Capability.ai_system_inventory: "AI Governance & Evidence (Professional-Tier)",
    Capability.kanzlei_reports: "AI Governance & Evidence (Professional-Tier)",
    Capability.enterprise_integrations: (
        "Enterprise Connectors (Zusatzpaket, Enterprise-Tier; SAP-/DATEV-Integrationen)"
    ),
}

# ---------------------------------------------------------------------------
# Tooltip texts for disabled UI elements
# ---------------------------------------------------------------------------

DISABLED_TOOLTIP_DE = "In Ihrem aktuellen Paket nicht enthalten."

DISABLED_TOOLTIP_WITH_HINT_DE = (
    "In Ihrem aktuellen Paket nicht enthalten. Verfügbar ab Paket '{upgrade_hint}'."
)

# ---------------------------------------------------------------------------
# Contact CTA
# ---------------------------------------------------------------------------

CONTACT_CTA_DE = "Für ein Upgrade oder weitere Informationen: kontakt@compliancehub.de"

CONTACT_URL = "mailto:kontakt@compliancehub.de"
