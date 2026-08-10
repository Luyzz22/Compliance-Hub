# 07 – Refactoring-Roadmap (P0–P3)

**Priorisierungslogik**

| Stufe | Definition | Gate |
|---|---|---|
| **P0** | Blockiert jeden produktiven Rollout — Sicherheitsrisiko, falsche Funktion oder nicht führbarer Kern-Claim | Vor **jedem** zahlenden Kunden |
| **P1** | Blockiert Enterprise- und Behördenkunden | Vor dem ersten Enterprise-Deal |
| **P2** | Wettbewerbsfähigkeit, Skalierung, Prüferfreundlichkeit | Erste 6 Monate nach Launch |
| **P3** | Differenzierung, Optionalität | Opportunistisch |

Aufwandsschätzung: **S** ≤ 2 PT · **M** 3–8 PT · **L** 9–20 PT · **XL** > 20 PT.

---

# P0 — Vor jedem Rollout

## P0-1 · Mandantenisolation: Toten RLS-Pfad entfernen, echte RLS einführen

**Problem** (`01` §5, `02` A2): `TenantMiddleware` ist nicht registriert, nicht
importierbar und würde bei Aktivierung `x-tenant-id` unauthentifiziert als
RLS-Mandanten akzeptieren — ein vollständiger Cross-Tenant-Bypass. Der `SET LOCAL`
in `db_tenant.py` feuert nie und verwendet zudem eine GUC, die keine Policy prüft.

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/tenant_middleware.py` | **Löschen.** Kein Ersatz an dieser Stelle |
| `app/db_tenant.py` | `get_async_db` muss den Mandanten aus dem **authentifizierten** `AuthContext` (`request.state.auth_context`) beziehen, nicht aus `request.state.tenant_id`; GUC auf `compliancehub.tenant_id` vereinheitlichen; **fail-closed**, wenn kein Kontext vorliegt |
| `db/postgres/migrations/2026xxxx_core_tenant_rls.sql` | **Neu.** `ENABLE`/`FORCE ROW LEVEL SECURITY` + Policy für alle mandantenbezogenen Tabellen |
| `app/db.py` | Sync-Session ebenfalls mit GUC versorgen (Session-Event `after_begin`) |
| `tests/postgres/core_tenant_rls_test.sql` | **Neu.** Negativtest je Tabellengruppe |
| `.github/workflows/ci.yml` | Job `postgres-rls` um den neuen Test erweitern |

**Adressiertes Risiko:** Cross-Tenant-Datenabfluss bei einem einzigen fehlenden
`WHERE tenant_id`-Filter in 409 Modulen.
**Abgesicherter Claim:** „Mandantentrennung auch datenbankseitig durchgesetzt."
**Tests:** Negativtest je Tabelle: Session mit Mandant A darf keine Zeile von B sehen.
**Aufwand: L**

---

## P0-2 · NIS2-Fristen ab Kenntniserlangung

**Problem** (`04` §6.2): Alle Fristen und `detected_at` werden auf den
Erfassungszeitpunkt gesetzt. Das Produkt zeigt „im Fristenrahmen", während die Frist
real abgelaufen ist. **Der schwerwiegendste fachliche Defekt im gesamten Repository.**

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/nis2_incident_models.py` | `NIS2IncidentCreate`: Pflichtfeld `became_aware_at_utc: datetime`; optional `detected_at_utc`; Validator `became_aware_at <= now` |
| `app/repositories/nis2_incidents.py:79–97` | Alle drei Fristen ab `became_aware_at_utc` berechnen; `detected_at` nicht mehr überschreiben |
| `app/governance_taxonomy.py:76–81` | `FINAL_REPORT_DAYS_AFTER_REPORT` → Ankerung an tatsächlicher Meldung, mit dokumentiertem Default; „ein Monat" als Kalendermonat |
| `app/models_db.py` (`nis2_incidents`) | Spalte `became_aware_at` NOT NULL; `deadline_basis` (`awareness \| entry_fallback`) für Altdaten |
| `app/db_migrations/migrations/m2026xxxx_nis2_awareness_anchor.py` | **Neu.** Backfill: `became_aware_at = detected_at`, `deadline_basis='entry_fallback'` |
| Frontend NIS2-Incident-Formular | Pflichtfeld + Hinweistext + Warnbanner bei Rückdatierung > 24 h |

**Adressiertes Risiko:** Falsche Fristenanzeige → Fristversäumnis beim Kunden →
Bußgeld und Haftung; Reputationsschaden für das Produkt.
**Abgesicherter Claim:** „Fristenberechnung ab Kenntniserlangung."
**Tests:** Vorfall mit `became_aware_at = now - 20h` → Frühwarnfrist in 4 h, Status
„kritisch"; Rückdatierung > 24 h → bereits überfällig.
**Aufwand: M**

---

## P0-3 · Souveränitätsmodus erzwingen (statt attestieren)

**Problem** (`05` §14): US-LLM-Provider bleiben in der Fallback-Kette; EU-Residenz ist
eine ENV-Attestierung ohne technische Wirkung.

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/sovereignty.py` | **Neu.** Enum `SovereigntyMode`, Vendor-Allowlist je Modus, `verify_startup_configuration()` |
| `app/main.py` (lifespan) | Startup-Verifikation aufrufen; bei Verstoß **Prozessabbruch**, nicht Warnung |
| `app/services/llm_router.py` | Provider-Kette **filtern**, nicht sortieren: `chain = [p for p in chain if p in mode.allowed_llm_providers]`; leere Kette → sauberer Fehler statt US-Fallback |
| `app/main.py` | Endpunkt `GET /api/v1/sovereignty/profile` (Modus, erlaubte Vendoren, freigegebene Claims, Restrisiken) |
| `frontend/src/app/trust-center/page.tsx` | Modus + Vendor-Liste aus dem Endpunkt rendern statt statischem Text |
| `.env.example` | `COMPLIANCEHUB_SOVEREIGNTY_MODE=standard_dach` |

**Adressiertes Risiko:** Prompt-Inhalte gelangen unbeabsichtigt zu US-Anbietern;
Souveränitäts-Claims ohne technische Grundlage.
**Abgesicherter Claim:** „KI-Verarbeitung ausschließlich über EU-Anbieter" — dann
technisch erzwungen und über den Endpunkt prüfbar.
**Tests:** Modus `eu_sovereign` + `OPENAI` konfiguriert → Startup schlägt fehl;
Router liefert in `eu_sovereign` niemals einen US-Provider.
**Aufwand: M**

---

## P0-4 · Evidenzintegrität: Hash, Magic Bytes, Malware-Scan

**Problem** (`01` §10, `02` E3): `evidence_files` hat keine Hash-Spalte; Typprüfung
nur über Header/Extension (spoofbar); kein Malware-Scan.

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/models_db.py` (`evidence_files`) | `sha256: String(64) NOT NULL`, `scan_status` (`pending\|clean\|infected\|skipped`), `scanned_at`, `data_classification` |
| `app/services/evidence_service.py` | SHA-256 beim Upload berechnen und speichern; Magic-Byte-Prüfung gegen die Allowlist; Scanner-Hook vor `storage.store_file` |
| `app/services/evidence_malware_scan.py` | **Neu.** Protokoll + `NoopScanner` (Dev) + `ClamAVScanner` (ICAP/clamd); `COMPLIANCEHUB_EVIDENCE_SCANNER` |
| `app/services/evidence_storage.py` | `AzureBlobEvidenceStorage` bzw. `S3EvidenceStorage` ergänzen; Backend über ENV wählbar |
| `app/main.py` (Evidence-Endpunkte) | `GET /evidence/{id}/verify` — Hash neu berechnen und vergleichen |
| Migration | **Neu.** Spalten + Backfill (`sha256` aus vorhandenen Dateien) |

**Adressiertes Risiko:** Unerkannte Verfälschung von Nachweisdateien; Malware-Verteilung
über die Plattform an andere Nutzer desselben Mandanten.
**Abgesicherter Claim:** „Evidenzintegrität durch Inhalts-Hash mit Verifikation";
„Uploads werden auf Schadsoftware geprüft."
**Tests:** Upload → Hash gespeichert; manipulierte Datei → `verify` schlägt fehl;
EICAR-Testdatei → abgelehnt; PDF-Header mit `.pdf`-Endung auf ausführbarem Inhalt → abgelehnt.
**Aufwand: M**

---

## P0-5 · Retention, Löschkonzept, Mandanten-Exit

**Problem** (`05` §6): Kein Retention-Feld, kein Löschjob, keine Mandantenlöschung,
kein Gesamtexport. Blockiert jeden AVV.

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/models_db.py` | Neue Tabellen `retention_rules`, `legal_holds`, `data_deletion_audit` (Metadaten ohne Nutzdaten, analog `runtime_state_deletion_audit`) |
| `app/services/retention_service.py` | **Neu.** Regelauswertung, Legal-Hold-Prüfung, Löschen/Anonymisieren/Archivieren |
| `app/audit_append_only.py` | Kontrollierter Ausnahmepfad: Löschung nur über einen explizit gesetzten Systemkontext, mit Pflicht-Audit-Eintrag |
| `app/services/tenant_lifecycle_service.py` | **Neu.** `export_tenant()` (vollständiges ZIP/JSON) und `delete_tenant()` (Karenzzeit → Löschung → Bestätigungsprotokoll) |
| `app/main.py` | Endpunkte `POST /tenants/{id}/export`, `POST /tenants/{id}/deletion-request`, `GET /retention/rules` |
| `app/services/health_monitor.py` | Retention-Lauf in den Scheduler (P0-6) einhängen |
| `app/config/retention_defaults.py` | **Neu.** Defaults je Kategorie mit Rechtsgrundlage (z. B. Audit-Logs 10 Jahre nach § 147 AO; Sessions 90 Tage; Runtime-Events 12 Monate) |

**Adressiertes Risiko:** Verstoß gegen Art. 5(1)(e); nicht abschließbarer AVV;
unbegrenztes Datenwachstum.
**Abgesicherter Claim:** „Konfigurierbare Aufbewahrungsfristen mit Legal-Hold";
„Vollständiger Datenexport und gesicherte Löschung bei Vertragsende."
**Tests:** Regel greift nach Ablauf; Legal Hold verhindert Löschung; Löschung erzeugt
Metadaten-Nachweis; Export enthält alle mandantenbezogenen Tabellen.
**Aufwand: L**

---

## P0-6 · Scheduler mit nachweisbarem Heartbeat

**Problem** (`01` §11, `04` §6.4): Kein In-Process-Scheduler; der TODO in
`health_monitor.py:219` ist offen. Fristenüberwachung läuft nur bei externer
Einrichtung — für den Kunden nicht erkennbar.

**Änderungen**

| Datei | Aktion |
|---|---|
| `pyproject.toml` | `apscheduler>=3.10` |
| `app/scheduler.py` | **Neu.** Jobs: Fristenprüfung, Eskalation, Reminder, Retention, Health-Poll; Leader-Election über DB-Advisory-Lock (mehrere Instanzen) |
| `app/main.py` (lifespan) | Scheduler starten/stoppen; `COMPLIANCEHUB_SCHEDULER_ENABLED` |
| `app/models_db.py` | `scheduled_job_runs`: `job_name`, `started_at`, `finished_at`, `status`, `items_processed`, `error` |
| `app/main.py` | `GET /api/v1/system/scheduler-status` — letzter Lauf je Job |
| Frontend Dashboard | Banner „Fristenprüfung zuletzt gelaufen: …" bzw. Warnung bei Ausbleiben |
| `app/services/health_monitor.py:219` | TODO auflösen |

**Adressiertes Risiko:** Stillschweigend nicht laufende Fristenüberwachung — der
Kunde verlässt sich auf ein Versprechen, das nicht eingelöst wird.
**Abgesicherter Claim:** „Automatische Fristen- und Eskalationsprüfung."
**Tests:** Job registriert; Lauf erzeugt `scheduled_job_runs`-Eintrag; zwei Instanzen
führen den Job nur einmal aus.
**Aufwand: M**

---

## P0-7 · Deployment-Artefakt und Betriebsgrundlage

**Problem** (`01` §12): Kein Dockerfile, keine IaC, kein Backend-Deployment. Damit sind
alle Hosting-, Residenz-, DR- und Verfügbarkeitsaussagen unbelegbar.

**Änderungen**

| Datei | Aktion |
|---|---|
| `Dockerfile` | **Neu.** Multi-Stage, non-root, Distroless/Slim, Healthcheck |
| `frontend/Dockerfile` | **Neu.** Next.js `output: "standalone"` (Voraussetzung für Modus 2) |
| `docker-compose.yml` | **Neu.** Lokale Vollumgebung: API, Frontend, Postgres, MinIO, n8n, OPA |
| `infra/azure/main.bicep` | **Neu.** Container Apps, PostgreSQL Flexible Server, Blob, Key Vault, Private Endpoints, Diagnostic Settings |
| `.github/workflows/deploy.yml` | **Neu.** Build → Scan (Trivy) → Sign (cosign) → Deploy Staging → Smoke → Prod |
| `docs/operations/runbook.md` | **Neu.** Betrieb, Restore, Incident-Response, Kontakte |
| `docs/operations/dr-plan.md` | **Neu.** RPO/RTO, Restore-Testprotokoll |
| `app/db.py:11` | **Startup-Guard:** in `prod` muss `COMPLIANCEHUB_DB_URL` gesetzt und nicht-SQLite sein |

**Adressiertes Risiko:** Produktivbetrieb auf einer SQLite-Datei; kein
Wiederherstellungspfad; keine belegbare Datenresidenz.
**Abgesicherter Claim:** „Betrieb in EU-Rechenzentren"; „dokumentierte Backup- und
Wiederherstellungsverfahren."
**Tests:** Compose-Stack startet und besteht die Smoke-Tests; Startup-Guard bricht
bei SQLite in `prod` ab.
**Aufwand: XL**

---

## P0-8 · Rechtsartefakte: AVV, TOM, Subprozessoren

**Problem** (`05` §5, §8): Kein AVV-Muster, kein TOM-Dokument, keine vollständige
Subprozessorenliste. Kein professioneller Einkauf schließt ohne diese ab.

**Änderungen** (reine Dokumentation, kein Code)

| Datei | Inhalt |
|---|---|
| `docs/legal/dpa-template.md` | AVV nach Art. 28 mit Anlagen |
| `docs/legal/dpa-annex-1-processing.md` | Verarbeitungsübersicht: Zwecke, Kategorien, Betroffene, Dauer |
| `docs/legal/dpa-annex-2-toms.md` | TOM nach Art. 32, abgeleitet aus dem Code |
| `docs/legal/subprocessors.md` | Liste mit Name, Sitz, Rolle, Zweck, Datenkategorien, Rechtsgrundlage, Stand |
| `docs/legal/transfer-impact-assessment.md` | TIA für Vercel und Microsoft |
| `frontend/src/app/trust-center/` | Downloadbereich (NDA-geschützt für sensible Artefakte) |

**Wichtig:** Diese Dokumente sind **von einer qualifizierten Rechtsberatung zu prüfen**,
bevor sie herausgegeben werden. Das Repository liefert Entwurf und Faktenbasis, nicht
die rechtliche Freigabe.
**Aufwand: M** (plus externe Prüfung)

---

## P0-9 · TOTP-Secrets verschlüsseln

**Problem** (`01` §6, `05` §10): `mfa_factors` speichert TOTP-Secrets ohne erkennbare
Verschlüsselung. Ein DB-Dump kompromittiert alle zweiten Faktoren.

**Änderungen**

| Datei | Aktion |
|---|---|
| `app/security_credentials.py` | Envelope-Encryption (AES-GCM) mit `COMPLIANCEHUB_CREDENTIAL_ENCRYPTION_KEY` / Key Vault |
| `app/services/enterprise_governance_service.py:196–220` | Verschlüsselt schreiben, beim Verifizieren entschlüsseln |
| `app/models_db.py` (`mfa_factors`) | `secret_encrypted`, `key_id`; Altspalte nach Migration entfernen |
| Migration | Bestehende Secrets verschlüsseln |

Gleiches Muster anschließend für `identity_providers` (Client Secrets) prüfen.
**Aufwand: S**

---

## P0-10 · Fehlbezeichnung „VVT" beseitigen

**Problem** (`05` §2): `VVTExport` in `app/services/audit_trail_service.py` exportiert
Audit-Log-Zeilen, heißt aber wie ein Verzeichnis der Verarbeitungstätigkeiten nach
Art. 30. Ein Kunde könnte das der Aufsicht vorlegen.

**Änderungen:** Umbenennen in `AuditActivityExport` in
`app/services/audit_trail_types.py` und `audit_trail_service.py`, Endpunkt und
UI-Label anpassen, Hinweistext ergänzen: „Dies ist ein Aktivitätsprotokoll, kein
Verzeichnis von Verarbeitungstätigkeiten nach Art. 30 DSGVO."
**Aufwand: S** — höchstes Nutzen-Aufwand-Verhältnis im gesamten P0-Block.

---

## P0-11 · `NEXT_PUBLIC_API_KEY` aus allen Vorlagen entfernen

**Problem** (`01` §2): `.env.pilot.example` liefert `NEXT_PUBLIC_API_KEY` und
`NEXT_PUBLIC_TENANT_ID`. Jeder Pilot, der die Vorlage kopiert, veröffentlicht seinen
Mandanten-API-Key im Browser-Bundle.

**Änderungen:** Beide Zeilen aus `.env.pilot.example` entfernen, durch Kommentar mit
Verweis auf den BFF-Pfad ersetzen; `frontend/scripts/verify-enterprise-readiness.mjs`
um eine Prüfung erweitern, die **jede** `NEXT_PUBLIC_*`-Variable mit
Credential-Semantik (`KEY`, `SECRET`, `TOKEN`, `PASSWORD`) im Build ablehnt.
**Aufwand: S**

---

## P0-12 · Cross-Tenant-Negativtestsuite

**Problem** (`05` §9): 178 Testdateien, aber keine systematischen
Cross-Tenant-Negativtests. Der zentrale Nachweis der Mandantentrennung fehlt.

**Änderungen**

| Datei | Aktion |
|---|---|
| `tests/security/test_cross_tenant_isolation.py` | **Neu.** Parametrisiert über alle Endpunkte: Mandant A authentifiziert, Ressourcen-ID von B → 403/404, nie 200 |
| `tests/security/test_advisor_authorization.py` | **Neu.** Advisor-Pfad: fremde `advisor_id`, fremde Mandanten, fehlende Allowlist |
| `tests/security/test_api_key_boundary.py` | **Neu.** Globale Keys in `prod` deaktiviert; Key von Mandant A gegen B → 401 |
| `.github/workflows/ci.yml` | Eigener Job `security-tests`, der bei Fehlschlag hart blockiert |

**Aufwand: M** — dieser Test **ist** der verkaufbare Nachweis. Sein Bestehen gehört
ins Trust Center.

---

# P1 — Vor dem ersten Enterprise-Kunden

| ID | Maßnahme | Betroffene Artefakte | Aufwand |
|---|---|---|---|
| **P1-1** | **DSGVO-Domäne:** `data_processing_activities` (ROPA), `data_categories`, `legal_bases`, `transfer_records`, `tia_assessments`, `dpa_records` | `app/models_db.py`, `app/services/privacy_service.py` (neu), Frontend `/tenant/privacy/*` | L |
| **P1-2** | **Supplier/Subprocessor-Register** — bedient NIS2 Art. 21(2)(d), DSGVO Art. 28 und die Subprozessorenliste in einem Modell | `app/models_db.py` (`suppliers`, `supplier_assessments`), `app/services/supplier_service.py` (neu), ersetzt `ai_systems.has_supplier_risk_register` | L |
| **P1-3** | **AI-Act-Rollenmodell:** Enum `ai_actor_role`, n:m `ai_system_actor_roles`, Art.-25-Rollenwechsel, abgeleitete Pflichtenliste | `app/models_db.py`, `app/services/classification_engine.py`, `app/grc/framework_mapping.py` | M |
| **P1-4** | **AI-Literacy-Register (Art. 4)** + Abdeckungs-KPI im Board-Report | `app/models_db.py` (`ai_literacy_records`), `app/services/ai_literacy_service.py` (neu), Board-KPI | M |
| **P1-5** | **`regulatory_notifications`** — generische Meldungsentität für NIS2 Art. 23, AI Act Art. 73, DSGVO Art. 33/34 mit Einreichzeitpunkt, Behörde, Aktenzeichen, Inhalts-Snapshot | `app/models_db.py`, `app/repositories/nis2_incidents.py`, neuer Router | M |
| **P1-6** | **Geschäftsleitungs-Billigung** (`management_body_approvals`) + Scope-Assessment (`nis2_scope_assessments`); `tenants.nis2_scope`-Default auf `assessment_required`, Fallback in `advisor_portfolio_priority.py:201` entfernen | `app/models_db.py`, `app/services/advisor_portfolio_priority.py` | M |
| **P1-7** | **Rate Limiting + Idempotency-Keys** für alle schreibenden Endpunkte | `app/rate_limit.py` (neu), `app/main.py` | M |
| **P1-8** | **DSAR-Workflow** + technischer „Alle Daten zu Nutzer X"-Export | `app/models_db.py` (`dsar_requests`), `app/services/dsar_service.py` (neu) | M |
| **P1-9** | **TOM-Dokument** aus dem Code ableiten und im Trust Center bereitstellen | `docs/legal/dpa-annex-2-toms.md` | S |
| **P1-10** | **Support-Zugriffsmodell:** Break-Glass mit Ticketbezug, Zeitfenster und für den Kunden sichtbarem Log | `app/services/support_access_service.py` (neu), nutzt vorhandene `privileged_action_events` und `approval_requests` | M |
| **P1-11** | **Risikoregister** `risks` + `risk_treatments` — bedient NIS2 Art. 21(1), ISO 27001 6.1/8.2/8.3, ISO 42001 zugleich | `app/models_db.py`, `app/services/risk_service.py` (neu) | L |
| **P1-12** | **Human-Oversight-Entität** (Art. 14) mit Verantwortlichem, Übersteuerungs-/Stopp-Befugnis, Wirksamkeitsreview | `app/models_db.py`, `app/services/human_oversight_service.py` (neu) | M |
| **P1-13** | **Klassifizierungs-Bestätigung:** `classification_status`, `confirmed_by_user_id`, `confirmed_at`, `confirmation_rationale` — der Nachweis, dass ein Mensch die Einstufung verantwortet | `app/models_db.py` (`ai_systems`, `risk_classifications`), `classification_engine.py` | S |
| **P1-14** | **Versionierung `ai_act_docs`** + Freigabestatus + Verknüpfung zu Evidenzdateien | `app/models_db.py`, `app/services/ai_act_docs.py` | M |
| **P1-15** | **SAML 2.0** als zweiter SSO-Pfad | `app/services/saml_service.py` (neu) | L |
| **P1-16** | **Externer Zeitstempel für die Audit-Kette** (RFC 3161) — periodischer Anchor-Digest | `app/services/audit_anchor_service.py` (neu) | M |
| **P1-17** | **`main.py` aufteilen** — mindestens Auth, AI-Act, NIS2, Evidence, Admin, Billing in eigene Router; Ziel < 500 Zeilen | `app/main.py` → `app/routers/*` | L |
| **P1-18** | **Penetrationstest** durch einen externen Anbieter, Bericht als Trust-Center-Artefakt | extern | — |

---

# P2 — Erste 6 Monate

| ID | Maßnahme | Aufwand |
|---|---|---|
| P2-1 | Asset-Register (NIS2 Art. 21(2)(i), ISO 27001 A.5.9) | M |
| P2-2 | `control_nature` (technisch/organisatorisch/physisch/personell), `control_type`, `automation_level` | S |
| P2-3 | Legal Entity / Jurisdiction unterhalb des Mandanten (Konzernstrukturen) | M |
| P2-4 | `ai_models` + `ai_providers` als eigene Entitäten inkl. GPAI-Kennzeichnung | M |
| P2-5 | NIS2-Registrierungsobjekt (BSI) | S |
| P2-6 | Alembic einführen und die 103 Tabellen unter versionierte Migrationen bringen | L |
| P2-7 | Feldbasierte Allowlist für `audit_logs.before/after` statt Voll-Serialisierung | M |
| P2-8 | SBOM (CycloneDX) im Build + Artefakt-Signierung (cosign) | S |
| P2-9 | Trust Center: automatisierte Statusseite mit Uptime, letztem Restore-Test, Pentest-Datum | M |
| P2-10 | BYOK-Readiness (Schlüsselabstraktion für Modus 2/3) | L |
| P2-11 | Datenexport im Standardformat (OSCAL o. ä.) für GRC-Toolwechsel | M |
| P2-12 | ISO-27001-Zertifizierung des eigenen Betriebs vorbereiten | XL |

---

# P3 — Optional / Differenzierung

| ID | Maßnahme |
|---|---|
| P3-1 | Modus `Strict Sovereign` als Single-Tenant-Produkt inkl. Offline-Build-Kette |
| P3-2 | Self-hosted-Inferenz (vLLM/Ollama) als unterstützter Provider |
| P3-3 | Öffentliche API mit OpenAPI-Client-SDKs für MSP-Automatisierung |
| P3-4 | Mandantenübergreifendes Benchmarking (anonymisiert, opt-in) |
| P3-5 | Behördenschnittstellen (BSI-Meldeportal, EU-Datenbank Art. 49), sobald verfügbar |
| P3-6 | White-Label für MSP/Kanzleien |
| P3-7 | Mobile App für Freigaben und Eskalationen |

---

# Kritischer Pfad bis „Marktreif für KMU in DE/DACH"

```
P0-11 ──┐
P0-10 ──┼── (je ≤ 2 PT, sofort)
P0-9  ──┘
        │
P0-2 ───┼── NIS2-Fristenanker   ─┐
P0-3 ───┼── Souveränitätsmodus   ├── Kern-Claims wieder führbar
P0-4 ───┼── Evidenzintegrität    │
P0-12 ──┴── Cross-Tenant-Tests  ─┘
        │
P0-6 ─── Scheduler ──┐
P0-5 ─── Retention  ─┼── AVV-Fähigkeit
P0-8 ─── Rechtsdocs ─┘
        │
P0-7 ─── Deployment + IaC ──┐
P0-1 ─── Postgres-RLS ──────┴── Betriebsnachweise
```

**Geschätzte Gesamtdauer P0:** 10–14 Wochen für ein Team von 2–3 Entwicklern,
zuzüglich externer Rechtsprüfung (parallel) und Penetrationstest (nach P0-7).

**Empfohlene Reihenfolge der ersten zwei Wochen** (maximaler Claim-Gewinn pro Aufwand):
P0-11 → P0-10 → P0-9 → P0-2 → P0-3. Danach ist die 🔴-Liste in
`02-claim-vs-proof-matrix.md` bereits um ein Drittel kürzer.
