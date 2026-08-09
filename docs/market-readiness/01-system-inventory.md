# 01 – System Inventory (Ist-Stand)

**Reviewdatum:** 2026-08-09
**Reviewgegenstand:** Repository `Luyzz22/Compliance-Hub`, Branch `main` @ `485c99c`
**Rolle des Reviews:** Enterprise- und Regulatorik-Readiness-Review vor Markteintritt DACH
**Reviewtiefe:** Statische Codeanalyse. Kein Zugriff auf Produktivumgebung, Azure-Tenant,
Verträge, Subprozessorenliste oder Betriebsdokumentation.

## Legende Belegstufen

| Marker | Bedeutung |
|---|---|
| **BELEGT IM CODE** | Im Repository verifizierbar, Datei/Zeile benannt |
| **PLAUSIBLE ANNAHME** | Aus Code/Doku ableitbar, aber nicht vollständig verifiziert |
| **OFFENE LÜCKE** | Nicht vorhanden, kein Blocker für Pilot, aber vor Enterprise nötig |
| **KRITISCHER BLOCKER** | Verhindert wahrheitsgemäße Produkt-Claims oder ist Sicherheits-/Rechtsrisiko |

---

## 1. Grobarchitektur

**BELEGT IM CODE.**

```
┌──────────────────────────────────────────────────────────────────┐
│ Next.js 16 App Router (frontend/)  ──  Vercel, region fra1       │
│  • Public Site (Marketing, Trust Center, Legal)                  │
│  • Authenticated Product UI (board/, tenant/, advisor/, admin/)  │
│  • Route-Guard + CSP: frontend/src/proxy.ts (Next-Middleware)    │
│  • BFF: app/api/backend/[...path]/route.ts (Catch-all → FastAPI) │
│    + 47 weitere Server-Routes (Auth, Admin, Advisor, Export)     │
│  • Server-seitige Postgres-Zugriffe: lib/advisorRuntimePostgres* │
│  • Azure Blob/Identity SDKs im Frontend-Dependency-Baum          │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTP (x-api-key / Bearer-Session / x-tenant-id)
┌───────────────▼──────────────────────────────────────────────────┐
│ FastAPI-Monolith (app/) — app/main.py: 10.092 LOC, 409 Module    │
│  Middlewares: Telemetry → SecurityHeaders → TrustedHost → CORS   │
│  9 ausgelagerte Router + ~250 Endpunkte direkt in main.py        │
└───────────────┬──────────────────────────────────────────────────┘
                │ SQLAlchemy 2.0 (sync) + async (aiosqlite/asyncpg)
┌───────────────▼──────────────────────────────────────────────────┐
│ DB: Default SQLite (!), optional PostgreSQL                      │
│  103 ORM-Tabellen (app/models_db.py, 2.601 LOC)                  │
│  Schema-Erzeugung: Base.metadata.create_all + additive Migrationen│
└──────────────────────────────────────────────────────────────────┘
        │              │                │              │
   Evidence-FS    Temporal        OPA (Rego)        LLM-Router
   (lokal!)       (optional)      (optional)        (5 Provider)
```

**Bewertung:** Die Architektur ist ein klassischer FastAPI-Monolith mit Next.js-BFF.
Das ist für die Zielgröße vertretbar. Problematisch sind nicht der Stil, sondern die
fehlenden Betriebsartefakte (siehe §12) und der Default-Datastore (§4).

---

## 2. Frontend-Stack

**BELEGT IM CODE** (`frontend/package.json`, `frontend/next.config.ts`, `frontend/vercel.json`):

| Element | Ist-Stand |
|---|---|
| Framework | Next.js 16.2.10, React 19.2.7, App Router |
| Sprache | TypeScript 5, 480 `.ts`/`.tsx`-Dateien |
| Styling | Tailwind CSS 4, eigene Design-Tokens (`public/static/css`) |
| Tests | Vitest 3.2.6 + Testing Library, `npm run test:unit` in CI |
| Deployment | Vercel, `regions: ["fra1"]` |
| Security-Header | `next.config.ts`: HSTS (nur prod), X-Frame-Options DENY, COOP/CORP, Permissions-Policy, `poweredByHeader: false` |
| CSP | Nonce-basiert, `scripts/verify-csp.mjs` als **prebuild-Gate** |
| Release-Gates | `scripts/verify-enterprise-readiness.mjs`, `verify-runtime-storage.mjs` laufen im `prebuild` |
| Session | `lib/serverSession.ts`: HttpOnly-Session-Cookie + separates, nicht-HttpOnly CSRF-Cookie (Double-Submit) |
| SSO-Flow | `app/api/auth/entra/start|callback` mit HttpOnly-Transaktions-Cookie |

**Positiv hervorzuheben:** Die `prebuild`-Verifier sind ein echtes, wirksames Anti-Regressions-Mittel.
Ein Produktions-Build schlägt fehl, wenn Legal-, Auth-, Host- oder Datenschutz-Konfiguration
fehlt. Das ist überdurchschnittlich für ein Produkt dieser Reifestufe.

**KRITISCHER BLOCKER — Browser-Credentials:**
`.env.pilot.example` liefert weiterhin
`NEXT_PUBLIC_API_KEY=pilot-demo-key` und `NEXT_PUBLIC_TENANT_ID=tenant-overview-001`.
Ein `NEXT_PUBLIC_*`-API-Key ist ein im Browser-Bundle ausgelieferter Mandanten-Credential.
Solange dieses Muster im Repo als Vorlage existiert, ist die Aussage „keine Client-Credentials"
nicht belastbar, und jeder Pilot, der die Vorlage kopiert, veröffentlicht seinen API-Key.

---

## 3. Backend-Stack

**BELEGT IM CODE** (`pyproject.toml`, `app/`):

| Element | Ist-Stand |
|---|---|
| Runtime | Python ≥ 3.11, FastAPI ≥ 0.115, Uvicorn |
| ORM | SQLAlchemy 2.0 (sync `app/db.py` + async `app/db_tenant.py`) |
| Validierung | Pydantic v2 |
| Auth-Krypto | `argon2-cffi` (Passwörter), `PyJWT[crypto]`, `cryptography` (Signaturen) |
| Observability | OpenTelemetry API/SDK, `app/telemetry/` |
| Workflow | `temporalio` ≥ 1.8 (`app/workflows/`) |
| Agents | `langgraph` ≥ 1.0 (`app/agents/langgraph/oami_explain_poc.py`) |
| RAG | `haystack-ai` 2.x, optional `rank-bm25`, `sentence-transformers` |
| Cloud-SDK | `azure-identity` (Managed Identity für Azure OpenAI) |
| Parser-Härtung | `defusedxml`, `app/xml_security.py` |
| Lint | ruff (E,F,I,UP), line-length 100 |

**OFFENE LÜCKE — Monolithgröße:** `app/main.py` mit 10.092 Zeilen ist der zentrale
Wartbarkeits- und Review-Blocker. Enterprise-Security-Reviews prüfen Endpunkt-für-Endpunkt
die Autorisierung; eine 10k-Zeilen-Datei macht diesen Nachweis teuer und fehleranfällig.
Nur 9 von geschätzt ~250 Endpunktgruppen sind in eigene Router ausgelagert.

---

## 4. Datenbankmodell und Datenhaltung

**BELEGT IM CODE** (`app/db.py`, `app/models_db.py`):

- 103 ORM-Tabellen.
- **Default-URL: `sqlite+pysqlite:///./test_compliancehub.db`** (`app/db.py:11`).
- Schema-Erzeugung über `Base.metadata.create_all` plus ein eigener additiver
  Migrationsrunner (`app/db_migrations/`) mit Schema-Tracking. **Kein Alembic.**
- PostgreSQL-spezifisches DDL existiert nur für **zwei** Advisor-Tabellen
  (`db/postgres/migrations/20260715_advisor_runtime_state_rls.sql`).

**KRITISCHER BLOCKER — SQLite als Default:**
Ein mandantenfähiges GRC-SaaS darf nicht auf einen Datastore defaulten, der keine
Row-Level-Security, keine Nebenläufigkeit auf Schreibpfaden, kein PITR und kein
rollenbasiertes DB-Berechtigungsmodell bietet. Solange `COMPLIANCEHUB_DB_URL` nicht
gesetzt ist, läuft die gesamte Plattform gegen eine Datei namens `test_compliancehub.db`.
Es gibt **keinen Startup-Check**, der das in Produktion verhindert.

**KRITISCHER BLOCKER — kein additiver Migrationspfad für Postgres-DDL:**
`create_all` erzeugt Tabellen, ändert aber keine bestehenden. Der eigene Runner
(`app/db_migrations/migrations/`) enthält aktuell **zwei fachliche Migrationen**.
Für 103 Tabellen ist das kein tragfähiges Schema-Evolutionsmodell für Enterprise-Betrieb
mit Datenerhalt.

### Tabellenlandschaft (Auszug nach Domäne)

| Domäne | Tabellen (Auswahl) |
|---|---|
| Mandant/Identität | `tenants`, `users`, `user_tenant_roles`, `user_sessions`, `identity_providers`, `external_identities`, `scim_sync_state`, `mfa_factors`, `mfa_backup_codes`, `tenant_api_keys` |
| Governance/IAM | `access_reviews`, `sod_policies`, `approval_requests`, `privileged_action_events` |
| AI Act | `ai_systems`, `ai_system_inventory_profiles`, `ai_register_entries`, `risk_classifications`, `ai_act_docs`, `ai_transparency_assessments`, `ai_transparency_controls`, `ai_runtime_events`, `ai_runtime_incident_summaries` |
| GRC-Kern | `compliance_frameworks`, `compliance_requirements`, `compliance_controls`, `compliance_requirement_control_links`, `governance_requirements`, `governance_controls`, `governance_control_evidence`, `governance_control_reviews` |
| NIS2 | `nis2_incidents`, `nis2_kritis_kpis`, `incidents`, `service_health_incidents` |
| Workflow | `governance_workflow_templates|runs|tasks|task_history`, `remediation_actions` (+ 7 Satelliten) |
| Evidenz/Audit | `audit_logs`, `evidence_files`, `evidence_bundles`, `trust_center_assets`, `trust_center_access_logs`, `audit_alerts` |
| Board/Report | `board_reports`, `board_report_snapshots|items|actions|metric_history`, `ai_compliance_board_reports` |
| Billing | `subscription_plans`, `subscriptions`, `billing_events` |
| Export | `datev_export_logs`, `xrechnung_exports`, `report_exports` |

**Bewertung:** Die Breite des Modells ist für ein Produkt dieser Größe **beeindruckend**
und deutlich über dem, was typische AI-Act-Tools bieten. Die Lücken sind spezifisch
und in `08-target-domain-model.md` katalogisiert (fehlend u. a.: Legal Entity,
Supplier/Subprocessor, Transfer Record/TIA, DPA, Data Processing Activity/ROPA,
Retention Rule, Risk/Risk Treatment als eigene Entitäten, AI-Literacy-Records).

---

## 5. Multi-Tenant-Modell

**BELEGT IM CODE:**

- **Isolationsmodell:** Shared Database, Shared Schema, `tenant_id`-Spalte auf praktisch
  jeder Tabelle, Filterung **ausschließlich in der Applikationsschicht**
  (`WHERE tenant_id = :tenant_id` in `app/repositories/*`).
- **Mandantenauflösung:** `app/auth_dependencies.py::_resolve_request_auth_context`
  – entweder Bearer-Session (Mandant aus der Session, `x-tenant-id` muss übereinstimmen,
  sonst 403) oder `x-api-key` + `x-tenant-id` gegen `tenant_api_keys` (Hash-Verifikation).
- **Globale Keys:** `COMPLIANCEHUB_API_KEYS` erlaubt einen Key für *beliebige* Mandanten.
  In `prod`/`production` standardmäßig deaktiviert (`_global_api_keys_allowed`), per
  `COMPLIANCEHUB_ALLOW_GLOBAL_API_KEYS=true` reaktivierbar.
- **Pfad-Konsistenz:** `require_path_tenant_matches_auth()` existiert als Guard.

**KRITISCHER BLOCKER — RLS wird beworben, ist aber nicht wirksam:**

Drei zusammenhängende Defekte:

1. `app/db_tenant.py:49` setzt `SET LOCAL app.current_tenant` aus
   `request.state.tenant_id`.
2. `request.state.tenant_id` wird **ausschließlich** von
   `app/tenant_middleware.py::TenantMiddleware` gesetzt.
3. `TenantMiddleware` wird **nirgends registriert** (`grep -rn "TenantMiddleware"` findet
   nur die Definition; `app/main.py:613–628` registriert Telemetry, SecurityHeaders,
   TrustedHost, CORS — nicht TenantMiddleware). Die Klasse ist zudem **nicht importierbar**:
   `from .config import settings` verweist auf `app/config/`, ein Verzeichnis **ohne
   `__init__.py` und ohne `settings`-Objekt**.

Folge: Der `SET LOCAL`-Zweig läuft nie. Alle `get_async_db`-Endpunkte
(`governance_workflow_routes.py`, `remediation_actions_routes.py`) haben **keinerlei
DB-seitige Mandantenschranke**. Zusätzlich verwendet der Code die GUC `app.current_tenant`,
während das einzige real existierende RLS-Policy-Set die GUC `compliancehub.tenant_id`
prüft — die Namen passen nicht zueinander.

**Zusätzlich KRITISCH:** Hätte man `TenantMiddleware` registriert, wäre es *schlimmer*:
Zeile 47–49 akzeptiert `x-tenant-id` als **unauthentifizierten Fallback** für die
RLS-Mandantenwahl. Das ist ein vollständiger Cross-Tenant-Bypass. Die Klasse muss
gelöscht, nicht aktiviert werden.

**Bewertung des Claims „Mandantenfähigkeit":** Der Claim ist auf Applikationsebene
belegbar. Der Claim „Row-Level-Security" / „DB-seitige Mandantentrennung" ist für
den Produktkern **nicht marktreif belegbar**. Er trifft ausschließlich auf zwei
Advisor-Tabellen im Schema `compliancehub_private` zu.

---

## 6. Auth, SSO, Rollenmodell

**BELEGT IM CODE:**

| Fähigkeit | Ist-Stand | Bewertung |
|---|---|---|
| Passwort-Login | Argon2id (`app/services/identity_service.py`), Legacy-SHA256-Rehash beim Login | Solide |
| Session | `user_sessions`-Tabelle, opake Tokens, TTL `COMPLIANCEHUB_SESSION_TTL_MINUTES` (Default 480 min), Revokation über `logout` | Solide |
| Session-Cookie | HttpOnly + CSRF-Double-Submit (`frontend/src/lib/serverSession.ts:81–104`) | Solide |
| OIDC/SSO | Microsoft Entra ID, Code+PKCE, verschlüsselte State/Nonce-Transaktion, `tid`+`oid`-Bindung, App-Role-Gate (`app/services/entra_oidc_service.py`) | Solide, aber **nur Entra** |
| SAML | **Nicht vorhanden** | OFFENE LÜCKE |
| Generisches OIDC (Okta, Keycloak, Auth0) | **Nicht vorhanden** | OFFENE LÜCKE |
| SCIM | `SCIMProvisioningService` mit provision/update/disable/deprovision + `scim_sync_state` | Vorhanden; SCIM-2.0-Protokollkonformität nicht verifiziert |
| MFA | Eigene RFC-6238-TOTP-Implementierung (`app/services/enterprise_governance_service.py:196–220`) + Backup-Codes | Funktional; **kein WebAuthn/FIDO2** |
| Rollen | 10 Rollen (`app/rbac/roles.py`), 47 Permissions (`app/rbac/permissions.py`) | Umfangreich, gut strukturiert |
| Policy-Engine | OPA/Rego (`infra/opa/policies/`), `app/policy/opa_client.py` | Optional; Rego-Tests laufen in CI |
| Break-Glass | **Kein dediziertes Konzept** | OFFENE LÜCKE |
| Step-Up-Auth | `mfa_step_up`-Endpunkt vorhanden (`app/main.py:8744`) | Erzwingung pro privilegierter Aktion nicht durchgängig verifiziert |

**KRITISCHER BLOCKER — TOTP-Secret-Speicherung:**
`mfa_factors` speichert das TOTP-Secret. Es ist im Repository **kein Verschlüsselungspfad
für dieses Feld erkennbar** (keine Envelope-Encryption, kein Key-Vault-Bezug). Ein
Datenbank-Dump kompromittiert damit alle zweiten Faktoren aller Mandanten. Vor
Enterprise-Vertrieb zwingend zu beheben.

**OFFENE LÜCKE — SSO-Marktabdeckung:** Für Beratungshäuser, MSPs und Mittelstand ist
Entra-only vertretbar (hohe M365-Durchdringung in DACH). Für Enterprise-Ausschreibungen
ist fehlendes SAML 2.0 ein häufiger K.-o.-Punkt.

---

## 7. Audit-Logging

**BELEGT IM CODE:**

- Tabelle `audit_logs` (`app/models_db.py:729–753`) mit `tenant_id`, `actor`, `action`,
  `entity_type`, `entity_id`, `before`, `after`, `ip_address`, `user_agent`,
  `previous_hash`, `entry_hash`, `actor_role`, `outcome`, `correlation_id`, `metadata_json`.
- **Hash-Kette:** `app/repositories/audit_logs.py::_compute_entry_hash` verkettet Einträge
  über `previous_hash`. `AuditTrailService.verify_integrity()` prüft die Kette und liefert
  `first_invalid_id`.
- **Append-only-Guard:** `app/audit_append_only.py` hängt sich in SQLAlchemys
  `before_flush` und wirft bei UPDATE/DELETE auf `AuditLogTable`.
- **Export:** GoBD-Export (`app/services/audit_gobd_export.py`), CSV-Export, VVT-Export.
- **Pseudonymisierung:** `COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY`,
  `app/services/audit_metadata_sanitize.py`.

**Bewertung:** Das ist ein **echtes** Audit-Log, kein Marketing-Feature. Der
Append-only-Claim hat aber eine benannte Grenze:

**OFFENE LÜCKE — Append-only ist ORM-seitig, nicht DB-seitig.**
Der Guard greift ausschließlich für Schreibvorgänge über die SQLAlchemy-Session.
Direkter SQL-Zugriff, ein DBA, ein Backup-Restore oder ein Bulk-Statement umgehen ihn
vollständig. Es gibt weder ein `REVOKE UPDATE, DELETE`-Grant-Modell noch einen
DB-Trigger noch WORM-Storage. Zulässige Formulierung: *„Append-only auf
Applikationsebene erzwungen; DB-seitige Unveränderlichkeit im Betriebsmodell zu
konfigurieren."* Nicht zulässig: *„unveränderliche Audit-Logs"*.

**OFFENE LÜCKE — Hash-Kette ohne externen Anker.** Die Kette beweist interne Konsistenz,
nicht Nicht-Manipulation: Wer Schreibzugriff hat, kann die Kette neu berechnen. Für
belastbare Beweiskraft fehlt ein externer Zeitstempel (RFC 3161 / eIDAS-Qualified
Timestamp) oder ein periodischer Anchor-Digest an einen unabhängigen Verwahrer.

---

## 8. Integrationen

**BELEGT IM CODE** (`app/integrations/`, `infra/n8n/workflows/`):

| Integration | Status |
|---|---|
| DATEV-Export | `app/services/datev_extf_export.py`, EXTF-Format, `datev_export_logs` — **Export-Format, keine DATEV-Zertifizierung** (auf der Landingpage korrekt so ausgewiesen) |
| SAP | `app/integrations/sap_envelope.py`, `sap_inbound.py` — Envelope/Blueprint-Ebene |
| XRechnung | `app/services/xrechnung_export.py`, `xrechnung_exports` |
| n8n | 7 Workflow-JSONs, HMAC-SHA256-signierte Webhooks (`app/services/n8n_webhook_service.py`) |
| Connector-Framework | `enterprise_connector_instances|sync_runs|evidence_records`, Outbox-Pattern (`app/integrations/outbox.py`) |
| Temporal | `app/workflows/worker.py`, Board-Report-Workflow, TLS/API-Key-Config |
| OPA | Rego-Policies + Client, in CI getestet |

**PLAUSIBLE ANNAHME:** Die Connector-Landschaft ist überwiegend Skeleton/Blueprint
(siehe `docs/enterprise/wave55–58`). Für die Vertriebsaussage bedeutet das: „vorbereitet"
und „projektabhängig", nicht „verfügbar". Die aktuelle Landingpage formuliert das
bereits korrekt.

---

## 9. AI-/LLM-Nutzung

**BELEGT IM CODE:**

- **Router:** `app/services/llm_router.py` — task-typ-abhängige Provider-Ketten über
  `LLMProvider`: `CLAUDE`, `OPENAI`, `AZURE_OPENAI`, `GEMINI`, `LLAMA`.
- **Default aus:** `COMPLIANCEHUB_FEATURE_LLM_ENABLED=false` (`.env.example`).
  Jeder LLM-Task hat zusätzlich ein eigenes Flag (`app/services/llm_task_flags.py`).
- **Guardrails:** `app/llm/guardrails.py` — Regex-Heuristik für E-Mail/IBAN/Telefon
  sowie 9 Prompt-Injection-Marker; `COMPLIANCEHUB_LLM_PII_MODE=block` als Default.
- **Residenz-Logik:** `DataResidencyPolicy` je Mandant; `COMPLIANCEHUB_LLM_ASSUME_AZURE_EU`,
  `COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU`, `COMPLIANCEHUB_LLM_US_CLOUD_OK` sind
  **Betreiber-Attestierungen**, keine technischen Prüfungen.
- **Metadaten:** `llm_call_metadata` protokolliert Provider, Task, Latenz, Ergebnis.
- **Azure OpenAI:** Managed Identity als Produktionsstandard, HTTPS erzwungen,
  Provider-Fehler werden nicht durchgereicht.

**Bewertung positiv:** LLM-off-by-default plus PII-Block-by-default ist die richtige
Grundhaltung für den DACH-Markt und deutlich besser als der Marktdurchschnitt.

**KRITISCHER BLOCKER für „EU-only"-Claims:**
Die Provider-Ketten enthalten `OPENAI`, `CLAUDE` und `GEMINI` als reguläre Fallbacks für
`LEGAL_REASONING`, `STRUCTURED_OUTPUT`, `CHAT_ASSISTANT` und alle Board-Report-Tasks.
Es gibt **keinen erzwungenen Betriebsmodus**, der die Kette hart auf
`AZURE_OPENAI` (EU-Region) bzw. `LLAMA` (self-hosted) beschränkt. `_prefer_configured_azure`
*bevorzugt* Azure, entfernt die US-Provider aber nicht aus der Kette.
Solange das so ist, ist jede Aussage in Richtung „keine US-Anbieter" oder
„EU-souverän" **nicht marktreif belegbar** (Fix: `07-refactoring-roadmap.md`, P0-3).

**OFFENE LÜCKE — Redaction ist Heuristik.** `redact_obvious_pii_patterns` fängt
E-Mail/IBAN/Telefon. Namen, Adressen, Geburtsdaten, Kundennummern, Gesundheitsdaten und
Freitext-Personenbezug werden **nicht** erkannt. Die Funktion trägt den Kommentar
„extend with DLP/HITL in production" — dieser TODO ist noch offen. Zulässige Aussage:
*„heuristische PII-Erkennung mit Fail-Closed-Verhalten"*, nicht *„PII-frei"*.

---

## 10. Dateispeicher (Evidence)

**BELEGT IM CODE** (`app/services/evidence_storage.py`, `app/services/evidence_service.py`):

| Aspekt | Ist-Stand | Bewertung |
|---|---|---|
| Backend | **Nur** `LocalFilesystemEvidenceStorage`, Pfad `EVIDENCE_STORAGE_PATH` (Default `./data/evidence`) | KRITISCHER BLOCKER |
| Blob/S3 | Protocol `EvidenceStorageBackend` definiert, **keine Implementierung** | Doku (`docs/azure-runtime-storage-*`) suggeriert mehr |
| Pfad-Isolation | `_validate_storage_key` prüft `..`, führenden `/` und Tenant-Präfix | Solide |
| Dateiname | Original wird **nicht** als Pfad verwendet (UUID) | Solide |
| Typprüfung | Allowlist PDF/DOCX/XLSX/PNG/JPEG, aber **nur über Header + Extension** | OFFENE LÜCKE (spoofbar; kein Magic-Byte-Check) |
| Größenlimit | `EVIDENCE_MAX_BYTES`, Default 20 MB | OK |
| Malware-Scan | **Nicht vorhanden** (kein ClamAV, kein Defender-Hook) | KRITISCHER BLOCKER |
| Inhalts-Hash | **`evidence_files` hat keine `sha256`-Spalte** | KRITISCHER BLOCKER |
| Verschlüsselung at rest | Keine applikationsseitige Verschlüsselung | OFFENE LÜCKE |
| Retention/Löschung | Kein Job, kein Retention-Feld | OFFENE LÜCKE |

**Konsequenz für den Claim „Evidence/Audit-fähig":** Ohne Inhalts-Hash kann das Produkt
nicht nachweisen, dass eine hochgeladene Nachweisdatei seit Upload unverändert ist. Genau
das ist aber die Kernanforderung an Evidenz in ISO-27001- und GoBD-Prüfungen. Der Claim
„Evidenzintegrität" ist derzeit **nicht marktreif belegbar** (Fix: P0-4).

Ebenso: Ein GRC-Tool, in das Kunden Auditberichte, Verträge und Screenshots hochladen,
ohne Malware-Scan, ist in jeder Enterprise-Security-Review ein sofortiger Ausschlussgrund.

---

## 11. Job- und Workflow-Engine

**BELEGT IM CODE:**

- **Temporal** (`app/workflows/`): Board-Report-Workflow mit Activities, eigener
  Worker-Prozess, TLS-/API-Key-Konfiguration. Optionales Add-on.
- **Governance-Workflow-Engine** (`app/services/governance_workflow_service.py`,
  `governance_workflow_*`-Tabellen): deterministische Regel-Bundles mit
  `RULE_BUNDLE_VERSION`, Tasks, SLA, Eskalationsstufen, History.
- **Remediation-Automation** (`remediation_automation_runs`, `remediation_escalations`,
  `remediation_reminders`).
- **n8n**: 7 externe Workflows (Deadline-Reminder, Eskalation, Board-PDF, DATEV-Export,
  Access-Review-Reminder, Gap-Analyse).

**KRITISCHER BLOCKER — kein In-Process-Scheduler:**
`app/services/health_monitor.py:4–5` dokumentiert explizit: „invoke … from a cron job,
systemd timer, or (optional) APScheduler on app startup — see TODO at bottom." Zeile 219
enthält den unerledigten TODO. Es existiert **kein Scheduler im Repository**.

Das bedeutet: **Fristenüberwachung, Eskalation und Reminder laufen nur, wenn der Betreiber
extern n8n oder Cron aufsetzt.** Ein Produkt, dessen Kernnutzenversprechen
„24h/72h-Meldekaskade und Fristenüberwachung" ist, darf diese Ausführung nicht
undokumentiert an eine optionale externe Komponente delegieren. Für den Kunden ist
nicht erkennbar, ob seine Frist überwacht wird.

---

## 12. Deployment-Setup

**KRITISCHER BLOCKER — Es gibt kein Deployment-Artefakt für das Backend.**

Verifiziert per `find`: **kein Dockerfile, kein docker-compose, kein Terraform, kein
Bicep, kein Helm-Chart, kein Kubernetes-Manifest, keine App-Service-Konfiguration** im
gesamten Repository.

| Komponente | Deployment |
|---|---|
| Frontend | Vercel (`frontend/vercel.json`, `regions: ["fra1"]`) — **BELEGT** |
| Backend | **Nicht definiert** |
| Datenbank | **Nicht definiert** (Default SQLite-Datei) |
| Evidence-Storage | **Nicht definiert** (lokales FS) |
| Temporal | **Nicht definiert** |
| OPA | **Nicht definiert** |
| n8n | **Nicht definiert** |

Konsequenzen:

1. Aussagen zu **Hosting-Region, Datenresidenz und EU-Hosting** sind für den
   Produktkern im Repository **nicht verifizierbar** — es gibt nichts zu verifizieren.
2. **Disaster Recovery, RPO/RTO, Backup-Restore-Test** sind nicht dokumentierbar.
3. Reproduzierbarkeit und Supply-Chain-Integrität des Backend-Builds sind nicht gegeben.
4. Jede Kundenfrage nach einem Architekturdiagramm mit Datenflüssen ist heute nicht
   beantwortbar.

Die Doku (`docs/azure-postgresql-rls-runtime-state-20260715.md`,
`docs/azure-runtime-storage-csp-reporting-20260715.md`) beschreibt eine Azure-Zielarchitektur.
Diese ist im Repository **nicht implementiert** — weder als IaC noch als Code-Pfad
(kein `azure-storage-blob` in `pyproject.toml`, keine `BlobServiceClient`-Nutzung im Backend).

---

## 13. CI/CD

**BELEGT IM CODE** (`.github/workflows/ci.yml`, `codeql.yml`, `dependabot.yml`, `CODEOWNERS`):

| Job | Inhalt |
|---|---|
| `backend` | ruff check + format, `pip-audit`, `bandit -lll`, `pytest` (178 Testdateien) |
| `frontend` | `npm audit --audit-level=moderate`, ESLint `--max-warnings=0`, Vitest, Production-Build |
| `policy` | `opa test` gegen Rego-Policies |
| `postgres-rls` | PostgreSQL 17, wendet RLS-Migration **zweimal** an (Idempotenz-Test) + `tests/postgres/advisor_runtime_state_rls_test.sql` |
| `dependency-review` | `fail-on-severity: moderate` auf PRs |
| CodeQL | separater Workflow |
| Dependabot | Python, npm, GitHub Actions |

Alle Third-Party-Actions sind auf **Commit-SHA gepinnt**. Das ist vorbildlich.

**Bewertung:** Die CI ist der stärkste Teil des Projekts und deutlich über dem
Marktdurchschnitt vergleichbarer Produkte.

**OFFENE LÜCKE — kein CD:** Es gibt keinen Deploy-Workflow, keine Umgebungs-Promotion,
keine Release-Signierung, kein SBOM-Artefakt im Build (nur der GitHub-Dependency-Graph).
Kein DAST, kein Container-Scan (mangels Container), keine Secret-Rotation-Automatik.

---

## 14. Secrets, Config, Environments

**BELEGT IM CODE:**

- Konfiguration ausschließlich über Umgebungsvariablen, Präfix `COMPLIANCEHUB_*`.
- `.env.example` und `.env.pilot.example` als Vorlagen; `.gitignore` schließt `.env` aus.
- Azure OpenAI: `AZURE_OPENAI_AUTH=managed_identity` als Produktionsstandard;
  API-Key nur als lokaler Break-Glass dokumentiert.
- API-Keys der Mandanten: SHA-256-Hash in `tenant_api_keys` (`app/security.py::hash_api_key`).
- Konstantzeit-Vergleiche über `secrets.compare_digest` (`secret_matches_any`).
- Release-Attestierungen: `COMPLIANCEHUB_RELEASE_CHANNEL`, `COMPLIANCEHUB_ENTERPRISE_AUTH_READY`,
  `COMPLIANCEHUB_LEGAL_PUBLISH_READY`.

**OFFENE LÜCKE — kein Secret-Manager im Code.** Kein Key-Vault-, Secrets-Manager- oder
SOPS-Pfad. Alle Secrets sind Klartext-ENV im Prozessraum.

**OFFENE LÜCKE — API-Key-Hashing ohne Salt/KDF.** `hash_api_key` ist ein reines
SHA-256 über den Rohschlüssel. Für hochentropische Zufallsschlüssel akzeptabel, aber
es gibt **keine erzwungene Mindestentropie** bei der Key-Erzeugung und keinen
Rotations-/Ablaufmechanismus (`tenant_api_keys` hat kein `expires_at`).

**KRITISCHER BLOCKER — `COMPLIANCEHUB_ADMIN_API_KEYS`.** Ein statischer, nicht
rotierender, nicht ablaufender ENV-String autorisiert `POST /api/v1/tenants/provision`,
also die Anlage beliebiger Mandanten. Kein MFA, kein Vier-Augen-Prinzip, keine
IP-Beschränkung, kein Ablauf.

---

## 15. Vendor-Abhängigkeiten (kritischer Pfad)

**BELEGT IM CODE.** Jurisdiktion bezeichnet die Kontrolle über das Unternehmen, nicht
den Serverstandort — für CLOUD-Act-Exposition ist Ersteres maßgeblich.

| Vendor | Rolle | Jurisdiktion | Im kritischen Pfad? | Belegstelle |
|---|---|---|---|---|
| **Vercel Inc.** | Hosting Frontend + BFF | **US** | **Ja** — 48 Server-Routes, darunter der Catch-all-Proxy zum Backend; terminiert Session-Cookies und leitet authentifizierte Mandantendaten weiter | `frontend/vercel.json`, `frontend/src/app/api/backend/[...path]/route.ts` |
| **Microsoft** (Azure OpenAI, Entra ID) | LLM + IdP | **US** (EU-Region wählbar) | Ja | `.env.example`, `app/services/entra_oidc_service.py` |
| **OpenAI** | LLM-Fallback | **US** | Ja, wenn LLM aktiv | `app/services/llm_router.py` |
| **Anthropic** | LLM-Fallback | **US** | Ja, wenn LLM aktiv | `app/services/llm_router.py` |
| **Google** (Gemini) | LLM-Fallback | **US** | Ja, wenn LLM aktiv | `app/services/llm_router.py` |
| **GitHub / Microsoft** | Quellcode, CI, CodeQL | **US** | Build-Pfad, nicht Datenpfad | `.github/workflows/` |
| **Temporal** | Workflow-Engine | US-Firma; self-host möglich | Optional | `app/workflows/config.py` |
| **n8n** | Automatisierung | DE (n8n GmbH); self-host möglich | Optional, aber **de facto nötig für Fristen** | `infra/n8n/` |
| Stripe | Billing | **US** | Code vorhanden (`stripe_billing_service.py`), Aktivierung unklar | `app/services/stripe_billing_service.py` |
| Sentry | — | — | **Nicht verwendet** (positiv) | — |

**Kernbefund für Souveränitätsaussagen:** Vercel ist **US-kontrolliert** und liegt im
Datenpfad — nicht nur in der Auslieferung statischer Assets, sondern als BFF, der
Session-Cookies setzt und authentifizierte Produktanfragen weiterleitet. Die Region
`fra1` ändert daran nichts: maßgeblich für den CLOUD Act ist die Kontrolle über den
Anbieter, nicht der Serverstandort.

Die Trust-Center-Seite weist Vercel korrekt aus, beschränkt die Aussage aber auf die
„öffentliche Website". Sobald das authentifizierte Produkt über denselben Vercel-BFF
läuft, ist diese Abgrenzung **nicht mehr zutreffend** (Detail: `05-gdpr-cloud-act-gap-analysis.md`).

---

## 16. Vorhandene Compliance-Features

**BELEGT IM CODE** — bemerkenswert breit:

- KI-System-Register mit AI-Act-Pflichtfeldern (`intended_purpose`,
  `training_data_provenance`, `fria_reference`, `provider_name`/`deployer_name`,
  `provider_responsibilities`/`deployer_responsibilities`, `pms_status` + PMS-Review-Daten)
- Risikoklassifizierungs-Engine nach Art.-6-Entscheidungsbaum
  (`app/services/classification_engine.py`), Annex-I/III-Berücksichtigung
- Art.-50-Transparenz-Assurance mit versionierten Assessments und Controls
- Policy-Engine mit Regeln und Violations
- Cross-Regulation-Mapping (`compliance_requirement_relations`) — „assess once, comply many"
- Governance-Controls mit Framework-Mappings, Evidence, Reviews, Statushistorie
- Governance-Workflow-Engine mit SLA und Eskalation
- NIS2-Incident-Modell mit 24h/72h/1-Monats-Fristenfeldern
- KRITIS-KPIs mit Board-Alert-Schwellen
- Audit-Trail mit Hash-Kette und GoBD-/VVT-Export
- Trust Center (mandantenseitig): Assets, Sensitivity-Stufen, Evidence-Bundles mit
  ECDSA-Signatur und Key-Rotation-sicherer Verifikation, Access-Logs
- Board-Reporting mit Snapshots und Metrik-Historie
- Access Reviews, SoD-Policies, Approval-Requests, Privileged-Action-Events
- Readiness-Score, Governance-Maturity, Gap-Analyse, What-If-Simulator
- Authority-Audit-Preparation-Pack

Das ist **substanziell mehr Fachtiefe als bei den meisten AI-Act-Tools am DACH-Markt.**
Die Produktvision trägt.

---

## 17. Fehlende Compliance-Features (Kurzliste)

| Fehlend | Betrifft | Priorität |
|---|---|---|
| ROPA / Verzeichnis der Verarbeitungstätigkeiten als Entität | DSGVO Art. 30 | P1 |
| Data Processing Activity, Data Category, Rechtsgrundlage | DSGVO Art. 30 | P1 |
| Supplier / Subprocessor als Entität | NIS2 Art. 21(2)(d), DSGVO Art. 28 | P1 |
| Transfer Record + TIA | Schrems II, Kap. V DSGVO | P1 |
| DPA/AVV-Register | DSGVO Art. 28 | P1 |
| Retention Rule + Löschjob | DSGVO Art. 5(1)(e), Art. 17 | P0 |
| DSAR-/Betroffenenrechte-Workflow | DSGVO Art. 12–22 | P1 |
| Datenexport + Mandantenlöschung (Exit) | DSGVO, Vertragsende | P0 |
| AI-Literacy-/Schulungsnachweise | AI Act Art. 4 | P1 |
| Rollenabgrenzung Anbieter/Betreiber/Importeur/Händler/Bevollmächtigter als Enum | AI Act Art. 3, 16, 22–27 | P1 |
| Serious-Incident-Meldepfad AI Act Art. 73 | AI Act | P1 |
| Zeitpunkt der Kenntniserlangung bei NIS2-Incidents | NIS2 Art. 23 | **P0** |
| Meldungsnachweise (Einreichzeitpunkt, Behörde, Aktenzeichen) | NIS2 Art. 23 | P1 |
| Geschäftsleitungs-Billigung und -Schulung | NIS2 Art. 20 / § 38 BSIG | P1 |
| Risk / Risk Treatment als eigenes Register | ISO 27001, NIS2 Art. 21 | P1 |
| Legal Entity / Jurisdiction unterhalb des Mandanten | Konzernstrukturen | P2 |

---

## 18. Zusammenfassende Einordnung

**Das Produkt ist fachlich weiter, als es betrieblich ist.**

Die regulatorische Modellierung (AI Act, Cross-Regulation-Mapping, Governance-Controls,
Workflow-Engine) ist die eigentliche Stärke und ein tragfähiger Wettbewerbsvorteil.
Die CI-Disziplin und die Messaging-Hygiene auf der öffentlichen Website sind
überdurchschnittlich sorgfältig.

Die blockierenden Defizite liegen fast vollständig in der **Betriebs- und
Nachweisschicht**: kein Deployment-Artefakt, SQLite als Default, RLS beworben aber
unwirksam, Evidence ohne Hash und Malware-Scan, kein Scheduler für die Fristen, die
das Produkt verspricht, keine Löschkonzept-Implementierung, und US-LLM-Provider ohne
erzwingbaren EU-Modus.

Vollständige Bewertung: `../market-readiness/00-executive-readiness-verdict.md`.
