# 02 – Claim-vs-Proof-Matrix

**Zweck:** Jede Produkt-, Website- und Pitch-Aussage gegen den tatsächlich im Code
belegbaren Nachweis stellen. Grundlage für Wettbewerbs-, UWG- und
Enterprise-Due-Diligence-Festigkeit.

**Maßstab:** Ein Claim ist marktreif belegbar, wenn ein Prospect ihn mit vertretbarem
Aufwand **prüfen** kann — durch Konfiguration, Artefakt, Testlauf oder Vertrag. Ein
Claim, der nur „stimmt, wenn der Betreiber es richtig einstellt", ist ein
**konfigurierbares** Merkmal, kein Compliance-Versprechen.

## Claim-Typologie (verbindlich für alle Texte)

| Typ | Definition | Sprachlicher Marker |
|---|---|---|
| **A – Standardmäßig so ausgeliefert** | Verhalten ist Default, ohne Zutun des Kunden aktiv, im Code erzwungen | „standardmäßig", „by default" |
| **B – Konfigurierbar** | Fähigkeit existiert, muss aber aktiviert/parametriert werden | „konfigurierbar", „aktivierbar", „im Betriebsmodell festzulegen" |
| **C – Unterstützend** | Produkt liefert Struktur/Daten, die fachliche Bewertung bleibt beim Menschen | „unterstützt", „strukturiert", „bereitet vor" |
| **D – Kundenseitig zu verantworten** | Pflicht liegt beim Kunden, Produkt ist nur Werkzeug | „kundenseitig zu verantworten", „prüfpflichtig" |
| **E – Nicht belegbar** | Aussage darf so nicht geführt werden | — |

## Risiko-Level

| Level | Bedeutung |
|---|---|
| 🔴 **Hoch** | Irreführungsrisiko (UWG §5), Vertragsrisiko, oder Ausschluss in Security-Review |
| 🟠 **Mittel** | Angreifbar in Due Diligence, erklärungsbedürftig, aber verteidigbar |
| 🟢 **Niedrig** | Belegbar, ggf. Präzisierung sinnvoll |

---

## A. Kernpositionierung

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| A1 | „Mandantenfähiger Governance-Workspace" | Tenant-Modell, durchgängige Isolation, negative Cross-Tenant-Tests | **Teilweise.** `tenant_id` auf allen Tabellen, Auth-Kontext erzwingt Mandantenbindung (`app/auth_dependencies.py`). Isolation nur applikationsseitig; keine automatisierten Cross-Tenant-Negativtests im CI | 🟠 | Behalten als **Typ A**, aber präzisieren: „Mandantentrennung auf Applikationsebene mit mandantenspezifischen Schlüsseln und Sessions". Cross-Tenant-Testsuite ergänzen (P0-6) |
| A2 | „Row-Level-Security / DB-seitige Mandantentrennung" | RLS-Policies auf allen mandantenbezogenen Tabellen + aktivierte Session-GUC | **Nein.** RLS existiert für **2 von 103** Tabellen (`db/postgres/migrations/20260715_...sql`). `SET LOCAL` in `app/db_tenant.py:49` feuert nie, weil `TenantMiddleware` nicht registriert und nicht importierbar ist. GUC-Namen weichen ab (`app.current_tenant` vs. `compliancehub.tenant_id`) | 🔴 | **Claim streichen**, bis P0-1 umgesetzt. Bis dahin: „Mandantentrennung applikationsseitig; DB-seitige RLS für governte Runtime-State-Tabellen" |
| A3 | „EU-Hosting / DACH-Fokus" | Deployment-Artefakt mit Region, Vertrag, Subprozessorenliste | **Nur Frontend.** `frontend/vercel.json` → `fra1`. **Kein Deployment-Artefakt fürs Backend** (kein Dockerfile/IaC im Repo). DB-Default ist eine lokale SQLite-Datei | 🔴 | Auf **Typ B** herabstufen: „EU-Region als Zielbetriebsmodell; verbindliche Datenregion vertraglich je Vertrag". „EU-Hosting" erst nach P0-7 |
| A4 | „Governance-Layer über mehrere Normen hinweg" | Cross-Framework-Datenmodell mit Requirement-Relations | **Ja.** `compliance_frameworks`, `compliance_requirements`, `compliance_requirement_relations`, `compliance_requirement_control_links`, `app/grc/framework_mapping.py` | 🟢 | Behalten, **Typ A**. Stärkster belegbarer Differenzierer |
| A5 | „Compliance Operating System" | Operativer Kreislauf: Pflicht → Control → Task → Evidenz → Report | **Weitgehend ja.** Workflow-Engine mit SLA/Eskalation, Remediation, Board-Reports. **Aber:** kein Scheduler im Repo (`health_monitor.py:219` TODO) | 🟠 | **Typ B**: „Operating-System-Logik; zeitgesteuerte Ausführung über Betriebs-Scheduler (n8n/Cron/Temporal) einzurichten" |

---

## B. EU AI Act

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| B1 | „KI-System-Register" | Entität mit AI-Act-Pflichtfeldern, mandantenfähig | **Ja, stark.** `ai_systems` mit `intended_purpose`, `training_data_provenance`, `fria_reference`, `provider_name`, `deployer_name`, `provider_responsibilities`, `deployer_responsibilities`, `pms_status`, `pms_next_review_date`; dazu `ai_system_inventory_profiles`, `ai_register_entries` | 🟢 | Behalten, **Typ A**. Ausbauen um Rollen-Enum (P1) |
| B2 | „Risikoklassifizierung nach EU AI Act" | Art.-6-Logik, Annex-Bezug, nachvollziehbare Begründung | **Ja.** `app/services/classification_engine.py`, Entscheidungsbaum `prohibited → high_risk → limited_risk → minimal_risk`, `risk_classifications`-Tabelle | 🟢 | Behalten, aber **Typ C** kennzeichnen: „unterstützte Vorklassifizierung; rechtliche Einstufung bleibt kundenseitig zu verantworten" |
| B3 | „AI Act ready" | Vollständige Abdeckung aller anwendbaren Pflichten | **Nein.** Fehlend: AI-Literacy-Records (Art. 4), Rollen-Enum Anbieter/Betreiber/Importeur/Händler/Bevollmächtigter, Serious-Incident-Meldepfad (Art. 73), GPAI-Kennzeichnung, EU-Datenbank-Registrierungs-ID (Art. 49), Konformitätsbewertung | 🔴 | **Formulierung verboten.** Ersatz: „Unterstützung für AI-Act-Governance-Pflichten in den Bereichen Register, Klassifizierung, Transparenz und technische Dokumentation" |
| B4 | „Transparenzpflichten Art. 50" | Assessment-Struktur mit Kontrollen und Review | **Ja.** `ai_transparency_assessments`, `ai_transparency_controls`, `app/services/ai_transparency_assurance.py`, versioniert | 🟢 | Behalten, **Typ C** |
| B5 | „Human Oversight" | Feld/Prozess je System, Nachweis der Wirksamkeit | **Nur rudimentär.** 5 Dateien referenzieren `human_oversight`; keine eigene Entität mit Maßnahmen, Verantwortlichen, Wirksamkeitsnachweis | 🟠 | **Typ C** und einschränken: „Human-Oversight-Dokumentation je System". Vor Enterprise ausbauen (P1) |
| B6 | „Technische Dokumentation (Annex IV)" | Strukturierte, versionierte Dokumentabschnitte je System | **Ja.** `ai_act_docs` mit `section_key`, Unique-Constraint je Mandant/System/Abschnitt, Export (`ai_act_docs_export.py`) | 🟢 | Behalten, **Typ C** |
| B7 | „Logging / Event Record (Art. 12)" | Automatische Ereignisaufzeichnung des KI-Systems | **Teilweise.** `ai_runtime_events` existiert, wird aber **über Ingest-API vom Kunden befüllt** (`runtime_events_ingest.py`) — das Produkt beobachtet die KI-Systeme nicht selbst | 🟠 | Präzisieren: „Aufnahme und Auswertung von Laufzeitereignissen, die aus Ihren KI-Systemen übermittelt werden" — **Typ B/D** |
| B8 | „AI Literacy / Schulungsnachweise (Art. 4)" | Trainings-Entität mit Personen, Datum, Inhalt, Nachweis | **Nein.** `grep -ri ai_literacy` → 0 Treffer | 🔴 | Claim **nicht führen**, bis P1-4 umgesetzt |
| B9 | „Abgrenzung Anbieter / Betreiber" | Rollen-Enum mit pflichtenabhängiger Logik | **Nur Freitext.** `provider_name`/`deployer_name`/`*_responsibilities` sind Textfelder ohne Enum und ohne abgeleitete Pflichtenlogik. Importeur/Händler/Bevollmächtigter fehlen ganz | 🟠 | **Typ C** und ehrlich benennen: „Dokumentationsfelder für Anbieter- und Betreiberrolle". Rollenmodell in P1-3 |

---

## C. NIS2

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| C1 | „NIS2-Meldekaskade 24h/72h/1 Monat" | Fristen ab **Kenntniserlangung**, Meldungsnachweise | **Fehlerhaft.** `app/repositories/nis2_incidents.py:93` setzt alle Fristen ab `now` (Erfassungszeitpunkt) und `detected_at=now`. `NIS2IncidentCreate` hat **kein** `detected_at`/`became_aware_at`-Feld. Ein vor 3 Tagen bemerkter Vorfall bekommt heute 24h Frist | 🔴 **BLOCKER** | **Claim aussetzen** bis P0-2. Ein Fristentool, das falsche Fristen anzeigt, ist schlimmer als keines — es erzeugt Vertrauensschaden und potenzielle Haftung |
| C2 | „Nachweis gegenüber Aufsicht / BSI" | Einreichzeitpunkt, Empfänger, Aktenzeichen, Meldungsinhalt | **Nein.** `nis2_incidents` hat nur Deadline-Felder, keine Felder für tatsächliche Meldung | 🔴 | Nicht führen bis P1-5 |
| C3 | „Zwischenmeldung / Abschlussmeldung" | Eigene Meldungsobjekte mit Status | **Nein.** Nur `final_report_deadline` als Datum | 🟠 | Nicht führen. `Notification`-Entität in P1-5 |
| C4 | „Rolle der Geschäftsleitung (Art. 20 / § 38 BSIG)" | Billigungs- und Schulungsnachweis der Leitungsorgane | **Nein.** `grep -ri geschaeftsleitung\|management_body` → 0 | 🟠 | Nicht führen. Board-Approval-Entität in P1-6 |
| C5 | „Lieferanten-/Supply-Chain-Risiko (Art. 21(2)(d))" | Supplier-Entität mit Risikobewertung | **Nur Boolean.** `ai_systems.has_supplier_risk_register` ist ein Ja/Nein-Flag. Keine `suppliers`-Tabelle. `app/services/ai_governance_suppliers.py` arbeitet auf abgeleiteten Daten | 🟠 | **Typ C**, stark einschränken: „Supplier-Risiko als Governance-Signal". Echte Entität in P1-2 |
| C6 | „Maßnahmenkatalog Art. 21(2)" | Requirement-Set mit Controls | **Ja.** `compliance_requirements`/`governance_controls` mit Framework-Mapping NIS2 | 🟢 | Behalten, **Typ C** |
| C7 | „KRITIS-Board-KPIs" | KPI-Definitionen, Schwellen, Alerts | **Ja.** `nis2_kritis_kpis`, `app/config/nis2_kritis_board_alert_thresholds.py`, Drilldowns | 🟢 | Behalten, **Typ A** |
| C8 | „NIS2-ready" | Wie B3 | **Nein.** Betroffenheitsprüfung, Registrierung beim BSI, Meldungsnachweise fehlen | 🔴 | **Formulierung verboten.** Ersatz: „strukturierte Vorbereitung auf NIS2-Nachweispflichten" |

---

## D. DSGVO / Datenschutz

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| D1 | „DSGVO-konform" | Ist Eigenschaft des Gesamtsystems inkl. Verträge, Prozesse, Betrieb — nie einer Software allein | Nicht bewertbar aus Code | 🔴 | **Formulierung verboten** (auch für das eigene Produkt). Ersatz: „datenschutzfreundlich konzipiert; DSGVO-Konformität des Einsatzes verantwortet der Verantwortliche" |
| D2 | „Verzeichnis der Verarbeitungstätigkeiten (Art. 30)" | ROPA-Entität mit Zwecken, Kategorien, Rechtsgrundlagen, Empfängern, Fristen | **Nein.** Es gibt einen `VVTExport` aus **Audit-Logs** (`app/services/audit_trail_service.py`) — das ist ein Aktivitätsprotokoll, kein VVT nach Art. 30 | 🔴 | **Umbenennen.** Der aktuelle Export darf nicht „VVT" heißen. Echte ROPA-Entität in P1-1 |
| D3 | „DSFA/DPIA-Unterstützung" | DPIA-Objekt mit Schwellenwertprüfung, Risiken, Maßnahmen, Freigabe | **Nur Flag.** `ai_systems.gdpr_dpia_required` (Boolean) + `fria_reference` (Textfeld) | 🟠 | **Typ C**: „DPIA-Pflicht-Indikation je KI-System". Kein „DSFA-Modul" behaupten |
| D4 | „Löschkonzept / Retention" | Retention-Regeln je Datenkategorie + ausführender Job | **Nein.** `grep -rn "purge\|retention_until\|delete_tenant"` in `app/` → **0 Treffer**. Retention existiert nur als Spalte in der Advisor-Postgres-Migration | 🔴 **BLOCKER** | Nicht führen. P0-5. Ohne Löschkonzept ist kein AVV mit einem professionellen Auftraggeber abschließbar |
| D5 | „Betroffenenrechte / DSAR" | Auskunfts-, Berichtigungs-, Löschworkflow | **Nein.** `grep -ri dsar\|data_subject` → 0 | 🟠 | Nicht führen. P1-8 |
| D6 | „Mandanten-Export / Exit" | Vollständiger Datenexport + gesicherte Löschung bei Vertragsende | **Nein.** Einzelexporte (DATEV, CSV, PDF, Bundles) existieren; kein Tenant-Gesamtexport, keine Mandantenlöschung | 🔴 | Nicht führen. P0-5. Standardfrage jedes Einkaufs |
| D7 | „Pseudonymisierung/Redaction vor Modellaufrufen" | Deterministische Erkennung + Fail-Closed | **Teilweise, ehrlich implementiert.** `COMPLIANCEHUB_LLM_PII_MODE=block` als Default; Regex für E-Mail/IBAN/Telefon. Namen, Adressen, Gesundheitsdaten werden **nicht** erkannt | 🟠 | **Typ A + Einschränkung**: „LLM-Aufrufe werden standardmäßig blockiert, wenn heuristisch erkannte personenbezogene Muster im Prompt auftreten." Nicht: „PII wird entfernt" |
| D8 | „Subprocessor-Transparenz" | Öffentliche, versionierte Liste mit Zweck, Ort, Rechtsgrundlage | **Nur für Public Site.** Trust Center nennt Vercel; die Enterprise-Ebene ist explizit ausgeklammert | 🟠 | Konsistent halten, solange das Produkt nicht live ist. Vor erstem Kunden: vollständige Liste (P0-8) |
| D9 | „TOMs nach Art. 32" | Dokumentierte technische/organisatorische Maßnahmen | Code-Kontrollen vorhanden; **kein TOM-Dokument** im Repo | 🟠 | TOM-Dokument erstellen (P1-9) — reines Dokumentationsartefakt, schnell machbar |
| D10 | „Verschlüsselung at rest" | Nachweis für DB, Evidence, Backups | **Nein applikationsseitig.** Evidence liegt unverschlüsselt im Dateisystem; DB-Verschlüsselung wäre Plattformeigenschaft ohne Deployment-Artefakt | 🔴 | Nicht führen bis P0-7. Danach als Plattformeigenschaft mit Verweis auf Hoster |

---

## E. Sicherheit / Enterprise

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| E1 | „Audit-Logs / Evidence" | Manipulationsresistente, exportierbare Protokolle | **Ja, gut.** Hash-Kette, Append-only-Guard, GoBD-Export, `verify_integrity()` | 🟢 | Behalten mit Präzisierung: „Append-only auf Applikationsebene, Hash-Kette mit Integritätsprüfung" |
| E2 | „Unveränderliche Audit-Logs" | DB-seitige Unveränderlichkeit oder WORM | **Nein.** Guard greift nur über SQLAlchemy-Session (`app/audit_append_only.py`); direkter SQL-Zugriff umgeht ihn | 🔴 | **Wort „unveränderlich" streichen.** Siehe E1 |
| E3 | „Evidenzintegrität" | Inhalts-Hash beim Upload + Verifikation | **Nein.** `evidence_files` hat **keine** Hash-Spalte | 🔴 **BLOCKER** | Nicht führen bis P0-4 |
| E4 | „SSO / SAML / SCIM" | Implementierung + Interop-Nachweis | **Teilweise.** Entra OIDC ✔, SCIM-Service ✔, **SAML ✘**, generisches OIDC ✘ | 🟠 | Präzisieren: „SSO über Microsoft Entra ID (OIDC); SCIM-Provisionierung; SAML auf Roadmap" |
| E5 | „MFA" | Zweiter Faktor + sichere Secret-Ablage | **Teilweise.** TOTP + Backup-Codes ✔; **TOTP-Secret ohne erkennbare Verschlüsselung** in `mfa_factors` | 🔴 | Claim beibehalten, aber P0-9 vor erstem Enterprise-Kunden |
| E6 | „Secure by design" | Threat Model, Security-Reviews, Default-Deny | **Teilweise.** LLM off-by-default, PII-Block-Default, globale Keys in prod aus, CSP-Gate, CI mit Bandit/CodeQL/pip-audit. **Kein Threat Model, kein Pentest, keine Cross-Tenant-Tests** | 🟠 | Als **Typ C** führen und mit konkreten Beispielen belegen statt mit dem Schlagwort |
| E7 | „Zero Trust" | Identitätsbasierte Autorisierung jeder Anfrage, mTLS, Mikrosegmentierung | **Nein.** Keine Netzwerkarchitektur im Repo | 🔴 | **Formulierung verboten** |
| E8 | „Enterprise-ready" | SSO+SCIM+Audit+SLA+DR+Pentest+DPA+Subprozessoren | **Nein.** Kein DR, kein Pentest, kein SLA, kein Deployment-Artefakt | 🔴 | **Formulierung verboten.** Ersatz: „Enterprise-Funktionsumfang: SSO, SCIM, RBAC, Audit-Trail, Trust Center" |
| E9 | „Rate Limiting / API-Härtung" | Middleware mit Limits | **Nein.** `grep -rn "rate_limit\|slowapi"` → 0 | 🟠 | Nicht führen. P1-7 |
| E10 | „Malware-Scan für Uploads" | Scanner im Upload-Pfad | **Nein.** | 🔴 | Nicht führen bis P0-3 |
| E11 | „Disaster Recovery / Backup" | RPO/RTO, getesteter Restore | **Nein.** Kein Deployment-Artefakt | 🔴 | Nicht führen bis P0-7 |

---

## F. Souveränität / CLOUD Act

| # | Claim | Erforderlicher Nachweis | Aktuell im Code? | Risiko | Empfehlung |
|---|---|---|---|---|---|
| F1 | „EU-souverän / sovereign" | Kein US-kontrollierter Anbieter mit Zugriffsmöglichkeit im Datenpfad | **Nein.** Vercel (US) betreibt Frontend **und BFF** — der BFF terminiert Sessions und proxied Produktdaten (`frontend/src/proxy.ts`). Azure/Entra (US-Mutter), LLM-Kette mit OpenAI/Anthropic/Google | 🔴 | **Formulierung verboten** im heutigen Betriebsmodell. Erst mit Modus `Strict Sovereign` (`06-target-architecture-modes.md`) |
| F2 | „Kein US-Cloud / CLOUD-Act-sicher" | Wie F1, zusätzlich Betrieb, Support, Schlüssel, Backup in EU/EWR-Kontrolle | **Nein.** | 🔴 | **Formulierung verboten.** „CLOUD Act compliant" ist zudem inhaltlich sinnlos — der CLOUD Act ist keine Norm, der man entspricht |
| F3 | „EU-Hosting" | Serverstandort EU **und** Offenlegung der Anbieterkontrolle | **Nur Frontend-Region** (`fra1`) belegt | 🟠 | Zulässig **nur** in der Form: „Auslieferung über EU-Region (Frankfurt); Anbieter Vercel Inc. unterliegt US-Recht — siehe Subprozessorenliste" |
| F4 | „Datenresidenz EU für KI-Verarbeitung" | Erzwungene Provider-Beschränkung | **Nein.** `COMPLIANCEHUB_LLM_ASSUME_AZURE_EU` ist eine **Betreiber-Attestierung**, keine technische Prüfung; US-Provider bleiben in der Fallback-Kette | 🔴 | Nicht führen bis P0-3 (harter EU-Provider-Modus) |
| F5 | „LLM standardmäßig deaktiviert" | Feature-Flag-Default | **Ja.** `COMPLIANCEHUB_FEATURE_LLM_ENABLED=false` | 🟢 | **Behalten und offensiv nutzen** — starkes, seltenes, prüfbares Verkaufsargument im DACH-Markt |

---

## G. Bereits gut formulierte Claims (Positivliste)

Diese Formulierungen sind belegbar und sollten **unverändert bleiben**. Sie zeigen, dass
im Team bereits ein funktionierendes Claim-Bewusstsein existiert:

| Fundstelle | Formulierung | Warum tragfähig |
|---|---|---|
| `frontend/src/app/page.tsx` | „Die Plattform unterstützt Analyse und Review; Verantwortung und Freigabe bleiben beim Menschen." | Saubere Typ-C/D-Abgrenzung |
| `frontend/src/app/page.tsx` | „LLM-Funktionen sind standardmäßig aus." | Typ A, im Code belegt |
| `frontend/src/app/trust-center/page.tsx` | „Das ist weder eine Zertifizierung noch eine automatische Feststellung der Rechtskonformität eines Kunden." | Exakt die nötige Abgrenzung |
| `website/compliancehub-landing.html` | „Keine behauptete offizielle SAP- oder DATEV-Produktzertifizierung." | Vorbildlich |
| `website/compliancehub-landing.html` | „Keine Rechtsberatung." | Notwendig, vorhanden |
| `README.md` | „Release-Status: Pre-Production / nicht freigegeben." | Ehrlich |

---

## H. Zusammenfassung

| Kategorie | Claims geprüft | 🟢 belegbar | 🟠 einschränken | 🔴 streichen/aussetzen |
|---|---|---|---|---|
| Kernpositionierung | 5 | 1 | 2 | 2 |
| EU AI Act | 9 | 4 | 3 | 2 |
| NIS2 | 8 | 2 | 3 | 3 |
| DSGVO | 10 | 0 | 5 | 5 |
| Sicherheit/Enterprise | 11 | 1 | 3 | 7 |
| Souveränität | 5 | 1 | 1 | 3 |
| **Summe** | **48** | **9 (19 %)** | **17 (35 %)** | **22 (46 %)** |

**Kernaussage:** Knapp die Hälfte der marktüblichen Claims für diese Produktkategorie
ist heute **nicht wahrheitsgemäß führbar**. Das ist kein Produktversagen — die
Fachtiefe ist da — sondern eine Lücke zwischen fachlicher Modellierung und
betrieblicher Nachweisbarkeit.

Die gute Nachricht: Die 🔴-Liste ist überwiegend durch **10 konkrete P0-Maßnahmen**
schließbar (`07-refactoring-roadmap.md`), nicht durch einen Architektur-Neubau.

Die verpflichtende Regel für alle Texte lautet ab sofort:
**Kein Claim ohne benannten Nachweis in `02`.** Neue Claims erhalten vor
Veröffentlichung eine Zeile in dieser Matrix.
