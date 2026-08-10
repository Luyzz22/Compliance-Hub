# 00 – Executive Marktreife-Bewertung

**Reviewdatum:** 2026-08-09
**Gegenstand:** ComplyWithAI.de / Compliance Hub — `Luyzz22/Compliance-Hub` @ `485c99c`
**Maßstab:** Enterprise- und Regulatorik-Readiness für den deutschen und DACH-Markt
**Grundlage:** Vollständige statische Codeanalyse (409 Python-Module, 71.474 LOC,
103 ORM-Tabellen, 480 TypeScript-Dateien, 178 Testdateien)

---

## A. Scorecard

| Dimension | Score | Begründung in einem Satz |
|---|---:|---|
| **Produktreife** | **68** | Fachliche Modellierung überdurchschnittlich, Betriebsschicht fehlt |
| **Sicherheitsreife** | **54** | Gute Grundlagen und exzellente CI, aber keine DB-seitige Mandantenschranke und kein Pentest |
| **DSGVO-Reife** | **24** | Kein Löschkonzept, kein ROPA, keine Transferdokumentation, kein AVV |
| **AI-Act-Reife** | **58** | Register und Dokumentation stark, Rollen- und Pflichtenableitung fehlt |
| **NIS2-Reife** | **41** | Struktur richtig, Fristenanker war falsch, Lieferkette und Meldungsnachweise fehlen |
| **Sovereignty / CLOUD Act** | **12** | US-Anbieter im Klartext-Datenpfad, kein erzwungener EU-Modus |
| **Enterprise-Vertriebsreife** | **22** | Acht der zehn häufigsten Dealbreaker sind offen |
| **Messaging-Wahrhaftigkeit** | **71** | Website vorbildlich zurückhaltend; im Produkt fanden sich erfundene Rechtsangaben |
| **Gesamt (gewichtet)** | **44 / 100** | |

*Die Scores beziehen sich auf den Ausgangsstand `485c99c`. Der Effekt der in diesem
Change-Set umgesetzten Maßnahmen ist in §E ausgewiesen.*

### Was das Produkt heute stark macht

1. **Cross-Regulation-Layer** — `compliance_requirement_relations` und das
   Framework-Mapping sind der belegbare Differenzierer. Kein Wettbewerber im
   DACH-Mittelstandssegment führt fünf Normen auf ein gemeinsames Kontrollmodell zurück.
2. **KI-Register mit echten Pflichtfeldern** — `intended_purpose`,
   `training_data_provenance`, `fria_reference`, Anbieter/Betreiber, PMS-Status. Das ist
   mehr Tiefe als die meisten AI-Act-Tools am Markt.
3. **CI-Disziplin** — Bandit, CodeQL, pip-audit, npm audit, OPA-Tests,
   PostgreSQL-RLS-Test, Dependency Review, SHA-gepinnte Actions, Dependabot. Deutlich
   über dem Marktdurchschnitt und der stärkste Punkt im Security-Fragebogen.
4. **LLM off by default + PII-Block by default** — prüfbar, selten und exakt das, was
   ein deutscher Datenschutzbeauftragter hören will.
5. **Messaging-Hygiene auf der öffentlichen Website** — „Verantwortung und Freigabe
   bleiben beim Menschen", „Keine behauptete Zertifizierung", „Keine Rechtsberatung".
   Da ist bereits Claim-Bewusstsein vorhanden.

### Was den Score drückt

Fast alles Blockierende liegt in der **Betriebs- und Nachweisschicht**, nicht in der
Fachlichkeit:

- **Kein Deployment-Artefakt für das Backend.** Kein Dockerfile, keine IaC, kein
  Deploy-Workflow. Damit sind Hosting-, Residenz-, DR- und Verfügbarkeitsaussagen
  nicht nur unbelegt, sondern unbelegbar.
- **SQLite als Default-Datastore** für ein mandantenfähiges GRC-SaaS.
- **RLS wurde beworben, war aber wirkungslos** — die zuständige Middleware war nicht
  registriert und nicht einmal importierbar.
- **Kein Löschkonzept.** `grep` über `app/` nach `purge|retention_until|delete_tenant`
  ergab null Treffer. Damit ist kein AVV abschließbar.
- **Kein Scheduler** für genau die Fristen, die das Produkt verspricht.
- **US-LLM-Provider ohne erzwingbaren EU-Modus.**

---

## B. Blocker-Liste

### P0 — vor jedem produktiven Rollout

| ID | Blocker | Status |
|---|---|---|
| P0-1 | Postgres-RLS auf alle mandantenbezogenen Tabellen | ⏳ offen (Vorarbeit erledigt) |
| P0-2 | NIS2-Fristen ab Kenntniserlangung | ✅ **umgesetzt** |
| P0-3 | Souveränitätsmodus erzwingen statt attestieren | ✅ **umgesetzt** |
| P0-4 | Evidenzintegrität: Hash + Magic Bytes | ✅ **umgesetzt** (Malware-Scan offen) |
| P0-5 | Retention, Löschkonzept, Mandanten-Exit | ⏳ offen |
| P0-6 | Scheduler mit nachweisbarem Heartbeat | ⏳ offen |
| P0-7 | Deployment-Artefakt, IaC, DR | ⏳ offen |
| P0-8 | AVV, TOM, Subprozessorenliste, TIA | ⏳ offen (Dokumentation) |
| P0-9 | TOTP-Secrets verschlüsseln | ⏳ offen |
| P0-10 | Fehlbezeichnung „VVT" beseitigen | ✅ **umgesetzt** |
| P0-11 | `NEXT_PUBLIC_API_KEY` aus Vorlagen entfernen | ✅ **umgesetzt** |
| P0-12 | Cross-Tenant-Negativtestsuite | ⏳ offen |

**Zusätzlich in diesem Change-Set behoben:** toter RLS-Pfad und latenter
Cross-Tenant-Bypass in `tenant_middleware.py`, SQLite-Startup-Guard für Produktion,
verpflichtende Advisor-Allowlist, Domain-Auto-Admin in Produktion deaktiviert.

### P1 — vor dem ersten Enterprise-Kunden

DSGVO-Domäne (ROPA, Transfer Records, TIA, DPA) · Supplier-/Subprozessoren-Register ·
AI-Act-Rollenmodell · AI-Literacy-Register · `regulatory_notifications` ·
Geschäftsleitungs-Billigung und NIS2-Scope-Assessment · Rate Limiting und Idempotenz ·
DSAR-Workflow · TOM-Dokument · Support-Zugriffsmodell · Risikoregister ·
Human-Oversight-Entität · Klassifizierungs-Bestätigung · Versionierung `ai_act_docs` ·
SAML 2.0 · externer Zeitstempel-Anker · `main.py` aufteilen · Penetrationstest.

Details: `07-refactoring-roadmap.md`.

### P2 — erste 6 Monate

Asset-Register · Kontroll-Klassifizierung · Legal Entity/Jurisdiction ·
AI Models/Providers als Entitäten · NIS2-Registrierung · Alembic ·
Audit-Feld-Allowlist · SBOM und Artefaktsignierung · Trust-Center-Statusseite ·
BYOK-Readiness · Standardformat-Export · ISO-27001-Vorbereitung.

### P3 — optional

`Strict Sovereign` als Produkt · self-hosted Inferenz · öffentliche API mit SDKs ·
anonymisiertes Benchmarking · Behördenschnittstellen · White-Label · Mobile Freigaben.

---

## C. Umsetzungsergebnis dieses Change-Sets

**39 Dateien geändert, 4.822 Zeilen hinzugefügt, 295 entfernt.**
Tests: **1.478 Backend-Tests grün**, ruff und bandit sauber, Frontend-Lint und
314 Frontend-Tests grün.

### Geänderter Code

| Datei | Änderung | Adressiertes Risiko |
|---|---|---|
| `app/tenant_middleware.py` | **gelöscht** | Nicht registrierte, nicht importierbare Klasse, die bei Aktivierung einen unauthentifizierten `x-tenant-id`-Header als RLS-Mandanten akzeptiert hätte |
| `app/db_tenant.py` | Mandant aus verifiziertem `AuthContext`, GUC `compliancehub.tenant_id`, fail-closed | Sessions ohne Mandantenschranke; GUC-Name passte zu keiner Policy |
| `app/nis2_incident_models.py` | `became_aware_at` als Pflichtfeld, `detected_at` optional, `NIS2DeadlineBasis` | Fristen liefen ab Erfassung statt ab Kenntniserlangung |
| `app/repositories/nis2_incidents.py` | Fristen ab Kenntniserlangung, `deadline_basis` bei Override | dito |
| `app/services/evidence_service.py` | SHA-256 beim Upload, Magic-Byte-Prüfung, `verify_evidence_integrity()` | Evidenzintegrität nicht nachweisbar; Typprüfung spoofbar |
| `app/sovereignty.py` | **neu** — Modi, Startup-Verifikation, Provider-Filter, Claim-Profil | Souveränität war Attestierung ohne technische Wirkung |
| `app/services/llm_router.py` | Sovereignty-Filter als oberste Instanz in `filter_candidates` | US-Provider blieben als Fallback in der Kette |
| `app/services/audit_trail_types.py`<br>`app/services/audit_trail_service.py` | `VVTExport` → `AuditActivityExport`, erfundene Rechtsangaben entfernt, Disclaimer | Der Export erzeugte ein Art.-30-ähnliches Dokument mit konstanter Rechtsgrundlage, konstanter Aufbewahrungsfrist und der Angabe „Row-Level-Security", die nicht aktiv ist |
| `app/main.py` | Startup-Guards (SQLite, DB-URL, Sovereignty), `GET /sovereignty/profile`, `GET /evidence/{id}/verify`, Endpunkt umbenannt mit deprecated Alias | Produktivbetrieb auf SQLite; unprüfbare Residenzaussagen |
| `app/security.py` | `require_advisor_allowlist_configured()` | Ohne Allowlist konnte jeder Inhaber eines globalen API-Keys eine beliebige `advisor_id` behaupten |
| `app/services/sbs_domain_auto_admin.py` | Produktions-Gate | Admin-Rechte an einer E-Mail-Domain |
| `app/models_db.py` | `nis2_incidents.became_aware_at`, `deadline_basis`, `evidence_files.sha256` | — |
| `.env.example` / `.env.pilot.example` | Souveränitätsmodus dokumentiert, `NEXT_PUBLIC_API_KEY`/`_TENANT_ID` entfernt | Jeder Pilot hätte seinen Mandanten-API-Key im Browser-Bundle veröffentlicht |

### Migrationen

| Migration | Inhalt |
|---|---|
| `m20260809_add_nis2_awareness_anchor.py` | `became_aware_at` + `deadline_basis`, Backfill aus `detected_at` mit Kennzeichnung `entry_fallback`. Bestehende Fristen bleiben unverändert — sie nachträglich neu zu berechnen würde den Compliance-Datensatz umschreiben |
| `m20260809_add_evidence_sha256.py` | `sha256` + Index. Altbestand bleibt `NULL`; ein Hash aus dem heutigen Dateiinhalt wäre eine Basislinie, die nichts beweist |

### Frontend

| Datei | Änderung |
|---|---|
| `components/admin/VVTExportClient.tsx` | **gelöscht** — zeigte erfundene Beispieldaten mit „Art. 30 DSGVO"-Badge und funktionslosen Download-Buttons |
| `components/admin/AuditActivityExportClient.tsx` | **neu** — Aktivitätsübersicht mit prominentem Abgrenzungshinweis |
| `app/admin/audit-log/vvt-export/` → `activity-export/` | Route umbenannt |
| `components/admin/AuditLogClient.tsx` | Verweis und Beschreibung korrigiert |

### Neue Tests

| Datei | Was abgesichert wird |
|---|---|
| `tests/test_sovereignty_mode.py` | 15 Tests: Modus-Auflösung, Provider **entfernt statt umsortiert**, Router wählt in `eu_sovereign` nie einen US-Provider (auch nicht bei maximal permissiver Mandantenpolicy), Startup-Verifikation, und: **kein Modus darf je „DSGVO-konform" autorisieren** |
| `tests/test_nis2_incidents.py` | 6 Tests: Frist ab Kenntniserlangung, 20h alter Vorfall hat ~4h Rest, 3 Tage alter Vorfall ist sofort überfällig, Pflichtfeld, Zukunftsdatum abgelehnt, `detected_at` darf vor aber nicht nach Kenntniserlangung liegen, manueller Override wird gekennzeichnet |
| `tests/test_evidence_files.py` | 5 Tests: Hash beim Upload, Manipulation der gespeicherten Datei wird als `mismatch` erkannt, Mandantenisolation der Verifikation, umbenannte ausführbare Datei mit `.pdf` abgelehnt, legitimes PNG akzeptiert |
| `tests/test_phase10_audit_trail.py` | Export darf keine erfundenen Rechtsangaben mehr enthalten, Disclaimer verpflichtend |

### Neue Dokumente

`docs/market-readiness/00` bis `13` — 14 Dokumente, ca. 4.000 Zeilen: Systeminventar,
Claim-Matrix, drei Gap-Analysen, Zielarchitektur, Refactoring-Roadmap, Ziel-Domänenmodell,
Security-Hardening-Plan, Messaging-Redlines, Website-Texte, GTM-Readiness,
Questionnaire-Pack.

---

## D. Die drei Befunde, die am meisten zählen

### 1. Der NIS2-Fristenanker

Vor dieser Änderung berechnete das Produkt alle Meldefristen ab dem Zeitpunkt der
**Dateneingabe**. Ein Vorfall, den ein Kunde am Freitagabend bemerkt und am
Montagmorgen erfasst, bekam eine Frühwarnfrist bis Dienstag — während sie real bereits
am Samstag abgelaufen war. **Das Produkt zeigte „im Fristenrahmen" an, während der
Kunde in Verzug war.**

Für ein Fristenüberwachungstool ist das der schwerstmögliche Defekt: Es erzeugt falsche
Sicherheit in genau der Situation, für die es gekauft wurde.

### 2. Der erfundene VVT-Export

`generate_vvt_export()` erzeugte ein Dokument mit dem Titel „DSGVO Art. 30
Verarbeitungsverzeichnis" aus Audit-Log-Zeilen — mit hartkodierter Rechtsgrundlage
(„Art. 6 Abs. 1 lit. c/f DSGVO"), hartkodierter Aufbewahrungsfrist („10 Jahre GoBD/AO",
obwohl kein Löschkonzept existiert) und einer TOM-Liste, die „Row-Level-Security"
auswies — eine Kontrolle, die für den Produktkern **nicht aktiv war**.

Ein Kunde hätte dieses Dokument seiner Aufsichtsbehörde vorlegen können. Die
Frontend-Seite zeigte dieselben Werte als scheinbar echte Daten.

### 3. Vercel im Klartext-Datenpfad

`frontend/src/app/api/backend/[...path]/route.ts` ist ein Catch-all-Proxy: Jede
authentifizierte Produktanfrage läuft über eine Vercel-Serverless-Funktion, die Anfrage
und Antwort im Klartext verarbeitet und die Session-Cookies terminiert. Vercel Inc. ist
US-kontrolliert; `regions: ["fra1"]` bestimmt den Ausführungsort, nicht die
Anbieterkontrolle.

Die Trust-Center-Aussage „Für die öffentliche Website wird Vercel zur Web-Auslieferung
eingesetzt" ist für den heutigen stateless Public-Release korrekt — sie wird
**unzutreffend in dem Moment, in dem das authentifizierte Produkt live geht**. Dieser
Übergang muss in den Texten mitgezogen werden.

---

## E. Wirkung dieses Change-Sets auf die Scores

| Dimension | Vorher | Nachher | Warum |
|---|---:|---:|---|
| Produktreife | 68 | 70 | Fristenlogik korrekt |
| Sicherheitsreife | 54 | 62 | Toter RLS-Pfad entfernt, fail-closed Session, Evidenz-Hash, Magic Bytes, Advisor-Allowlist, SQLite-Guard |
| DSGVO-Reife | 24 | 27 | Irreführender Art.-30-Export beseitigt |
| AI-Act-Reife | 58 | 58 | unverändert |
| NIS2-Reife | 41 | 55 | Fristenanker korrekt — der größte Einzelsprung |
| Sovereignty | 12 | 30 | Erzwungener Modus mit prüfbarem Profil-Endpunkt; Vercel bleibt im Datenpfad |
| Enterprise-Vertrieb | 22 | 26 | Zwei Fragebogenantworten wandern auf 🟢 |
| Messaging-Wahrhaftigkeit | 71 | 84 | Erfundene Rechtsangaben entfernt, Claim-Matrix als Grundlage |
| **Gesamt** | **44** | **52** | |

---

## F. Finaler Launch-Entscheid

# ⛔ NICHT MARKTREIF

**Das gilt für jede kommerzielle Nutzung mit echten Kundendaten.**

### Begründung

Der Entscheid folgt nicht aus fehlender Fachlichkeit — die ist überdurchschnittlich —
sondern aus vier Punkten, die einzeln jeweils ausreichen würden:

1. **Kein Deployment-Artefakt für das Backend.** Es gibt kein Dockerfile, keine IaC,
   keinen Deploy-Workflow. Ohne definierten Betrieb sind Datenresidenz, Backup,
   Wiederherstellung und Verfügbarkeit nicht nur unbelegt, sondern **nicht belegbar**.
   Ein Compliance-Produkt ohne nachweisbaren eigenen Betrieb ist ein Widerspruch.

2. **Kein Löschkonzept.** Ohne Aufbewahrungsfristen, Löschjob und Mandanten-Exit ist
   kein AVV mit einem professionellen Auftraggeber abschließbar. Das ist keine
   Feature-Lücke, sondern eine Vertragsunfähigkeit.

3. **Mandantentrennung ohne Nachweis.** Die applikationsseitige Filterung ist
   konsistent umgesetzt, aber bei 409 Modulen und ~250 Endpunkten ohne DB-seitige
   Schranke und ohne Negativtests ist **die Abwesenheit eines Fehlers nicht
   nachweisbar** — und genau diesen Nachweis verlangt jeder Datenschutzbeauftragte.

4. **Kein Penetrationstest.** Für ein Produkt, das die Nachweise anderer verwahrt,
   ist ein externer Sicherheitstest keine Kür.

### Was in Reichweite ist

**Nach vollständigem P0 (geschätzt 10–14 Wochen, 2–3 Entwickler):**

> ✅ **MARKTREIF FÜR PILOTKUNDEN** — mit ICP 1 (Datenschutz- und ISO-Berater), unter
> Pilotvertrag, mit ausdrücklicher Kennzeichnung als Early-Access und ohne
> Souveränitätsaussagen.

**Nach P0 + Pentest + Due-Diligence-Paket + drei Referenzen (ca. 6–9 Monate):**

> ✅ **MARKTREIF FÜR KMU IN DE/DACH** — ICP 1 bis 3 im Modus `Standard DACH`.

**Nach P1 + Modus `EU Sovereign` + ISO-27001-Vorbereitung (ca. 15–20 Monate):**

> ✅ **BEDINGT ENTERPRISE-TAUGLICH**

**ENTERPRISE-READY** setzt zusätzlich ISO-27001-Zertifizierung, SAML, BYOK,
SLA mit Pönale und belastbare Referenzen voraus — realistisch **24+ Monate**.

---

## G. Empfehlung für die nächsten 14 Tage

Maximale Wirkung pro Aufwand, überwiegend bereits begonnen:

| Tag | Maßnahme | Aufwand |
|---|---|---|
| 1–2 | Subprozessorenliste schreiben und veröffentlichen | S |
| 1–3 | AVV-Muster + TOM-Dokument entwerfen, zur Rechtsprüfung geben | M |
| 3–4 | Cross-Tenant-Negativtestsuite (P0-12) | M |
| 4–5 | TOTP-Secrets verschlüsseln (P0-9) | S |
| 5–8 | Dockerfile + docker-compose + Startup-Runbook (Beginn P0-7) | M |
| 8–12 | Retention-Regeln und Löschjob (P0-5) | L |
| 12–14 | Scheduler mit Heartbeat-Anzeige (P0-6) | M |
| laufend | Claim-Matrix in alle Texte ziehen; Produktname vereinheitlichen | S |

**Parallel, ohne Entwicklungsaufwand:**
Externen Penetrationstest beauftragen (Vorlauf 4–6 Wochen) und Rechtsberatung für
Impressum, Datenschutzerklärung, AGB und AVV mandatieren.

---

## H. Schlussbemerkung

Dieses Produkt hat ein selteneres Problem als die meisten: **Die schwierige Hälfte ist
bereits gebaut.** Die regulatorische Modellierung — Cross-Regulation-Mapping,
KI-Register mit echten Pflichtfeldern, Governance-Controls mit Evidenz und Reviews,
Workflow-Engine mit SLA — ist die Arbeit, an der die meisten GRC-Startups scheitern.
Sie ist hier vorhanden und trägt.

Was fehlt, ist die unglamouröse Hälfte: ein Dockerfile, ein Löschjob, ein Cron, ein
AVV, eine Subprozessorenliste, ein Pentest-Bericht. Nichts davon ist intellektuell
anspruchsvoll. Alles davon entscheidet über jeden einzelnen Deal.

Die Empfehlung ist deshalb nicht „mehr Features", sondern das Gegenteil: **Feature-Stopp
für ein Quartal und konsequente Abarbeitung von P0.** Der Cross-Regulation-Layer
verkauft sich nicht, solange der Einkauf keinen AVV bekommt.

Ein letzter Punkt, der über die Technik hinausgeht: Die Website ist bereits ehrlicher
formuliert als bei fast allen Wettbewerbern. Diese Haltung — offen sagen, was das
Produkt nicht kann — ist im DACH-Compliance-Markt kein Nachteil, sondern das
wirksamste Verkaufsargument, das dieses Team hat. Die veröffentlichte Claim-Matrix
wäre ein Alleinstellungsmerkmal, das kein Wettbewerber nachahmen wird, weil keiner
es sich leisten kann.
