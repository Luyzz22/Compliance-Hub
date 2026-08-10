# 05 – DSGVO, Schrems II und US CLOUD Act Gap-Analyse

**Gegenstand:** Verordnung (EU) 2016/679 (DSGVO), Kapitel V (Drittlandtransfers),
EuGH C-311/18 („Schrems II"), EU-US Data Privacy Framework, US CLOUD Act
(18 U.S.C. § 2713) und FISA § 702.

**Zwei Rollen, die getrennt zu betrachten sind:**

- **ComplyWithAI als Auftragsverarbeiter** (Art. 28) für Kundendaten in der Plattform.
- **ComplyWithAI als Verantwortlicher** für eigene Daten (Nutzerkonten, Leads,
  Website-Logs, Support).

Die meisten der folgenden Lücken betreffen die erste Rolle — und damit die
Abschlussfähigkeit jedes AVV.

---

## 1. Dateninventar und Datenkategorien

**Status: OFFENE LÜCKE — es existiert kein Dateninventar.**

Aus dem Schema lässt sich rekonstruieren, welche personenbezogenen Daten verarbeitet
werden. Ein **explizites, gepflegtes Inventar** gibt es nicht. Rekonstruktion:

| Kategorie | Tabellen/Felder | Betroffene | Sensibilität |
|---|---|---|---|
| Kontodaten | `users` (E-Mail, Passwort-Hash, Profil), `user_tenant_roles` | Kundenmitarbeiter | Normal |
| Sitzungsdaten | `user_sessions`, `external_identities` (`tid`, `oid`) | Kundenmitarbeiter | Normal |
| Authentifizierungsgeheimnisse | `mfa_factors` (**TOTP-Secret**), `mfa_backup_codes` | Kundenmitarbeiter | **Hoch** |
| Verhaltensdaten | `audit_logs` (`actor`, `ip_address`, `user_agent`), `usage_events`, `privileged_action_events`, `trust_center_access_logs` | Kundenmitarbeiter | **Hoch** (Verhaltens-/Leistungskontrolle, § 87 BetrVG) |
| Fachliche Kontaktdaten | `ai_systems.owner_email`, `evidence_files.uploaded_by`, `governance_workflow_tasks.assignee_user_id`, `compliance_deadlines.owner` | Kundenmitarbeiter | Normal |
| **Unstrukturierte Inhalte** | `evidence_files` (hochgeladene PDF/DOCX/XLSX/Bilder) | **Unbestimmt** | **Unbestimmt — potenziell Art. 9** |
| Freitextfelder | `incidents.summary`, `nis2_incidents.summary`, `ai_act_docs`, Kommentare | Unbestimmt | Unbestimmt |
| LLM-Metadaten | `llm_call_metadata` | Kundenmitarbeiter | Normal |
| Leads | `frontend/data/lead-inquiries` | Interessenten | Normal |

**Die kritische Zeile ist `evidence_files`.** Ein GRC-Tool bekommt Auditberichte,
Verträge, Screenshots, Protokolle, Personallisten und potenziell Gesundheits- oder
Beschäftigtendaten. Solange es keine Klassifizierung, kein Verbot besonderer Kategorien
und keinen Prüfmechanismus gibt, ist die Datenkategorie **unbestimmt** — und damit
ist keine belastbare TOM-Aussage und keine belastbare Löschfrist möglich.

**Empfehlung (P1-1):** Entitäten `data_processing_activity` (ROPA),
`data_category`, `data_subject_category`, `legal_basis` — plus Pflichtfeld
`data_classification` auf `evidence_files` und eine explizite Vertragsklausel
„keine besonderen Kategorien nach Art. 9 ohne vorherige schriftliche Vereinbarung".

---

## 2. Verarbeitungszwecke und Rechtsgrundlagen

**Status: NICHT MODELLIERT.**

Kein Feld im gesamten Schema hält einen Verarbeitungszweck oder eine Rechtsgrundlage
(Art. 6/9). `app/services/audit_trail_service.py` erzeugt zwar einen `VVTExport` —
dieser exportiert aber **Audit-Log-Zeilen**, nicht Verarbeitungstätigkeiten.

**Das ist eine Fehlbezeichnung mit Haftungspotenzial.** Ein Kunde, der diesen Export
als „VVT nach Art. 30" gegenüber seiner Aufsichtsbehörde vorlegt, legt ein
Aktivitätsprotokoll vor. Bezeichnung sofort ändern (P0-10), unabhängig von der
Implementierung der echten ROPA.

---

## 3. Vendor-Kette und AVV-Relevanz

**BELEGT IM CODE.** Bewertung nach dem Maßstab: *Wer kann rechtlich zur Herausgabe
gezwungen werden?* — nicht: *Wo steht der Server?*

| Vendor | Funktion | Kontrolle | Datenpfad | CLOUD-Act-Exposition | Bewertung |
|---|---|---|---|---|---|
| **Vercel Inc.** | Frontend + **BFF** (48 Server-Routes inkl. `api/backend/[...path]` Catch-all-Proxy) | **US** | **Voller Zugriff auf alle Anfrage-/Antwortdaten im Klartext**, terminiert Session-Cookies | **Sehr hoch** | 🔴 **Unvereinbar mit jeder Souveränitätspositionierung** |
| **Microsoft (Azure OpenAI)** | LLM | **US** (EU-Region konfigurierbar) | Prompt-Inhalte, wenn LLM aktiv | Hoch, mit EU Data Boundary abgemildert | 🟠 Vertretbar mit SCC/TIA + Doku |
| **Microsoft (Entra ID)** | IdP | **US** | Identitätsdaten, Anmeldeereignisse | Hoch | 🟠 In DACH faktisch Standard; vertretbar mit Doku |
| **OpenAI** | LLM-Fallback | **US** | Prompt-Inhalte | **Sehr hoch** | 🔴 In EU-Modus zu verbieten |
| **Anthropic** | LLM-Fallback | **US** | Prompt-Inhalte | **Sehr hoch** | 🔴 In EU-Modus zu verbieten |
| **Google (Gemini)** | LLM-Fallback | **US** | Prompt-Inhalte | **Sehr hoch** | 🔴 In EU-Modus zu verbieten |
| **GitHub/Microsoft** | Code, CI, CodeQL | **US** | **Kein** Kundendatenpfad | Niedrig | 🟢 Unkritisch, in Subprozessorenliste als Entwicklungsdienstleister nennen |
| **Stripe** | Billing (Code vorhanden) | **US** | Zahlungs-/Rechnungsdaten | Mittel | 🟠 Prüfen, ob aktiv; ggf. EU-Alternative (Mollie, Adyen) |
| **Temporal** | Workflow | US-Firma, self-host möglich | Board-Report-Daten | Mittel (Cloud) / Niedrig (self-hosted) | 🟢 self-hosted |
| **n8n** | Automatisierung | **DE** (n8n GmbH), self-host möglich | Report-/Reminder-Daten | Niedrig | 🟢 Positiv |
| Sentry | — | — | **Nicht verwendet** | — | 🟢 Positiv, aktiv kommunizieren |

### 3.1 Der Vercel-Befund im Detail

Dies ist der zentrale Souveränitätsbefund und muss klar benannt werden.

`frontend/src/app/api/backend/[...path]/route.ts` ist ein **Catch-all-Proxy**: jede
authentifizierte Produktanfrage des Browsers läuft über eine Vercel-Serverless-Funktion,
die Anfrage und Antwort **im Klartext** verarbeitet, bevor sie das FastAPI-Backend
erreicht. Zusätzlich setzt und liest Vercel-Code die Session-Cookies
(`frontend/src/lib/serverSession.ts`).

Das bedeutet:

1. Vercel Inc. ist **Auftragsverarbeiter für den gesamten Produktdatenverkehr**,
   nicht nur für statische Assets.
2. `regions: ["fra1"]` legt den Ausführungsort fest, **nicht die Kontrolle**. Vercel Inc.
   ist ein US-Unternehmen und unterliegt dem CLOUD Act unabhängig vom Serverstandort.
3. Die Aussage im Trust Center — „Für die öffentliche Website wird Vercel zur
   Web-Auslieferung eingesetzt" — ist für den **Public-Site-Release** korrekt, wird aber
   **unzutreffend**, sobald das authentifizierte Produkt live geht. Dieser Übergang muss
   in den Texten mitgezogen werden, sonst entsteht eine irreführende Aussage.

**Konsequenz für die Positionierung:** In den Modi `EU Sovereign` und
`Strict Sovereign` muss Vercel aus dem Datenpfad verschwinden (Self-Hosted Next.js
bei einem EU-Anbieter). Im Modus `Standard DACH Compliance` ist Vercel mit SCC +
TIA + Offenlegung vertretbar — aber **nur ohne jede Souveränitätsaussage**.

---

## 4. Drittlandtransfers, SCC und TIA

**Status: NICHT MODELLIERT — weder für die Kunden noch für ComplyWithAI selbst.**

`grep -ri "transfer_impact\|standard_contractual\|schrems"` in `app/` → praktisch keine
Treffer (die 66 `tia`-Treffer sind Substring-Fehltreffer wie „Initialisierung",
„Differentia…").

Fehlend:

| Artefakt | Für Kunden (Produktfunktion) | Für ComplyWithAI (Betrieb) |
|---|---|---|
| Transfer Record (welche Daten, an wen, in welches Land, auf welcher Grundlage) | ✘ | ✘ |
| TIA / Transfer Impact Assessment | ✘ | ✘ |
| SCC-Modul und -Version | ✘ | ✘ |
| Zusatzmaßnahmen (Verschlüsselung, Pseudonymisierung) | ✘ | ✘ |
| DPF-Zertifizierungsstatus des Empfängers + Prüfdatum | ✘ | ✘ |

**Doppelter Hebel:** Ein `transfer_record` + `tia`-Modul ist gleichzeitig
(a) ein verkäufliches Produktmodul und (b) die eigene Hausaufgabe. Das Produkt kann
seine eigene Vendor-Kette darin abbilden und den Auszug als Trust-Center-Artefakt
veröffentlichen. **P1-1.**

---

## 5. Auftragsverarbeitung vs. eigene Verantwortlichkeit

**Status: NICHT DOKUMENTIERT.**

Es fehlt eine klare Abgrenzung, welche Verarbeitungen ComplyWithAI als
Auftragsverarbeiter (weisungsgebunden) und welche es als eigener Verantwortlicher
durchführt. Typische Streitpunkte, die im AVV geregelt sein müssen:

| Verarbeitung | Voraussichtliche Rolle | Im Repo geregelt? |
|---|---|---|
| Mandanten-Fachdaten (KI-Register, Evidenz, Incidents) | Auftragsverarbeiter | ✘ |
| Nutzerkonten der Kundenmitarbeiter | Auftragsverarbeiter | ✘ |
| `usage_events` / Produktnutzungsanalyse | **Strittig** — häufig eigene Verantwortlichkeit | ✘ |
| `llm_call_metadata` | Auftragsverarbeiter | ✘ |
| Support-Zugriffe | Auftragsverarbeiter mit Sonderregelung | ✘ |
| Lead-Daten (`frontend/data/lead-inquiries`) | Eigener Verantwortlicher | ✘ |
| Website-Logs | Eigener Verantwortlicher | Teilweise (Datenschutzerklärung) |

**Empfehlung (P0-8):** AVV-Muster mit Anlage „Verarbeitungsübersicht" und Anlage
„Subprozessoren" erstellen. Reines Dokumentationsartefakt, in wenigen Tagen machbar,
**zwingend vor dem ersten zahlenden Kunden.**

---

## 6. Löschkonzept und Aufbewahrung

**Status: KRITISCHER BLOCKER — nicht vorhanden.**

Verifiziert: `grep -rn "purge\|retention_until\|delete_tenant\|erase"` über `app/` →
**0 Treffer**. `retention_until` existiert ausschließlich in der
Postgres-Migration für zwei Advisor-Tabellen, ohne ausführenden Job.

Das bedeutet konkret:

- Es gibt **keine** Aufbewahrungsfristen je Datenkategorie.
- Es gibt **keinen** Löschjob.
- Es gibt **keine** Mandantenlöschung bei Vertragsende.
- Audit-Logs wachsen unbegrenzt — und sind wegen des Append-only-Guards
  **nicht einmal regulär löschbar**.
- `ai_runtime_events` wachsen unbegrenzt.
- Evidence-Dateien werden nie automatisch entfernt.

**Konflikt, der aufgelöst werden muss:** Der Append-only-Guard
(`app/audit_append_only.py`) verhindert jedes DELETE auf `audit_logs`. Damit steht
Art. 5(1)(e) DSGVO (Speicherbegrenzung) im direkten Widerspruch zur
Unveränderlichkeitsarchitektur. Die Lösung ist ein **kontrollierter,
protokollierter Retention-Pfad**, der Legal Holds respektiert — nicht das Aufheben
des Guards.

**Empfehlung (P0-5):**
1. Entität `retention_rule`: `data_category`, `retention_period`, `legal_basis`
   (z. B. § 147 AO, § 257 HGB, Art. 5(1)(e) DSGVO), `action`
   (`delete | anonymize | archive`), `legal_hold_supported`.
2. Entität `legal_hold` mit Bezug auf Mandant/Entität/Zeitraum.
3. Retention-Job mit eigenem, protokolliertem Systemakteur, der den
   Append-only-Guard über einen explizit benannten Pfad passiert und jede Löschung
   als Metadaten-Nachweis (ohne Nutzdaten) festschreibt — analog zur bereits
   existierenden `runtime_state_deletion_audit`-Logik in der Postgres-Migration.
   **Dieses Muster ist im Repo schon vorhanden und sollte auf den Kern übertragen werden.**
4. `tenant_deletion`-Workflow: Export → Karenzzeit → gesicherte Löschung → Bestätigung.

---

## 7. Betroffenenrechte (Art. 12–22)

**Status: NICHT VORHANDEN.**

Kein Workflow für Auskunft, Berichtigung, Löschung, Einschränkung,
Datenübertragbarkeit oder Widerspruch. Für einen Auftragsverarbeiter ist die zentrale
Pflicht die **Unterstützung des Verantwortlichen** (Art. 28(3)(e)) — der Kunde muss
ein Auskunftsersuchen seiner Mitarbeiter innerhalb eines Monats beantworten können und
braucht dafür einen Export aus der Plattform.

**Empfehlung (P1-8):** `dsar_request` mit Typ, Betroffenem, Eingang, Frist,
Bearbeiter, Ergebnis, Nachweis — plus ein technischer „Alle Daten zu Nutzer X"-Export.
Dieselbe Entität ist auch als **Kundenmodul** verkaufbar.

---

## 8. Technische und organisatorische Maßnahmen (Art. 32)

**Status: Kontrollen vorhanden, Dokument fehlt.**

| Maßnahme | Status | Belegstelle |
|---|---|---|
| Pseudonymisierung | Teilweise | `COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY`, `audit_metadata_sanitize.py` |
| Verschlüsselung Transport | ✔ | HSTS, HTTPS-Zwang für Azure OpenAI |
| Verschlüsselung at rest | ✘ applikationsseitig | Evidence liegt im Klartext im Dateisystem |
| Vertraulichkeit (Zugriffskontrolle) | ✔ | RBAC 10 Rollen / 47 Permissions, MFA, SSO |
| Integrität | Teilweise | Audit-Hash-Kette ✔; **Evidence ohne Hash ✘** |
| Verfügbarkeit / Belastbarkeit | ✘ | Kein DR-Konzept, kein Deployment-Artefakt |
| Wiederherstellbarkeit | ✘ | Kein getesteter Restore |
| Regelmäßige Überprüfung | Teilweise | CI-Sicherheitschecks ✔; kein Pentest, kein Threat Model |

**Empfehlung (P1-9):** TOM-Dokument nach Art. 32 als Anlage zum AVV. Es kann fast
vollständig aus dem vorhandenen Code abgeleitet werden — hoher Nutzen, geringer Aufwand.

---

## 9. Mandantenisolation

Siehe `01` §5 und `02` A1/A2. Zusammenfassung aus Datenschutzsicht:

- Applikationsseitige Isolation: **belegt**, konsistent umgesetzt.
- DB-seitige Isolation (RLS): **für den Kern nicht wirksam** (`TenantMiddleware` nicht
  registriert, nicht importierbar, GUC-Namen inkonsistent).
- **Keine automatisierten Cross-Tenant-Negativtests** in der 178-Dateien-Testsuite.
- Schwächste Autorisierungsstelle: der Advisor-Pfad
  (`app/security.py::require_advisor_api_access`) mit globalem API-Key +
  selbstdeklariertem `x-advisor-id`-Header.

Für einen Auftragsverarbeiter mit mehreren Kunden in einer Datenbank ist der Nachweis
der Mandantentrennung die **Kernfrage jedes Datenschutzbeauftragten**. Ohne
Negativtests ist sie nicht beantwortbar. **P0-6.**

---

## 10. Schlüsselmanagement

**Status: OFFENE LÜCKE.**

- Kein Key-Management-System, kein Key Vault im Code.
- Signaturschlüssel für Evidence-Bundles: `signing_key_id` existiert, Rotationslogik
  ist vorbereitet — **positiv**.
- TOTP-Secrets in `mfa_factors`: **kein Verschlüsselungspfad erkennbar** — 🔴.
- API-Keys: SHA-256 ohne Salt/KDF, ohne `expires_at`, ohne Rotationsmechanismus.
- BYOK / Customer Managed Keys: **nicht vorhanden, nicht vorbereitet**.

**Empfehlung:** P0-9 (TOTP-Verschlüsselung), P2 (BYOK-Readiness als
Enterprise-Verkaufsargument).

---

## 11. Datenminimierung

**Positiv:** `UserDB` trägt den Kommentar „DSGVO data-sparse"; die Registrierung gibt
kein Verifikationstoken zurück; API-Keys werden gehasht; `AuthContext.api_key` ist
`exclude=True, repr=False` — der Credential landet nicht in Logs oder Serialisierungen.
Das zeigt Bewusstsein.

**Negativ:**
- `audit_logs.before`/`after` speichern **vollständige Zustandsobjekte als JSON**. Bei
  Entitäten mit Freitext (Incident-Summary, Doku-Abschnitte) landen damit
  potenziell personenbezogene Daten unbegrenzt und **unlöschbar** im Audit-Log.
- `ip_address` und `user_agent` in `audit_logs` und `trust_center_access_logs` ohne
  Löschfrist.

**Empfehlung (P1):** Feldbasierte Allowlist für `before`/`after` statt
Voll-Serialisierung, plus Anwendung der Retention-Regeln (P0-5).

---

## 12. Pseudonymisierung / Redaction vor Modellaufrufen

**Status: TEILWEISE — ehrlich implementiert, klar zu kommunizieren.**

Was funktioniert (`app/llm/guardrails.py`):
- Erkennung von E-Mail, IBAN-ähnlichen Mustern, Telefonnummern
- Erkennung von 9 Prompt-Injection-Markern
- Risikoeinstufung low/medium/high mit Logging
- `COMPLIANCEHUB_LLM_PII_MODE=block` als **Default** → Aufruf wird verweigert
- Alternativer Redaction-Modus (nicht-produktiv)

Was **nicht** erkannt wird: Namen, Adressen, Geburtsdaten, Personal-/Kundennummern,
Gesundheitsdaten, Beschäftigtendaten, Freitext-Personenbezug jeder Art. Der
Code-Kommentar „extend with DLP/HITL in production" ist ein offener TODO.

**Kommunikationsregel:**
✅ „LLM-Aufrufe werden standardmäßig blockiert, wenn heuristisch erkennbare
personenbezogene Muster im Prompt enthalten sind."
❌ „Personenbezogene Daten werden vor Modellaufrufen entfernt."

---

## 13. Support-Zugriffskonzept

**Status: NICHT VORHANDEN — häufige Ausschlussfrage in Enterprise-Reviews.**

Es gibt kein Konzept für:
- Wer darf im Support auf Mandantendaten zugreifen?
- Braucht es eine Kundenfreigabe (Access Approval)?
- Ist der Zugriff zeitlich begrenzt?
- Wird er dem Kunden sichtbar protokolliert?

Es existieren `privileged_action_events` und `approval_requests` — die Bausteine sind
da, aber nicht zu einem Support-Zugriffsmodell verbunden.

**Empfehlung (P1-10):** „Break-Glass mit Kundenfreigabe": Support-Zugriff erfordert
Ticketbezug + Begründung + zeitliche Begrenzung, wird in einem für den Kunden
einsehbaren Log geführt. Das ist ein **starkes Verkaufsargument**, weil es fast kein
Wettbewerber sauber hat.

---

## 14. EU-only / Sovereign-Betriebsoptionen

**Status: NICHT VORHANDEN als erzwingbarer Modus.**

Vorhanden sind Betreiber-**Attestierungen** als ENV-Flags:
`COMPLIANCEHUB_LLM_ASSUME_AZURE_EU`, `COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU`,
`COMPLIANCEHUB_LLM_US_CLOUD_OK`. Diese ändern nur die **Routing-Bewertung**, sie
entfernen US-Provider **nicht aus der Fallback-Kette**
(`app/services/llm_router.py::_prefer_configured_azure` sortiert Azure nur nach vorne).

Es fehlt ein zentraler, erzwingender Betriebsmodus. **Fix: P0-3** — ein
`COMPLIANCEHUB_SOVEREIGNTY_MODE` mit einer im Code hinterlegten Vendor-Allowlist,
der Startup-Verifikation, Provider-Filterung und Claim-Freigabe steuert.
Zielarchitektur: `06-target-architecture-modes.md`.

---

## 15. Gesamtbewertung DSGVO / Souveränität

| Bereich | Abdeckung |
|---|---|
| Dateninventar | 15 % |
| Zwecke / Rechtsgrundlagen | 0 % |
| ROPA (Art. 30) | 5 % (Fehlbezeichnung eines Audit-Exports) |
| AVV-Vendor-Kette | 10 % |
| Drittlandtransfers / SCC / TIA | 0 % |
| Löschkonzept / Retention | **0 %** |
| Betroffenenrechte | 0 % |
| TOMs (Art. 32) | 55 % Kontrollen, 0 % Dokument |
| Mandantenisolation | 60 % (App ja, DB nein, keine Negativtests) |
| Schlüsselmanagement | 20 % |
| Datenminimierung | 45 % |
| PII-Schutz vor LLM | 55 % |
| Support-Zugriffskonzept | 10 % |
| Subprozessor-Transparenz | 25 % (nur Public Site) |
| EU-only-Betriebsmodus | 0 % |

### Reifegrad-Score DSGVO: **24 / 100**
### Reifegrad-Score Souveränität/CLOUD Act: **12 / 100**

---

## 16. Klartext-Bewertung der US-Anbieter

Wie vom Auftrag verlangt, ohne Weichzeichnung:

**🟢 Vertretbar mit Dokumentation und SCC/TIA (Modus `Standard DACH Compliance`):**
- Microsoft Entra ID — in DACH faktischer Standard, Kunden bringen ihn selbst mit
- Microsoft Azure OpenAI mit EU-Region/EU Data Boundary
- GitHub/CodeQL — kein Kundendatenpfad
- Vercel — **nur** mit vollständiger Offenlegung und ohne jede Souveränitätsaussage

**🟠 Problematisch für „EU-only"-Claims:**
- Vercel als BFF im Klartext-Datenpfad
- Azure OpenAI, solange die EU-Region nur *attestiert* und nicht *technisch erzwungen* ist
- Stripe, falls aktiv

**🔴 Unvereinbar mit harter Souveränitätspositionierung:**
- Vercel Inc. im Datenpfad — **der zentrale Blocker**
- OpenAI, Anthropic, Google Gemini in der LLM-Kette
- Jede US-kontrollierte Managed-Datenbank ohne Kundenschlüssel

**🔵 Nur im optionalen Kundenmodus vertretbar:**
- LLM-Funktionen generell — heute korrekt: standardmäßig deaktiviert. **Diese
  Grundhaltung ist beizubehalten und offensiv zu vermarkten.**

---

## 17. Die zehn Fragen, die heute nicht beantwortbar sind

Diese Fragen kommen in jeder DACH-Enterprise-Beschaffung. Aktuell gibt es auf keine
eine belegbare Antwort:

1. Wo werden meine Daten gespeichert und wer kontrolliert diesen Anbieter?
2. Wer sind Ihre Subprozessoren? *(Liste existiert nur für die Public Site)*
3. Wie lange speichern Sie meine Daten und wie löschen Sie sie?
4. Was passiert mit meinen Daten bei Vertragsende?
5. Wie stellen Sie sicher, dass ein anderer Mandant meine Daten nicht sieht?
6. Wer aus Ihrem Support kann auf meine Daten zugreifen, und sehe ich das?
7. Wann war Ihr letzter Penetrationstest?
8. Wie ist Ihr RPO/RTO und wann haben Sie den Restore zuletzt getestet?
9. Bitte um AVV, TOM-Dokument und Subprozessorenliste.
10. Verlassen meine Daten die EU? Wenn ja, auf welcher Rechtsgrundlage?

**Sieben davon (1, 2, 3, 4, 6, 9, 10) sind reine Dokumentations- oder
Konfigurationsarbeit und in zwei bis drei Wochen lösbar.** Nur 5, 7 und 8 erfordern
technische Arbeit. Das ist die günstigste Investition im gesamten Backlog.
