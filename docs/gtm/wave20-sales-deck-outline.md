# Wave 20 – Sales-Deck-Outline (Messaging-Rohbau)

**Zweck:** Wiederverwendbare Struktur und Kurztexte für Website, Sales-Decks und Kampagnen.  
**Sprache der Beispieltexte:** Deutsch.  
**Preise:** bewusst nicht enthalten (nur Paket-Fit).  
**Regulatorik:** vorsichtige Formulierungen („Unterstützung bei Readiness“, „Nachweise dokumentieren“) – finale Zusagen nur nach Legal/Compliance-Review.

**Bezug Wave 21 (Statement Library):** Kanonische Claims, Proof Points und Disclaimers aus [`compliance-statement-library-de.md`](./compliance-statement-library-de.md) und [`statements/statements.v1.json`](./statements/statements.v1.json) verwenden; Kanal `sales_deck`, Familien siehe [`statements/sku_channel_family_mapping.md`](./statements/sku_channel_family_mapping.md). Bullets im Deck idealerweise mit `statement_id` in Sprecher-Notizen oder CMS referenzieren.

**Bezug Wave 19:** Baut auf dem **Pricing & Sales-Playbook (Wave 19)** auf – SKU-Definition und Repo-Anker: [`wave19-pricing-sales-playbook-stub.md`](./wave19-pricing-sales-playbook-stub.md). Dieselbe **SKU-/Paketbezeichnung** und Tier-Logik wie dort (ohne hier Beträge zu nennen):

| SKU (Paket)            | Kurzbezeichnung im Deck |
| ---------------------- | ----------------------- |
| AI Act Readiness       | **Paket: AI Act Readiness** |
| Governance & Evidence  | **Paket: Governance & Evidence** |
| Enterprise Connectors  | **Paket: Enterprise Connectors** |

**Module (konsistent zur Produktlandschaft):** Advisor · Evidence · GRC · AiSystem · Integrationen · Lifecycle/Readiness · Board Reports · Kanzlei-Dossiers (wo relevant erwähnen, nicht alle auf einer Folie überfrachten).

**Leitidee (ein Satz):** *ComplianceHub: einmal mappen, viele Anforderungen abdecken – KI-Register, Nachweise und Reports aus einer mandantenfähigen Quelle.*

---

## 1. Generische Deck-Struktur (12–15 Folien)

Jede Folie: **Titel** + **Kernaussagen** (Bullets) + **Platzhalter** `[ … ]` für Kundenname, Branche, Datum.

### Folie 1 – Titel & Credibility

- **Titel:** ComplianceHub – AI-Governance & Compliance für den DACH-Raum
- **Untertitel:** Mandantenfähige Plattform für Register, Nachweise und Board-taugliche Übersichten
- **Bullets:**
  - Fokus: Unternehmen, Kanzleien und Konzerne mit SAP-/Enterprise-Landschaft
  - Technische Basis: strukturierte Evidenz, Audit-Trails, Integrationen (ohne Cloud-Anbieter-Name zu erzwingen)
- **Platzhalter:** `[Kunde] · [Datum] · [Vertraulichkeit: nur zur internen Verwendung]`

### Folie 2 – Agenda

- Kurzüberblick: Herausforderung → Risiko heutiger Ad-hoc-Lösungen → ComplianceHub → Pakete → Beispiele → Rollen → Nächste Schritte
- **Platzhalter:** `[Dauer der Session · z. B. 45 Min.]`

### Folie 3 – Problem-Landschaft (Regulatorik, sachlich)

- **Titel:** Was sich für Organisationen in der EU/DACH verschärft
- **Bullets:**
  - **EU AI Act:** zunehmende Pflichten je nach Risikoklasse und Einsatzszenario; Dokumentation und Nachvollziehbarkeit gewinnen an Gewicht
  - **NIS2 / nationales KRITIS-Rahmenwerk:** Erwartung an Incident-Prozesse, Lieferketten und Nachweise – auch für mittelständische kritische Anbieter relevant
  - **ISO/IEC 42001 & ISO 27001/27701:** KI-Managementsystem und ISMS greifen ineinander; Audits erwarten konsistente Spuren
  - **GoBD / steuerliche Dokumentation:** wo KI Systeme buchungs- oder belegrelevante Prozesse berührt, steigen Anforderungen an Nachvollziehbarkeit und Aufbewahrung
- **Hinweis für Sprecher:** „Wir unterstützen bei der Vorbereitung und Dokumentation – keine Garantie für Konformität.“

### Folie 4 – Branchen-Brille (optional kurz)

- **Titel:** Gleiche Regeln, unterschiedliche Schwerpunkte
- **Bullets:**
  - **Industrie / Mittelstand:** Lieferanten, Produktion, SAP-lastige Prozesse, AI Act Readiness unter Zeitdruck
  - **Kanzlei:** Mandantenfähige Beratung, GoBD/DATEV-Ökosystem, wiederholbare Dossiers
  - **Enterprise:** Konzernweite Transparenz, viele KI-Nutzer, Anbindung an SAP BTP / Event-getriebene Landschaften
- **Platzhalter:** `[Welche Persona heute im Fokus?]`

### Folie 5 – Risiken von Excel, E-Mail und Einzeltools

- **Titel:** Ad-hoc heißt: Lücken beim Audit
- **Bullets:**
  - Verstreute Listen: kein durchgängiger **Audit-Trail** über Änderungen und Freigaben
  - Manuelle Abstimmung zwischen Legal, IT und Fachbereich: Fehler, Verzögerung, Versionskonflikte
  - Isolierte „KI-Checklisten“ ohne Anbindung an Register, Incidents und Board-Reporting
  - Folge: teure Firefighting-Phasen vor Audits oder Vorstandsterminen

### Folie 6 – ComplianceHub in einem Satz

- **Titel:** Eine Plattform für Register, Governance und Nachweise
- **Zentraler Satz:** **Map once, comply many** – Anforderungen aus AI Act, ISO- und Security-Governance sowie Nachweispflichten an einer Stelle abbilden und für Reports und Mandanten-Akten nutzbar machen.
- **Bullets:**
  - Mandantenfähig (Multi-Tenant) – geeignet für Beratungshäuser und Konzerne mit Tochtergesellschaften
  - Deutschsprachige Oberfläche und Outcomes für DACH-Entscheider

### Folie 7 – Modul-Übersicht

- **Titel:** Was ComplianceHub modular abdeckt
- **Bullets:**
  - **Advisor:** Portfolio- und Mandantensicht, Priorisierung, Snapshots für Beratung und interne Steuerung
  - **Evidence:** strukturierte Nachweise, Verknüpfung zu Controls und Systemen
  - **GRC:** Risiko- und Compliance-Objekte im Kontext von KI und IT
  - **AiSystem:** KI-Register, Klassifizierung, Lifecycle – inkl. High-Risk-Themen nachvollziehbar dokumentieren
  - **Integrationen:** u. a. SAP-Umfeld, DMS-/Exportpfade für Kanzleien und Board-Reports
  - **Lifecycle / Readiness:** geführte Readiness, Scores, Meilensteine – ohne „fertige Compliance“ zu versprechen

### Folie 8 – Drei Pakete (SKUs) – Fit, nicht Preis

- **Titel:** Pakete – vom Einstieg bis zur Enterprise-Anbindung
- **Paket: AI Act Readiness**
  - Für Teams, die **schnell Klarheit** zu KI-Systemen, Risikoklassen und Dokumentationslücken brauchen
  - Fokus: Register, Readiness-Pfade, Board-taugliche KPIs
- **Paket: Governance & Evidence**
  - Für Organisationen mit **Audit- und ISO-Bezug**: Evidenzketten, wiederholbare Reviews, erweiterte GRC-Nutzung
- **Paket: Enterprise Connectors**
  - Für **SAP-/Konzernsetups**: tiefere Integration, Event-/Betriebssignale einbeziehen, skalierbare Governance über viele Einheiten
- **Platzhalter:** `[Empfohlenes Paket für diesen Account: … + Begründung in einem Satz]`

### Folie 9 – Beispiel-Workflow A

- **Titel:** Beispiel: AI Act Readiness in 30 Tagen (Pilotlogik)
- **Bullets:**
  - Woche 1–2: Inventar KI-Use-Cases und Systeme im Register; erste Risikoeinstufung; Lückenliste
  - Woche 3: Verknüpfung mit Evidence und Verantwortlichkeiten (RACI light)
  - Woche 4: Readiness-Übersicht und Kurzreport für Management – **als Entscheidungsgrundlage**, nicht als Zertifikat
- **Platzhalter:** `[Anzahl Systeme · Zielgruppe im Projekt]`

### Folie 10 – Beispiel-Workflow B

- **Titel:** Beispiel: Kanzlei – Mandanten-Dossier „Mandant X“
- **Bullets:**
  - Mandanten-Stammdaten und Scope festlegen
  - Board-Report / Governance-Export als **Prüfungs- oder Beratungsdokument** strukturieren
  - DATEV-/DMS-taugliche Weiterverarbeitung vorbereiten (technischer Export-Pfad – Details im Integrationsgespräch)
- **Platzhalter:** `[Mandantenname · Beratungsprodukt der Kanzlei]`

### Folie 11 – Rollen & Nutzen

- **Titel:** Wer arbeitet womit?
- **Bullets:**
  - **CISO / Informationssicherheit:** übergreifende Risiko- und Incident-Themen, NIS2-Bezug in der Darstellung
  - **AI Owner / Produkt:** Systempflege im Register, Nachweise zu Modellen und Änderungen
  - **Kanzlei-Partner / Berater:** Mandanten-Portfolio, Dossiers, Wiederholbarkeit
  - **Mandanten / Fachbereiche:** klare Aufgaben und Nachweispunkte – weniger Rückfragen in der Endphase

### Folie 12 – Datenhaltung & Vertrauen (kurz, ohne Marketing)

- **Titel:** Was Sie dokumentieren – und was Sie selbst entscheiden
- **Bullets:**
  - Mandantenfähige Datenhaltung; **keine** automatische Rechtsberatung
  - Audit-Logs **immutable** (Produktprinzip) – geeignet für Prüfpfade
  - DSGVO- und Aufbewahrungsthemen mit Ihrem DSB / WP abzustimmen

### Folie 13 – Nächste Schritte

- **Titel:** Von hier zum Pilot
- **Bullets:**
  - **Pilot:** klarer Scope (z. B. eine Division, 5–15 Systeme, 4–6 Wochen)
  - **Onboarding:** Rollen, Mandantenstruktur, Schulung der Kernuser
  - **Integration:** SAP BTP / DMS / DATEV-Pfad je nach Paket – technischer Workshop
- **Platzhalter:** `[Nächstes Meeting · verantwortliche Personen]`

### Folie 14 – Q&A / Anhang-Hinweis (optional)

- **Titel:** Fragen & Tiefgang
- **Bullets:**
  - Vertiefung: Norm-Mapping, konkrete Integrations-Screenshots, Demo-Mandant
  - **Anhang-Folien** (optional): Architektur-Skizze, Beispiel-Board-Report-Auszug

### Folie 15 – Kontakt / Call to Action (optional)

- **Titel:** Kontakt
- **Platzhalter:** `[Name · Rolle · E-Mail · Kalenderlink]`

---

## 2. Persona-spezifische Varianten (modulare Zusatz-Folien)

*Nicht ein zweites Deck – diese Folien **einfügen oder Folie 4/8/9–10 ersetzen** je nach Audience.*

### Variante A – Industrie-Mittelstand

**A1 – Titelfolie (optional, Untertitel anpassen)**  
- **Untertitel-Zusatz:** AI Act Readiness, NIS2-Relevanz und SAP-nahe Prozesse – ohne Konzern-Overhead

**A2 – Schwerpunktfolie „Mittelstand unter Druck“**  
- Lieferketten und kritische Dienstleistungen: NIS2 verschärft Erwartungen an Nachweise und Lieferanten
- ISO 27001 besteht oft schon – **ISO 42001** und KI-Register als sinnvolle Erweiterung
- SAP als „System der Wahrheit“: Governance-Daten mit Unternehmensprozessen verzahnen (Richtung Enterprise Connectors)

**A3 – Mini-Case (Platzhalter)**  
- **Bullets:** `[Branche]` · `[Anzahl Standorte]` · `[SAP S/4 oder andere ERP-Linie]` · Ergebnis: „Readiness-Score und Prioritätenliste für den Vorstand in Woche 4“

### Variante B – Kanzlei

**B1 – Untertitel-Zusatz (Titelfolie)**  
- Mandanten-Compliance, GoBD-Kontext und skalierbare Beratungsprodukte

**B2 – Schwerpunktfolie „Wiederholbare Mandanten-Akte“**  
- GoBD: Nachvollziehbarkeit und Aufbewahrung bei KI-gestützten Buchungs- oder Belegprozessen **thematisieren** – Umsetzung mit Mandant abstimmen
- DATEV-Ökosystem: strukturierte Exporte / Metadaten für die Kanzlei-DMS-Praxis
- Neues Angebot: „AI Governance Review“ als Standardpaket mit ComplianceHub-Dossier

**B3 – Mini-Case (Platzhalter)**  
- **Bullets:** Mandant `[Name]` · Branche `[…]` · Deliverable: „Governance-Dossier + Board-Report-Auszug für Jahresgespräch“

### Variante C – Enterprise SAP

**C1 – Untertitel-Zusatz (Titelfolie)**  
- SAP BTP, Event-getriebene Architekturen und konzernweite AI Governance

**C2 – Schwerpunktfolie „Skalierung & Signale“**  
- Viele KI-Deployments (SAP AI Core, Partner-Tools): **ein** Governance-Register und einheitliche Reports
- Event Mesh / Betriebsereignisse: Anknüpfungspunkte für Monitoring-Narrative (OAMI) – Fachlichkeit im Integrationsworkshop
- Konzern: Mandanten / Subsidiaries im Advisor-Portfolio vergleichen

**C3 – Mini-Case (Platzhalter)**  
- **Bullets:** `[Konzernbereich]` · `[SAP-Landschaft Kurzbeschreibung]` · Ergebnis: „einheitlicher Board-Report über mehrere Einheiten“

---

## 3. Maschinenlesbare Kurzform (JSON)

```json
{
  "wave": 20,
  "references_wave_19_doc": "docs/gtm/wave19-pricing-sales-playbook-stub.md",
  "references_wave_21_statement_library": "docs/gtm/compliance-statement-library-de.md",
  "references_wave_21_statements_json": "docs/gtm/statements/statements.v1.json",
  "skus": [
    "AI Act Readiness",
    "Governance & Evidence",
    "Enterprise Connectors"
  ],
  "generic_slides": [
    {"id": 1, "key": "title_credibility"},
    {"id": 2, "key": "agenda"},
    {"id": 3, "key": "problem_regulatory_landscape"},
    {"id": 4, "key": "persona_lens_optional"},
    {"id": 5, "key": "risks_ad_hoc"},
    {"id": 6, "key": "one_liner_map_once"},
    {"id": 7, "key": "module_overview"},
    {"id": 8, "key": "three_skus_fit"},
    {"id": 9, "key": "workflow_ai_act_30d"},
    {"id": 10, "key": "workflow_law_firm_dossier"},
    {"id": 11, "key": "roles_benefits"},
    {"id": 12, "key": "trust_data_governance"},
    {"id": 13, "key": "next_steps_pilot"},
    {"id": 14, "key": "qa_appendix_optional"},
    {"id": 15, "key": "contact_cta_optional"}
  ],
  "persona_insert_slides": {
    "industry_mittelstand": ["A1_title_sub", "A2_pressure_nis2_sap", "A3_mini_case"],
    "kanzlei": ["B1_title_sub", "B2_mandantenakte_gobd_datev", "B3_mini_case"],
    "enterprise_sap": ["C1_title_sub", "C2_scale_events", "C3_mini_case"]
  }
}
```

---

## 4. Platzhalter für Visuals / Diagramme (Sales-Deck)

| Folie(n)        | Empfohlene Visualisierung (später) |
| --------------- | ---------------------------------- |
| 1               | Logo + eine Zeile „DACH / Enterprise“-Key-Visual (kein Stock-Foto-Zwang) |
| 3               | **Regulatorik-Timeline** oder vier Kacheln (AI Act · NIS2 · ISO · GoBD) mit kurzen Untertiteln |
| 4               | Drei Spalten: Industrie · Kanzlei · Enterprise (Icons sachlich) |
| 5               | **Vorher/Nachher:** verstreute Icons (Excel, Mail, PDF) vs. eine zentrale Plattform-Silhouette |
| 6               | Ein Satz groß, darunter kleines **„Map once → comply many“**-Schema (Pfeil) |
| 7               | **Systemlandkarte** Module als Boxen mit kurzen Labels |
| 8               | Drei Spalten/SKUs mit je 3 Icon-Bullets (Outcome-fokussiert) |
| 9–10            | **Workflow-Schritte** (1–2–3–4) als horizontale oder vertikale Swimlane |
| 11              | **RACI-light-Matrix** oder Rollen-Avatare mit einem Nutzen-Satz je Rolle |
| 12              | Einfache **Trust-Stack**-Grafik (Tenant · Audit · Ihre Policies) |
| 13              | **Roadmap-Balken** Pilot → Onboarding → Integration |
| 14–15           | Nur Text oder Kontakt-Card |

---

*Review-Hinweis: Alle regulatorischen Aussagen mit Legal/Compliance gegen Finaltexte des Produkts und der Website abgleichen.*
