# Wave 18 — Offering Definitions & GTM Alignment

> Status: Implemented (Wave 18, in-memory / config-based)
> Scope: Internal SKU model, German in-app copy, persona-based demo modes, error UX

---

## 1  Offering Definitions (SKU Catalog)

### SKU_AI_ACT_STARTER — "AI Act Readiness"

| Dimension | Detail |
|-----------|--------|
| Interner SKU-Code | `SKU_AI_ACT_STARTER` |
| Zielgruppe | KMU, Steuerberater-Kanzleien (Einstieg) |
| Tier | `starter` |
| Bundles | `ai_act_readiness` |
| Capabilities | `cap_ai_advisor_basic`, `cap_ai_evidence_basic` |
| Tagline (DE) | *Der schnelle Einstieg in die KI-Verordnung.* |

**Typische Einstiegsszenarien:**
1. Erste AI-Act-Risikoeinschätzung für ein KI-System durchführen
2. Nachweise und Dokumentation im Evidence-Bereich ablegen
3. Überblick: Welche meiner KI-Anwendungen sind betroffen?

**Value Props für Vertrieb:**
- Schneller Start ohne Implementierungsprojekt
- Strukturierte Risikoeinschätzung statt Excel-Listen
- Audit-Trail von Anfang an

---

### SKU_GOVERNANCE_PRO — "AI Governance & Evidence Suite"

| Dimension | Detail |
|-----------|--------|
| Interner SKU-Code | `SKU_GOVERNANCE_PRO` |
| Zielgruppe | Steuerberater-/WP-Kanzleien, wachsender Mittelstand |
| Tier | `pro` |
| Bundles | `ai_act_readiness`, `ai_governance_evidence` |
| Capabilities | Alle Starter-Caps + `cap_grc_records`, `cap_ai_system_inventory`, `cap_kanzlei_reports` |
| Tagline (DE) | *Umfassende KI-Governance für Kanzleien und Mittelstand.* |

**Typische Einstiegsszenarien:**
1. KI-System-Inventar aufbauen und AI-Act-Klassifizierung pflegen
2. NIS2-Pflichten und ISO 42001-Gaps pro System tracken
3. Mandanten-Board-Reports als Grundlage für Beirats-/Vorstandsberichte
4. Kanzlei-Compliance-Dossiers als Anlage zur Verfahrensdokumentation

**Value Props für Vertrieb:**
- Mandantenübergreifende Governance-Übersicht
- Board-Reports für professionelle Mandantenberatung
- GRC-Modul mit AI Act, NIS2 und ISO 42001 in einer Plattform

---

### SKU_ENTERPRISE_CONNECT — "Enterprise Connectors (SAP/DATEV)"

| Dimension | Detail |
|-----------|--------|
| Interner SKU-Code | `SKU_ENTERPRISE_CONNECT` |
| Zielgruppe | SAP-zentrierter Mittelstand, größere Kanzleien mit Systemintegration |
| Tier | `enterprise` |
| Bundles | Alle Pro-Bundles + `enterprise_integrations` |
| Capabilities | Alle Pro-Caps + `cap_enterprise_integrations` |
| Tagline (DE) | *Nahtlose Integration in SAP- und DATEV-Ökosysteme.* |

**Typische Einstiegsszenarien:**
1. DATEV-konforme Compliance-Dossiers automatisch erzeugen und exportieren
2. KI-System-Events aus SAP S/4HANA via BTP Event Mesh empfangen
3. Integration-Jobs überwachen, wiederholen und als Audit-Trail nutzen

**Value Props für Vertrieb:**
- Keine manuelle Datenübertragung zwischen Systemen
- GoBD-konforme Exporte für DATEV-Workflows
- SAP-native Event-Anbindung über BTP

---

## 2  In-App Copy (Deutsch)

### Prinzipien
- **Keine Rechtsberatung**: Formulierungen wie "unterstützt Sie bei …", nie "garantiert Konformität"
- **Anglizismen sparsam**: Fachbegriffe (Board Report, Evidence, Compliance) bleiben, aber werden im Kontext erklärt
- **Zielgruppengerecht**: Kanzlei-Sprache vs. Industrie-Sprache je nach Kontext

### Value Hints (pro Screen)

Value Hints erscheinen subtil auf den jeweiligen Screens und verweisen auf das aktive Paket.
Sie werden nur angezeigt, wenn die zugehörige Capability im Plan des Mandanten enthalten ist.

| Screen | Value Hint |
|--------|-----------|
| AI Advisor | "Teil Ihres Pakets: Der AI Act Advisor unterstützt Sie bei der strukturierten Einschätzung Ihrer KI-Systeme gemäß EU-KI-Verordnung." |
| Evidence Views | "Teil Ihres Pakets: AI-Evidence & Audit-Trail — dokumentieren Sie Nachweise, Prüfschritte und Entscheidungen nachvollziehbar." |
| GRC Records | "Teil Ihres Pakets 'AI Governance & Evidence': Risikobewertungen, NIS2-Pflichten und ISO 42001-Gaps zentral verwalten." |
| AI System Inventory | "Teil Ihres Pakets 'AI Governance & Evidence': Übersicht aller KI-Systeme mit AI-Act-/NIS2-/ISO-42001-Bezug und Lifecycle-Status." |
| Kanzlei Reports | "Teil Ihres Kanzlei-Pakets: Mandanten-Board-Reports fassen den KI-Compliance-Status eines Mandanten für Beirat oder Vorstand zusammen." |
| Kanzlei Dossier | "Teil Ihres Kanzlei-Pakets: Mandanten-Compliance-Dossiers eignen sich als Anlage zur Verfahrensdokumentation oder als strukturierter Compliance-Nachweis im DATEV-Umfeld." |
| Enterprise Integrations | "Teil Ihres Enterprise-Pakets: Nahtlose Integration in SAP- und DATEV-Ökosysteme für automatisierte Compliance-Synchronisation." |

### Feature-not-enabled Fehlermeldung (403)

Wenn eine Capability im aktuellen Paket nicht enthalten ist:

```json
{
  "error": "feature_not_enabled",
  "message_de": "Diese Funktion (GRC-Einträge) ist in Ihrem aktuellen Paket (Starter – AI Act Readiness) nicht enthalten.",
  "message_en": "This feature (GRC Records) is not included in your current plan.",
  "upgrade_hint_de": "Diese Funktion ist typischerweise im Paket 'AI Governance & Evidence (Professional)' verfügbar.",
  "contact_cta_de": "Für ein Upgrade oder weitere Informationen: kontakt@compliancehub.de",
  "contact_url": "mailto:kontakt@compliancehub.de",
  "disclaimer_de": "ComplianceHub unterstützt Sie bei der strukturierten Umsetzung von KI-Governance-Anforderungen. Die Nutzung der Plattform ersetzt keine individuelle Rechtsberatung.",
  "capability": "cap_grc_records",
  "current_plan": "Starter – AI Act Readiness"
}
```

---

## 3  Persona-basierte Demo-Modi

### Verfügbare Profile

| Profil | Tier | Zielgruppe | Seeded Systems |
|--------|------|------------|----------------|
| `industrie_mittelstand_demo` | Professional | CISO / AI-Owner Mittelstand | 3 (Predictive Maintenance, Qualitätskontrolle, Bewerber-Vorauswahl) |
| `kanzlei_demo` | Professional | Kanzlei-Partner / Tax-Compliance | 3 (Mandanten-Chatbot, Belegklassifikation, Steuerrisiko-Scoring) |
| `sap_enterprise_demo` | Enterprise | SAP/BTP-zentrierter Mittelstand | 3 (SAP Kredit-Scoring, Fraud Detection, Demand Forecasting) |
| `sme_demo` | Starter | KMU-Einstieg | 2 (Support-Chatbot, Spam-Filter) |

### Seeding-Umfang
Pro Demo-Profil werden angelegt:
- AI-Systeme mit realistischen Namen, Beschreibungen und Klassifizierungen
- AI-Risk-Assessments pro System
- NIS2-Obligations (wo relevant)
- ISO 42001-Gap-Records (wo relevant)

### API

```
POST /api/internal/product/demo-seed/{tenant_id}?profile=kanzlei_demo&seed_data=true
```

Response enthält Plan-Details und `seeded_data`-Summary.

---

## 4  Demo-Scripts (20–30 min)

### Script 1: "Industrie-Mittelstand CISO / AI-Owner"

**Ziel**: Zeigen, wie ComplianceHub dem CISO/AI-Owner im Mittelstand hilft,
KI-Systeme strukturiert zu erfassen, zu bewerten und nachweisbar zu dokumentieren.

**Setup**: `industrie_mittelstand_demo` Profil seeden.

| Min | Screen | Was zeigen | Talking Point |
|-----|--------|-----------|---------------|
| 0–3 | Login / Workspace | Dashboard mit Paket-Info | "Ihr Paket: AI Governance & Evidence Suite" |
| 3–8 | AI System Inventory | 3 Systeme mit Klassifizierung, Lifecycle | "Alle KI-Systeme auf einen Blick — AI Act, NIS2, ISO 42001" |
| 8–13 | GRC → AI Risk Assessments | Risikobewertung Predictive Maintenance | "Hochrisiko-System? ComplianceHub unterstützt bei der Einschätzung" |
| 13–17 | GRC → NIS2 | NIS2-Pflichten für Produktion | "NIS2-relevante Systeme automatisch verknüpft" |
| 17–20 | GRC → ISO 42001 Gaps | Gap-Analyse zeigen | "ISO 42001-Gaps tracken und Remediation planen" |
| 20–23 | AI Advisor | Risikoeinschätzung für Bewerber-Vorauswahl | "AI Act Advisor: strukturierte Ersteinschätzung in Minuten" |
| 23–27 | Evidence | Audit-Trail durchgehen | "Jede Aktion dokumentiert — für interne Audits und externe Prüfer" |
| 27–30 | Board Report | Report generieren | "Vorstandsbericht auf Knopfdruck — PDF-ready" |

**Nicht zeigen**: Admin-Konfiguration, Integration-Endpoints, interne API-Docs.

---

### Script 2: "Kanzlei-Partner / Tax-Compliance"

**Ziel**: Zeigen, wie eine Steuerberater-Kanzlei mit ComplianceHub ihren
Mandanten KI-Compliance-Beratung als Dienstleistung anbieten kann.

**Setup**: `kanzlei_demo` Profil seeden.

| Min | Screen | Was zeigen | Talking Point |
|-----|--------|-----------|---------------|
| 0–3 | Login / Workspace | Kanzlei-Branding, Paket-Info | "Ihr Kanzlei-Paket: AI Governance & Evidence" |
| 3–7 | AI System Inventory | Mandanten-KI-Systeme | "KI-Systeme Ihrer Mandanten zentral erfassen" |
| 7–12 | AI Advisor | Chatbot-Risikoeinschätzung | "Mandant fragt: Brauche ich für meinen Chatbot eine Risikobewertung?" |
| 12–16 | GRC → Risk Assessment | Steuerrisiko-Scoring bewerten | "Hochrisiko-Kandidat: Was bedeutet das für den Mandanten?" |
| 16–20 | GRC → ISO 42001 | Gap-Analyse für Kanzlei-Mandant | "ISO 42001-Readiness: Wo steht Ihr Mandant?" |
| 20–24 | Board Report | Mandanten-Board-Report erstellen | "Professioneller Compliance-Report für Beirat oder Geschäftsführung" |
| 24–28 | Kanzlei-Dossier | Dossier-Export (JSON/CSV) | "Mandanten-Compliance-Dossier als Anlage zur Verfahrensdokumentation — DATEV-ready" |
| 28–30 | Evidence | Audit-Trail des Mandanten | "Lückenlose Nachverfolgung: Wer hat was wann dokumentiert?" |

**Nicht zeigen**: SAP-Integration, Enterprise Connectors, Admin-APIs.

---

## 5  Telemetrie (GTM-Iteration)

Minimale Events für Produktentwicklung (kein PII):

| Event Type | Felder | Zweck |
|-----------|--------|-------|
| `demo_mode_activated` | `tenant_id`, `profile`, `tier` | Welche Demo-Profile werden genutzt? |
| `demo_data_seeded` | `tenant_id`, `profile`, `ai_systems`, `risks`, … | Umfang der Seeding-Daten |
| `gtm_screen_view` | `tenant_id`, `screen`, `demo_profile`, `plan_tier` | Welche Screens werden in Demos besucht? |
| `capability_usage` | `tenant_id`, `capability`, `action`, `tier`, `bundle` | Welche Features werden aktiv genutzt? |

API: `POST /api/internal/product/telemetry/screen-view`

---

## 6  Design-Entscheidungen

1. **SKUs sind intern**: Noch keine öffentliche Preisseite. SKU-Definitionen leben in `app/product/offerings.py` und können 1:1 in Vertriebsmaterialien übernommen werden.

2. **Copy zentral verwaltet**: Alle deutschen Texte in `app/product/copy_de.py` — einzelne Quelle der Wahrheit für Produkttexte.

3. **Keine Compliance-Versprechen**: Sämtliche Texte formulieren "unterstützt bei", nicht "garantiert". Disclaimer wird in 403-Fehlern mitgeliefert.

4. **Demo-Seeding ist idempotent**: Mehrfaches Seeden überschreibt vorhandene Systeme (upsert), erzeugt keine Duplikate.

5. **Value Hints sind capability-gefiltert**: Der `value-hints` Endpoint liefert nur Hints für Capabilities, die im Plan des Mandanten aktiv sind — keine Upsell-Banner.

6. **Additive Architektur**: Neue SKUs, Bundles oder Demo-Profile können ohne Schema-Änderungen hinzugefügt werden.

---

## 7  Dateien

| Datei | Zweck |
|-------|-------|
| `app/product/offerings.py` | SKU-Katalog mit DE/EN-Copy, Tier/Bundle-Mapping |
| `app/product/copy_de.py` | Zentrale deutsche Texte: Labels, Beschreibungen, Value Hints, Error-Copy |
| `app/product/demo_plans.py` | Demo-Profile mit realistischen Sample-Daten (4 Personas) |
| `app/product/plan_store.py` | Enhanced 403 mit Upgrade-Hint, Contact CTA, Disclaimer |
| `app/product/models.py` | Plan-Display nutzt zentrale deutsche Labels |
| `app/demo_models.py` | `TenantWorkspaceMetaResponse` + SKU-Felder |
| `app/main.py` | Neue Endpoints: offerings, value-hints, screen-view telemetry |
| `tests/test_wave18_offerings_gtm.py` | 42 neue Tests |
| `tests/test_product_packaging.py` | Aktualisierte Wave 17-Tests |
