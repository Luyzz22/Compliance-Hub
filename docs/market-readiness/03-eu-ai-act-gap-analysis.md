# 03 – EU AI Act Gap-Analyse

**Gegenstand:** Verordnung (EU) 2024/1689 (KI-Verordnung / EU AI Act)
**Perspektive:** Zwei Ebenen, die konsequent getrennt werden müssen:

- **Ebene 1 — Produkt als Werkzeug:** Kann ComplyWithAI seine Kunden bei deren
  AI-Act-Pflichten unterstützen? *(Das ist das Verkaufsversprechen.)*
- **Ebene 2 — Produkt als KI-System:** Welche AI-Act-Pflichten treffen ComplyWithAI
  selbst, weil das Produkt LLM-Funktionen enthält? *(Das wird regelmäßig vergessen und
  in Enterprise-Reviews abgefragt.)*

> **Hinweis zur Rechtslage:** Die Anwendungszeitpunkte der KI-VO waren zuletzt Gegenstand
> laufender Gesetzgebungsverfahren auf EU-Ebene. Dieses Dokument bewertet **funktionale
> Abdeckung**, nicht Fristen. Vor jeder Außenkommunikation mit Datumsbezug ist der
> aktuelle Stand durch qualifizierte Rechtsberatung zu verifizieren. Datumsangaben
> gehören nicht in Produktmarketing ohne solche Prüfung.

---

## Teil 1 — Ebene 1: Unterstützung der Kundenpflichten

### 1.1 KI-System-Register

**Status: BELEGT IM CODE — stärkster Bereich des Produkts.**

| Anforderung | Umsetzung | Fundstelle |
|---|---|---|
| Systeminventar je Mandant | `ai_systems` (Primary Key + `tenant_id`) | `app/models_db.py:297` |
| Zweckbestimmung | `intended_purpose` (Text) | `app/models_db.py:315` |
| Trainingsdaten-Herkunft | `training_data_provenance` | `app/models_db.py:316` |
| Anbieter/Betreiber | `provider_name`, `deployer_name` + `*_responsibilities` | `app/models_db.py:318–322` |
| Grundrechte-Folgenabschätzung | `fria_reference` (Referenzfeld) | `app/models_db.py:317` |
| Post-Market-Monitoring | `pms_status`, `pms_next_review_date`, `pms_last_review_date` | `app/models_db.py:323–330` |
| Erweitertes Profil | `ai_system_inventory_profiles` mit `use_case`, `business_process`, Scope je Norm | `app/models_db.py:342` |
| Register-Einträge | `ai_register_entries` | `app/models_db.py:458` |
| Import | CSV/XLSX-Import + Template (`frontend/public/ai-systems-template.csv`) | `app/services/ai_system_import.py` |

**Bewertung:** Diese Feldtiefe übertrifft die meisten am DACH-Markt verfügbaren
AI-Act-Tools. Der Claim „KI-System-Register" ist **voll belegbar**.

**Offene Lücken:**

| Lücke | Auswirkung | Priorität |
|---|---|---|
| Kein `ai_model` / `ai_provider` als eigene Entität | Ein System, das drei Modelle nutzt, ist nicht sauber abbildbar. Modellwechsel ist nicht historisierbar | P1 |
| Keine GPAI-Kennzeichnung (Art. 51–55) | Systeme auf Basis von GPAI-Modellen mit systemischem Risiko sind nicht als solche markierbar | P1 |
| Keine EU-Datenbank-Registrierungs-ID (Art. 49) | Hochrisiko-Betreiber müssen registrieren; Referenz nicht speicherbar | P2 |
| Kein Lebenszyklus-/Versionsstand des KI-Systems | „Welche Version war zum Prüfzeitpunkt im Einsatz?" nicht beantwortbar | P1 |
| Kein Feld für Inverkehrbringen/Inbetriebnahme-Datum | Fristenbezug nicht ableitbar | P2 |

---

### 1.2 Risikoklassifizierung

**Status: BELEGT IM CODE.**

- Entscheidungsbaum `prohibited → high_risk → limited_risk → minimal_risk`
  (`app/services/classification_engine.py`).
- Annex-I-/Annex-III-Kategorien werden berücksichtigt (`ai_act_category`).
- Ergebnisse persistiert in `risk_classifications`, versioniert, mandantenfähig.
- Wizard für geführte Selbsteinschätzung (`app/eu_ai_act_wizard_engine.py`,
  `app/services/eu_ai_act_wizard_decision.py`).
- Gap-Analyse-Dashboard aggregiert nach Risikostufe und Kategorie.

**Kritische Abgrenzung — zwingend im Produkt sichtbar:**

Die Klassifizierung nach Art. 6 ist eine **Rechtsanwendung**, keine Berechnung. Sie hängt
an Zweckbestimmung, Einsatzkontext, Ausnahmen nach Art. 6(3) und der Frage, ob das System
ein Sicherheitsbauteil eines Produkts nach Annex I ist. Ein deterministischer
Entscheidungsbaum kann das **vorbereiten**, nicht **entscheiden**.

| Anforderung | Status |
|---|---|
| Ergebnis als Vorschlag gekennzeichnet, nicht als Feststellung | **Zu verifizieren im UI** — im Datenmodell fehlt ein Feld `classification_confirmed_by` / `confirmed_at` |
| Begründungspfad nachvollziehbar (welche Regel führte zum Ergebnis) | Teilweise über `risk_classifications`; explizite Regel-Trace fehlt |
| Menschliche Bestätigung erzwungen | **OFFENE LÜCKE** — P1 |
| Ausnahmen nach Art. 6(3) abbildbar | **OFFENE LÜCKE** |

**Empfohlene Ergänzung (P1):** Felder `classification_status`
(`suggested | under_review | confirmed | disputed`), `confirmed_by_user_id`,
`confirmed_at_utc`, `confirmation_rationale`. Ohne diese Felder kann der Kunde nicht
nachweisen, dass ein Mensch die Einstufung verantwortet hat — und genau danach fragt
eine Marktüberwachungsbehörde.

---

### 1.3 Zweckbindung und Use-Case-Dokumentation

**Status: BELEGT IM CODE.** `intended_purpose` (`ai_systems`) und `use_case`
(`ai_system_inventory_profiles`, NOT NULL) sowie `business_process`.

**Lücke:** Keine Abgrenzung „bestimmungsgemäße Verwendung" vs. „vernünftigerweise
vorhersehbare Fehlanwendung" (Art. 9(2)(b)). Für Hochrisiko-Systeme ist Letzteres
Pflichtbestandteil des Risikomanagements. **P1.**

---

### 1.4 Human Oversight (Art. 14)

**Status: OFFENE LÜCKE.**

`grep -ril human_oversight app/` liefert 5 Dateien, überwiegend Text-/Report-Bausteine.
Es existiert **keine Entität**, die abbildet:

- welche Aufsichtsmaßnahmen je System vorgesehen sind (Art. 14(4)(a)–(e))
- wer die aufsichtsführende Person ist und welche Kompetenz/Befugnis sie hat
- ob sie das System übersteuern oder stoppen kann („Stop-Taste", Art. 14(4)(e))
- ob die Wirksamkeit der Aufsicht überprüft wurde und wann

**Empfehlung (P1):** Entität `human_oversight_measure` mit
`ai_system_id`, `measure_type`, `description`, `responsible_user_id`,
`can_override` (bool), `can_halt` (bool), `competence_evidence_id`,
`effectiveness_reviewed_at`, `next_review_at`.

Bis dahin darf der Claim nur lauten: *„Dokumentationsfelder für Human Oversight"*.

---

### 1.5 Logging / Aufzeichnungen (Art. 12, Art. 19)

**Status: TEILWEISE — mit wichtiger Abgrenzung.**

`ai_runtime_events` (`app/models_db.py:1052`) und `ai_runtime_incident_summaries`
existieren, ebenso ein Ingest-Pfad (`app/services/runtime_events_ingest.py`) mit
Sanitizing (`runtime_event_sanitize.py`) und Unique-Constraint gegen Doppel-Ingest.

**Entscheidende Abgrenzung:** Art. 12 verlangt, dass das **Hochrisiko-KI-System selbst**
Ereignisse automatisch aufzeichnet. ComplyWithAI **beobachtet die KI-Systeme des Kunden
nicht**. Es nimmt Ereignisse entgegen, die der Kunde übermittelt.

Das ist eine legitime und wertvolle Funktion — aber der Claim muss lauten:
*„Zentrale Aufnahme, Aufbewahrung und Auswertung von Laufzeitereignissen, die Ihre
KI-Systeme übermitteln"*, nicht *„AI-Act-Logging nach Art. 12"*.

**Lücke:** Keine konfigurierbare Aufbewahrungsfrist für `ai_runtime_events`
(Art. 12(1) verlangt angemessene Aufbewahrung; Art. 19 mindestens 6 Monate für
Anbieter, soweit anwendbar). **P1** — hängt an der Retention-Engine (P0-5).

---

### 1.6 Technische Dokumentation (Art. 11, Annex IV)

**Status: BELEGT IM CODE.**

`ai_act_docs` mit `section_key` und Unique-Constraint
`(tenant_id, ai_system_id, section_key)`, Export-Service, KI-gestützte
Entwurfsunterstützung (`ai_act_docs_ai_assist.py`, hinter Feature-Flag).

**Lücken:**

| Lücke | Priorität |
|---|---|
| Keine Versionierung der Dokumentabschnitte (nur `updated_at`) — „welcher Stand galt beim Audit?" nicht beantwortbar | P1 |
| Kein Freigabe-/Review-Status je Abschnitt | P1 |
| Kein Vollständigkeitscheck gegen die Annex-IV-Gliederung | P2 |
| Keine Verknüpfung Dokumentabschnitt ↔ Evidenzdatei | P1 |

---

### 1.7 Transparenzpflichten (Art. 50)

**Status: BELEGT IM CODE — gut umgesetzt.**

`ai_transparency_assessments` (versionierter Assurance-Header) +
`ai_transparency_controls`, Service `app/services/ai_transparency_assurance.py`,
eigener Router, Doku `docs/enterprise/wave60-article50-transparency-assurance.md`.

Deckt ab: Offenlegung KI-Interaktion, Kennzeichnung synthetischer Inhalte,
Emotionserkennung/biometrische Kategorisierung, Deepfake-Kennzeichnung.

**Lücke:** Keine technische Verifikation der Kennzeichnung (z. B. C2PA-/
Wasserzeichen-Nachweis). Das ist bewusst ein Dokumentationsmodul — so ist es auch
zu verkaufen (**Typ C**).

---

### 1.8 Rollenabgrenzung (Art. 3, 16, 22–27)

**Status: KRITISCHE LÜCKE für ein Produkt mit diesem Anspruch.**

Die KI-VO knüpft völlig unterschiedliche Pflichtenbündel an fünf Rollen:

| Rolle | Kernpflichten | Im Produkt abbildbar? |
|---|---|---|
| **Anbieter** (Art. 16) | QMS (Art. 17), techn. Doku, Konformitätsbewertung (Art. 43), CE (Art. 48), Registrierung (Art. 49), PMS (Art. 72), Vorfallmeldung (Art. 73) | Nur `provider_name` als Freitext |
| **Betreiber** (Art. 26) | Verwendung nach Gebrauchsanweisung, Human Oversight, Input-Daten-Kontrolle, Log-Aufbewahrung, Information der Betroffenen, FRIA (Art. 27) | Nur `deployer_name` als Freitext |
| **Einführer** (Art. 23) | Prüfung vor Inverkehrbringen, Kontaktdaten, Aufbewahrung | **Nicht vorhanden** |
| **Händler** (Art. 24) | Prüfpflichten, Korrekturmaßnahmen | **Nicht vorhanden** |
| **Bevollmächtigter** (Art. 22) | Vertretung von Drittland-Anbietern | **Nicht vorhanden** (`grep -ri bevollmaecht` → 0) |

**Warum das ein Blocker für die Positionierung ist:** Der wichtigste Beratungswert am
DACH-Markt ist gerade die Rollenklärung. Der Mittelstand fragt: „Bin ich Betreiber oder
werde ich durch Fine-Tuning zum Anbieter?" (Art. 25 — Rollenwechsel bei wesentlicher
Änderung oder Inverkehrbringen unter eigenem Namen). Ein Tool, das diese Frage nicht
im Datenmodell führt, kann die daraus folgenden Pflichten nicht ableiten und keine
belastbare Gap-Analyse erzeugen.

**Empfehlung (P1-3):** Enum `ai_actor_role` mit
`provider | deployer | importer | distributor | authorised_representative`, als
**n:m-Beziehung** `ai_system_actor_role` (ein Mandant kann für dasselbe System mehrere
Rollen haben), plus `role_change_trigger` (Art. 25) und daraus abgeleiteter
Pflichtenliste über `compliance_requirements`.

---

### 1.9 AI Literacy (Art. 4)

**Status: NICHT VORHANDEN.** `grep -ri "ai_literacy\|article_4"` in `app/` → 0 Treffer.

Art. 4 verpflichtet Anbieter **und** Betreiber, ein ausreichendes KI-Kompetenzniveau
ihres Personals sicherzustellen. Das ist eine der **wenigen Pflichten, die praktisch
jeden Kunden trifft** — unabhängig von Risikoklasse. Für den DACH-Mittelstand ist
das oft der erste konkrete Handlungsbedarf und damit ein idealer Einstiegs-Use-Case.

**Empfehlung (P1-4):** Entität `ai_literacy_record`:
`tenant_id`, `person_ref` (pseudonymisiert), `role`, `training_title`,
`provider`, `completed_at`, `duration_minutes`, `scope` (welche Systeme/Rollen),
`evidence_file_id`, `valid_until`, `refresher_due_at`.
Plus Aggregat „Abdeckungsgrad der KI-Kompetenz je Organisationseinheit" für den
Board-Report.

**Vertriebsargument:** Dieses Modul ist mit geringem Aufwand baubar und liefert sofort
einen erklärbaren, prüfbaren Nachweis. Empfehlung: als sichtbares Feature priorisieren.

---

### 1.10 Vorfälle und Beschwerden (Art. 73, Art. 85)

**Status: LÜCKE.**

- `incidents` und `nis2_incidents` existieren, sind aber auf Sicherheits-/
  Betriebsvorfälle ausgerichtet.
- Ein **schwerwiegender Vorfall nach Art. 3(49)** (Tod, schwere Gesundheits-/
  Sachschäden, Verletzung von Grundrechten, Störung kritischer Infrastruktur) hat
  andere Merkmale und eine eigene Meldekaskade an die Marktüberwachungsbehörde
  (Art. 73: unverzüglich, spätestens 15 Tage; 2 Tage bei weitreichenden Verstößen;
  10 Tage bei Todesfall).
- Ein Beschwerdepfad für Betroffene nach Art. 85 ist nicht modelliert.

**Empfehlung (P1-5):** `ai_serious_incident` als eigene Entität mit
`incident_category` (Art. 3(49)), `became_aware_at`, Fristenberechnung analog NIS2
(aber mit den AI-Act-Fristen), `authority`, `submitted_at`, `reference_number`,
`corrective_actions`.

---

### 1.11 Weitere Hochrisiko-Anforderungen

| Artikel | Anforderung | Status |
|---|---|---|
| Art. 9 | Risikomanagementsystem über den Lebenszyklus | **Lücke** — kein Risikoregister als Entität; nur `risk_classifications` (Einstufung ≠ Risikomanagement) |
| Art. 10 | Data Governance, Trainings-/Validierungs-/Testdaten, Bias-Prüfung | **Lücke** — nur `training_data_provenance` als Freitext |
| Art. 15 | Genauigkeit, Robustheit, Cybersicherheit | **Lücke** — keine Metrik-/Testnachweise je System (`ai_system_kpi_values` ist generisch) |
| Art. 17 | Qualitätsmanagementsystem | **Lücke** — als Requirement-Set mappbar, nicht als eigenes Modul |
| Art. 43/47/48 | Konformitätsbewertung, EU-Konformitätserklärung, CE | **Lücke** — `conformity` erscheint in 13 Dateien, aber kein Konformitätsobjekt |
| Art. 72 | Post-Market-Monitoring-Plan | **Teilweise** — `pms_status` + Review-Daten vorhanden, aber kein Plan-Dokument, keine Auswertung |

---

## Teil 2 — Ebene 2: ComplyWithAI als KI-System

**Diese Frage wird in jeder ernsthaften Enterprise-Review gestellt und ist derzeit
nicht dokumentiert.**

### 2.1 Rolleneinordnung

**PLAUSIBLE ANNAHME (durch Rechtsberatung zu bestätigen):**

ComplyWithAI integriert Fremdmodelle (Azure OpenAI, Claude, Gemini, Llama) und stellt
sie unter eigenem Namen als Produktfunktion bereit (Gap-Assist, Board-Report-Generierung,
Readiness-Explain, Advisor-Brief, RAG). Nach Art. 25 spricht viel dafür, dass
ComplyWithAI dadurch **Anbieter eines KI-Systems** wird, nicht bloß Betreiber.

**Konsequenz:** Anbieterpflichten nach Art. 16 ff. wären anwendbar — mindestens
Transparenz nach Art. 50, plausibel auch technische Dokumentation und QMS-Anteile.

### 2.2 Risikoeinstufung

**PLAUSIBLE ANNAHME:** Die LLM-Funktionen sind **kein** Hochrisiko-System nach Annex III,
solange sie ausschließlich Textentwürfe für interne Governance-Arbeit erzeugen und
keine Entscheidungen über Personen treffen. Sie fallen aber unter **Art. 50(1)**
(Offenlegung der KI-Interaktion) und potenziell **Art. 50(2)** (Kennzeichnung
KI-generierter Inhalte).

**Risiko-Hinweis:** Sollte eine Ausbaustufe „automatische Compliance-Bewertung" oder
„Score mit Rechtsfolge" liefern, ist die Einstufung neu zu prüfen. Die aktuelle
Produktsprache („unterstützt Analyse und Review; Verantwortung und Freigabe bleiben
beim Menschen") ist hier **schützend** — sie sollte nicht aufgeweicht werden.

### 2.3 Was ComplyWithAI selbst braucht

| Pflicht | Status | Maßnahme |
|---|---|---|
| Eigenes KI-System-Register für ComplyWithAI | **Nicht vorhanden** | Eigenen Mandanten „ComplyWithAI intern" anlegen und dort die eigenen LLM-Funktionen führen — **kostenlos, hochwirksam als Vertriebsbeleg** |
| Art.-50-Kennzeichnung KI-generierter Ausgaben | **Zu verifizieren im UI** | Jede LLM-erzeugte Passage in Reports muss als solche gekennzeichnet und im Export erkennbar sein |
| Art.-4-Kompetenznachweis eigenes Personal | **Nicht vorhanden** | Interne Schulung dokumentieren |
| Technische Dokumentation der eigenen LLM-Funktionen | **Nicht vorhanden** | Ableitbar aus `llm_router.py`, `guardrails.py`, `llm_call_metadata` |
| Prohibited-Practices-Selbstprüfung (Art. 5) | **Nicht vorhanden** | Einmalige dokumentierte Prüfung |

**Empfehlung mit hohem Hebel:** ComplyWithAI sollte sein eigenes Produkt auf sich selbst
anwenden und das Ergebnis als Trust-Center-Artefakt veröffentlichen („Wir führen unser
eigenes KI-Register in ComplyWithAI — hier ist der Auszug"). Das ist der stärkste
denkbare Produktbeweis und kostet fast nichts.

---

## Teil 3 — Gesamtbewertung AI Act

| Bereich | Abdeckung | Bewertung |
|---|---|---|
| KI-System-Register | 85 % | Stark, marktführungsfähig |
| Risikoklassifizierung | 75 % | Gut; Bestätigungs-Workflow fehlt |
| Zweckbindung | 70 % | Gut; Fehlanwendung fehlt |
| Technische Doku (Annex IV) | 65 % | Gut; Versionierung fehlt |
| Transparenz (Art. 50) | 80 % | Gut umgesetzt |
| Logging (Art. 12) | 40 % | Ingest ja, Retention nein, Claim präzisieren |
| Human Oversight (Art. 14) | 20 % | Lücke |
| Rollenabgrenzung (Art. 3/22–27) | 15 % | **Kernlücke der Positionierung** |
| AI Literacy (Art. 4) | 0 % | **Lücke mit dem besten Aufwand-Nutzen-Verhältnis** |
| Risikomanagement (Art. 9) | 20 % | Lücke |
| Data Governance (Art. 10) | 15 % | Lücke |
| Konformität (Art. 43/47/48/49) | 5 % | Lücke; für Betreiber-Zielgruppe nachrangig |
| Serious Incidents (Art. 73) | 10 % | Lücke |
| PMS (Art. 72) | 45 % | Ansatz vorhanden |
| **Eigene AI-Act-Position** | **0 %** | **Nicht dokumentiert** |

### Reifegrad-Score AI Act: **58 / 100**

**Begründung:** Die Register- und Dokumentationsschicht ist überdurchschnittlich.
Die Pflichtenableitungsschicht (Rollen → Pflichten → Controls → Evidenz) ist der
fehlende Baustein, der aus einem sehr guten Register ein Compliance-Werkzeug macht.

### Zulässige Außenkommunikation (Stand heute)

✅ „Strukturiertes KI-System-Register mit den Dokumentationsfeldern der KI-VO"
✅ „Unterstützte Risikoklassifizierung entlang der Logik von Art. 6 und Annex I/III"
✅ „Technische Dokumentation nach Annex-IV-Gliederung strukturiert erfassen"
✅ „Transparenzanforderungen nach Art. 50 als Kontrollregister"
✅ „KI-Funktionen standardmäßig deaktiviert"

❌ „AI Act ready" / „AI-Act-konform" / „erfüllt die KI-VO"
❌ „automatische Risikoklassifizierung" (ohne den Zusatz „unterstützend")
❌ „Art.-12-Logging" (das Produkt loggt die KI-Systeme des Kunden nicht selbst)
❌ „vollständige Pflichtenabdeckung"
