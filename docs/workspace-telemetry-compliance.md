# Workspace-Telemetrie: Event-Modell, NIS2/ISO-Bezug, SIEM

Internes Referenzdokument für GRC, Security Operations und Enterprise-Kunden (SAP/BTP-Deployments).  
**Keine PII** in `usage_events`-Payloads: nur `tenant_id` als Spalte, strukturiertes JSON ohne Namen, E-Mails oder Request-Bodies.

## 1. Normalisiertes Event-Modell

### Kernfelder (konzeptionell)

| Feld | Quelle | Hinweis |
|------|--------|---------|
| `tenant_id` | DB-Spalte `usage_events.tenant_id` | Mandantenbezug für Multi-Tenant-Auswertung |
| `event_type` | DB-Spalte | Stabiler Name für SIEM-Regeln |
| `payload_json` | Strukturiertes JSON | Siehe Schema pro Event |
| `created_at_utc` | DB-Zeitstempel | UTC |

### Payload-Felder (JSON, ohne PII)

Jedes Event enthält mindestens:

| Feld | Bedeutung |
|------|-----------|
| `event_type` | Gleich DB-Spalte `event_type` (SIEM-Export als Ein-Blob) |
| `tenant_id` | Mandanten-ID (wie DB-Spalte) |
| `workspace_mode` | `production` \| `demo` \| `playground` \| `unknown` |
| `actor_type` | `tenant` (Mandanten-API-Key) \| `advisor` (Pfad unter `/api/v1/advisors/`) |
| `timestamp` | ISO-8601 UTC (z. B. `2026-03-25T12:00:00Z`) |

Optional:

| Feld | Bedeutung |
|------|-----------|
| `result` | `success` \| `forbidden_demo_readonly` |
| `feature_name` | UI-/Feature-Tag (snake_case), z. B. `board_ai_compliance_report` |
| `route` | OpenAPI-Pfad-Template, z. B. `/api/v1/ai-systems` |
| `method` | HTTP-Methode in Großbuchstaben |
| weitere Schlüssel | Nur über `extra`, nach Allowlist/Denylist (keine E-Mails, kein Freitext) |

**Sink:** Postgres-Tabelle `usage_events` (bestehend). Zusätzlich optional **`COMPLIANCEHUB_WORKSPACE_TELEMETRY_STRUCTURED_LOG=true`** → eine JSON-Zeile pro Event im App-Logger (PostHog/Collector-seitig abgreifbar).

**Bewusst nicht enthalten (DSGVO / Datenminimierung):** IP-Adresse, User-Agent, API-Key-Wert, Korrelations-IDs, AI-System-Namen, Freitext aus Bodies.  
**Ergänzung für strengere ISO/NIS2-Audits (Roadmap):** optionale `correlation_id` (technisch, keine PII), `high_risk_context` (bool oder Enum), Export in separates **Audit-Log** (immutabel) vs. **Usage-Telemetrie**.

## 2. Kanonische Event-Typen

| `event_type` | Zweck |
|--------------|--------|
| `workspace_session_started` | Modus-bewusster Session-Start (derzeit: Demo-Mandant bei `GET /workspace/tenant-meta`, Dedupe 24h) |
| `workspace_feature_used` | Nutzung eines Demo-Story-Features (`GET /workspace/feature-used?feature_key=…`) |
| `workspace_mutation_blocked` | Schreibversuch in read-only Demo/Playground (Policy), inkl. Route/Methode |
| `workspace_incident_flagged` | **Reserviert** – noch keine Emission; für AI-Governance-/Security-Incidents |

### Migration von früheren Namen

Alte Konstanten `demo_session_started`, `demo_feature_used`, `demo_mutation_blocked` sind im Code **Aliase auf dieselben String-Werte** wie die `workspace_*`-Typen (keine doppelten Events). Bestehende SIEM-Regeln sollten auf die neuen Namen umgestellt werden.

## 3. Beispiel-JSON

### workspace_session_started (Demo-Mandant)

```json
{
  "event_type": "workspace_session_started",
  "tenant_id": "demo-seed-tenant-1",
  "workspace_mode": "demo",
  "actor_type": "tenant",
  "timestamp": "2026-03-25T12:00:00Z",
  "result": "success"
}
```

### workspace_feature_used

```json
{
  "event_type": "workspace_feature_used",
  "tenant_id": "demo-seed-tenant-1",
  "workspace_mode": "demo",
  "actor_type": "tenant",
  "timestamp": "2026-03-25T12:01:00Z",
  "feature_name": "board_ai_compliance_report",
  "result": "success"
}
```

### workspace_mutation_blocked

```json
{
  "event_type": "workspace_mutation_blocked",
  "tenant_id": "demo-seed-tenant-1",
  "workspace_mode": "demo",
  "actor_type": "tenant",
  "timestamp": "2026-03-25T12:02:00Z",
  "result": "forbidden_demo_readonly",
  "route": "/api/v1/ai-systems",
  "method": "POST"
}
```

### workspace_session_started (Produktiv – sobald ausgeweitet)

```json
{
  "event_type": "workspace_session_started",
  "tenant_id": "prod-tenant-1",
  "workspace_mode": "production",
  "actor_type": "tenant",
  "timestamp": "2026-03-25T12:00:00Z",
  "result": "success"
}
```

*Hinweis: Session-Telemetrie für reine Produktiv-Mandanten ist aktuell nicht aktiv (nur `is_demo` bei tenant-meta); Schema ist dafür vorbereitet.*

## 4. NIS2 / ISO 27001 / ISO 42001 – Mapping (hochlevel)

| Anforderung / Kontrollidee | Relevanz dieser Events |
|----------------------------|------------------------|
| **NIS2** – Überwachung von Zugriffen und ungewöhnlichem Verhalten | `workspace_mutation_blocked` zeigt verweigerte Schreibzugriffe (Policy durchgesetzt); Häufung pro Mandant/Route als Indikator |
| **ISO 27001 A.8.x / Logging** | Strukturierte, zeitgestempelte Ereignisse ohne PII; Export aus `usage_events` in SIEM |
| **ISO 27001 A.9** Zugriffskontrolle | `actor_type` unterscheidet Berater- vs. Mandanten-Pfade auf API-Ebene |
| **ISO 42001** AI-Governance-Überwachung | `feature_name` + `workspace_mode` für Demo/Story vs. Produktion; **Konfigurationsänderungen** an Hochrisiko-KI sollten künftig über **Audit-Log** + optionale `workspace_incident_flagged` / dedizierte Events abgebildet werden |

### Typische Lücken für ein formales Audit

- **Kein** vollständiges Benutzer-Identitäts-Mapping (nur API-Mandant) – für Enterprise oft Ergänzung durch IdP-Logs (SAP IAS, Azure AD).
- **Keine** IP/User-Agent in Usage-Events – bei Bedarf nur in **Edge/WAF**-Logs mit strenger Aufbewahrungsrichtlinie.
- **Hochrisiko-KI-Kontext** (welches System) bei Mutationen: aktuell nicht in Telemetry-Payload; Audit-Trail über `audit_logs` / Domain-Repositories.

## 5. Backend-Implementierung (Ist)

- **Zentral:** `app/services/workspace_telemetry.py` – `emit_workspace_event` (Schema + optional strukturiertes Log), Wrapper `log_workspace_*`.
- **Fehler / Performance:** synchroner Insert in derselben Request-Session; Fehler werden geschluckt (`log_usage_event`). Kein Blockieren durch Telemetrie-Timeouts außerhalb DB.
- **Integration:** `GET /workspace/tenant-meta` (Demo) → `workspace_session_started`; `GET /workspace/feature-used` (Alias: `demo-feature-used`) → `workspace_feature_used`; Demo-Guard → `workspace_mutation_blocked`.
- **Middleware:** bewusst nicht global; Guard + explizite Hooks halten die Pipeline schlank und vermeiden Doppelzählung.

## 6. Frontend-Vertrag

- **Primär serverseitig:** Modus kommt aus dem Backend (`workspace_mode` in Meta); keine parallele „Wahrheit“ im Client.
- **Client:** `useWorkspaceMode` für UX; `logDemoFeatureUsed` / `feature-used` sendet nur `feature_key` (Query) – Server ergänzt `workspace_mode`, `actor_type`, `result`.
- **Kein** Ersatz für Audit-Log: UI-Telemetrie ergänzt keine GoBD-/ISO-Nachweise für Inhaltsänderungen.

## 7. Beispiel-Auswertungen (SQL-artig / SIEM)

**Alle blockierten Schreibversuche in Demo-Mandanten (letzte 30 Tage):**

- Filter: `event_type = workspace_mutation_blocked` AND `payload.workspace_mode = demo` AND `result = forbidden_demo_readonly`

**Demo-Feature-Reichweite (Sales/GTM):**

- Filter: `event_type = workspace_feature_used` GROUP BY `payload.feature_name`

**Berater vs. Mandant (Zugriffsmuster):**

- Filter: `event_type IN (workspace_session_started, workspace_feature_used, workspace_mutation_blocked)` GROUP BY `payload.actor_type`

**Konfigurationsänderungen Hochrisiko-KI (Zielbild):**

- Heute: über **Audit-Log-Tabellen** / dedizierte API-Audit-Events, nicht über `usage_events` allein.
- Roadmap: `workspace_incident_flagged` oder Domänen-Event `ai_system_config_changed` mit `risk_level=high` (ohne PII im Payload).

---

*Pflege: Bei neuen Events `usage_event_logger` / `workspace_telemetry` erweitern und dieses Dokument anpassen.*
